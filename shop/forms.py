from django import forms

from .models import Customer, Expense, Payment, Product, Purchase, Sale

DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class StyledForm(forms.ModelForm):
    """Adds Bootstrap classes to every field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            is_select = isinstance(field.widget, forms.Select)
            field.widget.attrs["class"] = "form-select" if is_select else "form-control"


class ProductForm(StyledForm):
    class Meta:
        model = Product
        fields = ["name", "purchase_price", "selling_price", "stock", "min_stock"]


class PurchaseForm(StyledForm):
    class Meta:
        model = Purchase
        fields = ["date", "supplier", "product", "quantity", "purchase_price"]
        widgets = {"date": DATE}


class SaleForm(StyledForm):
    class Meta:
        model = Sale
        fields = ["date", "product", "quantity", "selling_price", "discount", "payment_method", "customer"]
        widgets = {"date": DATE}
        labels = {"customer": "Customer (needed for Udhaar)"}

    def clean(self):
        data = super().clean()
        product, qty = data.get("product"), data.get("quantity")
        price, discount = data.get("selling_price"), data.get("discount") or 0
        if product and qty and qty > product.stock:
            self.add_error("quantity", f"Only {product.stock} in stock.")
        if qty and price is not None and discount > qty * price:
            self.add_error("discount", "Discount is more than the bill amount.")
        if data.get("payment_method") == "Udhaar" and not data.get("customer"):
            self.add_error("customer", "Select a customer for Udhaar sales.")
        return data


class CustomerForm(StyledForm):
    class Meta:
        model = Customer
        fields = ["name", "mobile"]


class PaymentForm(StyledForm):
    class Meta:
        model = Payment
        fields = ["amount", "date", "note"]
        widgets = {"date": DATE}

    def __init__(self, *args, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer = customer

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.customer and amount > self.customer.remaining:
            raise forms.ValidationError(f"Customer only owes ₹{self.customer.remaining}.")
        return amount


class ExpenseForm(StyledForm):
    class Meta:
        model = Expense
        fields = ["date", "category", "amount", "description"]
        widgets = {"date": DATE}
