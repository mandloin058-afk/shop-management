from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from . import balance
from .forms import AccountEntryForm, CustomerForm, ExpenseForm, PaymentForm, ProductForm, PurchaseForm, SaleForm
from .models import AccountEntry, Customer, Expense, Payment, Product, Purchase, Sale, total_of


# ---------- Small helpers ----------
class FormPage(LoginRequiredMixin):
    """Shared behaviour for all add/edit pages."""
    template_name = "form.html"
    title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context

    def form_valid(self, form):
        messages.success(self.request, "Saved successfully.")
        return super().form_valid(form)


class RemovePage(LoginRequiredMixin, DeleteView):
    """Shared delete confirmation page."""
    template_name = "confirm_delete.html"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, "Cannot delete: this record is used in other entries.")
            return redirect(self.success_url)
        messages.success(self.request, "Deleted.")
        return response


def summary(sales, purchases, expenses):
    """Sales, purchases, expenses, gross profit and net profit for the given records."""
    gross = total_of(sales, "profit")  # Sales revenue - cost of sold products
    spent = total_of(expenses, "amount")
    return {
        "sales": total_of(sales),
        "purchases": total_of(purchases),
        "expenses": spent,
        "gross": gross,
        "net": gross - spent,
    }


def stock_data():
    return {p.pk: {"sell": str(p.selling_price), "cost": str(p.purchase_price), "stock": p.stock}
            for p in Product.objects.all()}


# ---------- Dashboard ----------
@login_required
def dashboard(request):
    today = timezone.localdate()
    day = summary(Sale.objects.filter(date=today), Purchase.objects.filter(date=today),
                  Expense.objects.filter(date=today))
    stock_value = sum(p.stock_value for p in Product.objects.all())
    pending = total_of(Sale.objects.filter(payment_method="Udhaar")) - total_of(Payment.objects, "amount")
    low_stock = Product.objects.filter(stock__lte=F("min_stock"))

    stats = [
        ("Today's sales", day["sales"]), ("Today's purchases", day["purchases"]),
        ("Today's expenses", day["expenses"]), ("Today's gross profit", day["gross"]),
        ("Today's net profit", day["net"]), ("Total stock value", stock_value),
        ("Pending udhaar", pending),
    ]

    recent = []
    for s in Sale.objects.select_related("product")[:5]:
        recent.append(("Sale", f"{s.product.name} x {s.quantity}", s.total, s.date, s.created_at))
    for p in Purchase.objects.select_related("product")[:5]:
        recent.append(("Purchase", f"{p.product.name} x {p.quantity}", p.total, p.date, p.created_at))
    for e in Expense.objects.all()[:5]:
        recent.append(("Expense", e.category, e.amount, e.date, e.created_at))
    recent.sort(key=lambda r: r[4], reverse=True)

    return render(request, "shop/dashboard.html", {
        "stats": stats, "low_stock": low_stock, "low_count": low_stock.count(), "recent": recent[:8],
    })


# ---------- Products ----------
class ProductList(LoginRequiredMixin, ListView):
    model = Product
    template_name = "shop/product_list.html"

    def get_queryset(self):
        q = self.request.GET.get("q", "")
        return Product.objects.filter(name__icontains=q)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


class ProductCreate(FormPage, CreateView):
    model, form_class, title = Product, ProductForm, "Add product"
    success_url = reverse_lazy("product_list")


class ProductUpdate(FormPage, UpdateView):
    model, form_class, title = Product, ProductForm, "Edit product"
    success_url = reverse_lazy("product_list")


class ProductDelete(RemovePage):
    model = Product
    success_url = reverse_lazy("product_list")


# ---------- Purchases ----------
class PurchaseList(LoginRequiredMixin, ListView):
    model = Purchase
    paginate_by = 20
    template_name = "shop/purchase_list.html"
    queryset = Purchase.objects.select_related("product")


class PurchaseCreate(FormPage, CreateView):
    model, form_class, title = Purchase, PurchaseForm, "New purchase"
    template_name = "shop/trade_form.html"
    success_url = reverse_lazy("purchase_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_data"] = stock_data()
        return context


class PurchaseDelete(RemovePage):
    model = Purchase
    success_url = reverse_lazy("purchase_list")


# ---------- Sales ----------
class SaleList(LoginRequiredMixin, ListView):
    model = Sale
    paginate_by = 20
    template_name = "shop/sale_list.html"
    queryset = Sale.objects.select_related("product", "customer")


class SaleCreate(FormPage, CreateView):
    model, form_class, title = Sale, SaleForm, "New sale"
    template_name = "shop/trade_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product_data"] = stock_data()
        return context

    def get_success_url(self):
        return reverse("sale_invoice", args=[self.object.pk])  # go straight to the invoice


class SaleDelete(RemovePage):
    model = Sale
    success_url = reverse_lazy("sale_list")


@login_required
def sale_invoice(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("product", "customer"), pk=pk)
    return render(request, "shop/invoice.html", {"sale": sale, "shop_name": settings.SHOP_NAME})


# ---------- Customers / Udhaar ----------
class CustomerList(LoginRequiredMixin, ListView):
    model = Customer
    template_name = "shop/customer_list.html"


class CustomerCreate(FormPage, CreateView):
    model, form_class, title = Customer, CustomerForm, "Add customer"
    success_url = reverse_lazy("customer_list")


class CustomerUpdate(FormPage, UpdateView):
    model, form_class, title = Customer, CustomerForm, "Edit customer"
    success_url = reverse_lazy("customer_list")


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = PaymentForm(request.POST or None, customer=customer)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        payment.customer = customer
        payment.save()
        messages.success(request, "Payment recorded.")
        return redirect("customer_detail", pk=pk)
    return render(request, "shop/customer_detail.html", {
        "customer": customer, "form": form,
        "udhaar_sales": customer.sales.filter(payment_method="Udhaar").select_related("product"),
        "payments": customer.payments.all(),
    })


