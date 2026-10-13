import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

MONEY = dict(max_digits=10, decimal_places=2, validators=[django.core.validators.MinValueValidator(0)])
QTY = dict(validators=[django.core.validators.MinValueValidator(1)])
TOTAL = dict(max_digits=12, decimal_places=2, default=0, editable=False)
def ID():
    return models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", ID()),
                ("name", models.CharField(max_length=100)),
                ("mobile", models.CharField(blank=True, max_length=15)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", ID()),
                ("name", models.CharField(max_length=100, unique=True)),
                ("purchase_price", models.DecimalField(**MONEY)),
                ("selling_price", models.DecimalField(**MONEY)),
                ("stock", models.PositiveIntegerField(default=0, verbose_name="Current stock")),
                ("min_stock", models.PositiveIntegerField(default=5, verbose_name="Minimum stock")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", ID()),
                ("category", models.CharField(choices=[("Rent", "Rent"), ("Electricity", "Electricity"), ("Transport", "Transport"), ("Packaging", "Packaging"), ("Repairs", "Repairs"), ("Other", "Other")], default="Other", max_length=20)),
                ("amount", models.DecimalField(**MONEY)),
                ("description", models.CharField(blank=True, max_length=200)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", ID()),
                ("amount", models.DecimalField(**MONEY)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("note", models.CharField(blank=True, max_length=100)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="shop.customer")),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="Purchase",
            fields=[
                ("id", ID()),
                ("supplier", models.CharField(max_length=100)),
                ("quantity", models.PositiveIntegerField(**QTY)),
                ("purchase_price", models.DecimalField(**MONEY)),
                ("total", models.DecimalField(**TOTAL)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="shop.product")),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
        migrations.CreateModel(
            name="Sale",
            fields=[
                ("id", ID()),
                ("quantity", models.PositiveIntegerField(**QTY)),
                ("selling_price", models.DecimalField(**MONEY)),
                ("discount", models.DecimalField(default=0, **MONEY)),
                ("cost_price", models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10)),
                ("total", models.DecimalField(**TOTAL)),
                ("profit", models.DecimalField(**TOTAL)),
                ("payment_method", models.CharField(choices=[("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card"), ("Udhaar", "Udhaar")], default="Cash", max_length=10)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="shop.customer")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="shop.product")),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
    ]
