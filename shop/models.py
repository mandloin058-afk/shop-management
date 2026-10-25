from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

# Reusable field settings
MONEY = dict(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
QTY = dict(validators=[MinValueValidator(1)])
TOTAL = dict(max_digits=12, decimal_places=2, default=0, editable=False)

PAYMENT_METHODS = [("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card"), ("Udhaar", "Udhaar")]
EXPENSE_CATEGORIES = [(c, c) for c in ("Rent", "Electricity", "Transport", "Packaging", "Repairs", "Other")]

# Balance-sheet items that the shop owner enters by hand (everything else is worked out from sales/purchases)
ENTRY_KINDS = [
    ("cash", "Cash / Bank balance"),
    ("other_current_asset", "Other current assets"),
    ("ppe", "Property, plant and equipment"),
    ("accumulated_depreciation", "Accumulated depreciation"),
    ("accounts_payable", "Accounts payable (suppliers ko baki)"),
    ("customer_credit", "Customer credit (customer ka advance)"),
    ("tax_payable", "Tax payable (GST)"),
    ("other_current_liability", "Other current liabilities"),
    ("long_term_debt", "Long term debt (loan)"),
    ("equity_capital", "Equity capital"),
    ("retained_earnings_opening", "Retained earnings (pehle ka)"),
]


def total_of(queryset, field="total"):
    """Sum a field of a queryset (0 if empty)."""
    return queryset.aggregate(s=Sum(field))["s"] or Decimal("0")


class Product(models.Model):
    name = models.CharField(max_length=100, unique=True)
    purchase_price = models.DecimalField(**MONEY)
    selling_price = models.DecimalField(**MONEY)
    stock = models.PositiveIntegerField(default=0, verbose_name="Current stock")
    min_stock = models.PositiveIntegerField(default=5, verbose_name="Minimum stock")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_low(self):
        return self.stock <= self.min_stock

    @property
    def stock_value(self):
        return self.stock * self.purchase_price


class Customer(models.Model):
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def total_amount(self):  # everything bought on udhaar
        return total_of(self.sales.filter(payment_method="Udhaar"))

    @property
    def paid_amount(self):
        return total_of(self.payments, "amount")

    @property
    def remaining(self):
        return self.total_amount - self.paid_amount


class Payment(models.Model):
    """Money received from a customer against udhaar."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(**MONEY)
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-date", "-id"]


class Purchase(models.Model):
    supplier = models.CharField(max_length=100)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(**QTY)
    purchase_price = models.DecimalField(**MONEY)
    total = models.DecimalField(**TOTAL)
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def save(self, *args, **kwargs):
        if self._state.adding:  # new purchase -> add to stock
            self.total = self.quantity * self.purchase_price
            with transaction.atomic():
                super().save(*args, **kwargs)
                Product.objects.filter(pk=self.product_id).update(stock=F("stock") + self.quantity)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # undo the stock increase
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.product_id)
            product.stock = max(0, product.stock - self.quantity)
            product.save(update_fields=["stock"])
            return super().delete(*args, **kwargs)


class Sale(models.Model):
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.PROTECT, related_name="sales")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(**QTY)
    selling_price = models.DecimalField(**MONEY)
    discount = models.DecimalField(default=0, **MONEY)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    total = models.DecimalField(**TOTAL)
    profit = models.DecimalField(**TOTAL)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, default="Cash")
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def subtotal(self):
        return self.quantity * self.selling_price

    def save(self, *args, **kwargs):
        if self._state.adding:
            # Remember the cost at the time of sale so old profit never changes
            self.cost_price = self.product.purchase_price
            self.total = self.subtotal - self.discount
            self.profit = self.total - self.quantity * self.cost_price
            with transaction.atomic():
                super().save(*args, **kwargs)
                Product.objects.filter(pk=self.product_id).update(stock=F("stock") - self.quantity)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # put the items back in stock
        with transaction.atomic():
            Product.objects.filter(pk=self.product_id).update(stock=F("stock") + self.quantity)
            return super().delete(*args, **kwargs)


class Expense(models.Model):
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES, default="Other")
    amount = models.DecimalField(**MONEY)
    description = models.CharField(max_length=200, blank=True)
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class AccountEntry(models.Model):
    """A balance-sheet figure entered by hand: cash, capital, loan, supplier dues, etc.

    Entries add up. Use a minus amount to reduce a figure (e.g. cash taken out).
    """
    kind = models.CharField(max_length=30, choices=ENTRY_KINDS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.amount}"