# ---------- Expenses ----------
class ExpenseList(LoginRequiredMixin, ListView):
    model = Expense
    paginate_by = 20
    template_name = "shop/expense_list.html"


class ExpenseCreate(FormPage, CreateView):
    model, form_class, title = Expense, ExpenseForm, "Add expense"
    success_url = reverse_lazy("expense_list")


class ExpenseUpdate(FormPage, UpdateView):
    model, form_class, title = Expense, ExpenseForm, "Edit expense"
    success_url = reverse_lazy("expense_list")


class ExpenseDelete(RemovePage):
    model = Expense
    success_url = reverse_lazy("expense_list")


# ---------- Reports ----------
def get_date(value, default):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return default


@login_required
def report_daily(request):
    day = get_date(request.GET.get("date"), timezone.localdate())
    sales = Sale.objects.filter(date=day).select_related("product")
    purchases = Purchase.objects.filter(date=day).select_related("product")
    expenses = Expense.objects.filter(date=day)
    return render(request, "shop/report_daily.html", {
        "day": day, "sm": summary(sales, purchases, expenses),
        "sales": sales, "purchases": purchases, "expenses": expenses,
    })


@login_required
def report_monthly(request):
    try:
        year, month = map(int, request.GET.get("month", "").split("-"))
        first = date(year, month, 1)
    except ValueError:
        first = timezone.localdate().replace(day=1)
    filters = {"date__year": first.year, "date__month": first.month}
    sales = Sale.objects.filter(**filters)
    purchases = Purchase.objects.filter(**filters)
    expenses = Expense.objects.filter(**filters)

    rows = defaultdict(lambda: {"sales": 0, "purchases": 0, "expenses": 0, "gross": 0})
    for r in sales.values("date").annotate(t=Sum("total"), g=Sum("profit")).order_by():
        rows[r["date"]].update(sales=r["t"], gross=r["g"])
    for r in purchases.values("date").annotate(t=Sum("total")).order_by():
        rows[r["date"]]["purchases"] = r["t"]
    for r in expenses.values("date").annotate(t=Sum("amount")).order_by():
        rows[r["date"]]["expenses"] = r["t"]
    days = [dict(v, date=d, net=v["gross"] - v["expenses"]) for d, v in sorted(rows.items())]

    return render(request, "shop/report_monthly.html", {
        "first": first, "sm": summary(sales, purchases, expenses), "days": days,
    })


@login_required
def report_products(request):
    today = timezone.localdate()
    start = get_date(request.GET.get("start"), today.replace(day=1))
    end = get_date(request.GET.get("end"), today)
    rows = (Sale.objects.filter(date__range=(start, end))
            .values("product__name")
            .annotate(qty=Sum("quantity"), revenue=Sum("total"), profit=Sum("profit"))
            .order_by("-revenue"))
    return render(request, "shop/report_products.html", {"rows": rows, "start": start, "end": end})


@login_required
def report_stock(request):
    products = Product.objects.all()
    return render(request, "shop/report_stock.html", {
        "products": products, "stock_value": sum(p.stock_value for p in products),
    })


# ---------- Accounts (cash, capital, loans ... entered by hand) ----------
class AccountEntryList(LoginRequiredMixin, ListView):
    model = AccountEntry
    paginate_by = 20
    template_name = "shop/account_entry_list.html"


class AccountEntryCreate(FormPage, CreateView):
    model, form_class, title = AccountEntry, AccountEntryForm, "Add account entry"
    success_url = reverse_lazy("account_list")


class AccountEntryUpdate(FormPage, UpdateView):
    model, form_class, title = AccountEntry, AccountEntryForm, "Edit account entry"
    success_url = reverse_lazy("account_list")


class AccountEntryDelete(RemovePage):
    model = AccountEntry
    success_url = reverse_lazy("account_list")


# ---------- Balance sheet ----------
def stock_value_on(day):
    """Value of stock in hand on the given day (today's figure uses the live stock)."""
    products = Product.objects.all()
    if day >= timezone.localdate():
        return sum((p.stock_value for p in products), Decimal("0"))
    bought = dict(Purchase.objects.filter(date__lte=day).values_list("product").annotate(q=Sum("quantity")).order_by())
    sold = dict(Sale.objects.filter(date__lte=day).values_list("product").annotate(q=Sum("quantity")).order_by())
    return sum((max(0, bought.get(p.pk, 0) - sold.get(p.pk, 0)) * p.purchase_price for p in products), Decimal("0"))


def balance_sheet_on(day):
    manual = {r["kind"]: r["s"] for r in
              AccountEntry.objects.filter(date__lte=day).values("kind").annotate(s=Sum("amount")).order_by()}
    receivable = (total_of(Sale.objects.filter(payment_method="Udhaar", date__lte=day))
                  - total_of(Payment.objects.filter(date__lte=day), "amount"))
    earned = (total_of(Sale.objects.filter(date__lte=day), "profit")
              - total_of(Expense.objects.filter(date__lte=day), "amount"))
    return balance.compute(manual, receivable, stock_value_on(day), earned)


@login_required
def report_balance_sheet(request):
    today = timezone.localdate()
    day = get_date(request.GET.get("date"), today)
    compare = get_date(request.GET.get("compare"), None)
    dates = [day] + ([compare] if compare else [])
    columns = [balance_sheet_on(d) for d in dates]
    return render(request, "shop/balance_sheet.html", {
        "dates": dates, "day": day, "compare": compare,
        "rows": balance.rows(columns), "main": columns[0],
        "shop_name": settings.SHOP_NAME,
    })
