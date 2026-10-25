import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("shop", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AccountEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[
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
                        ],
                        max_length=30,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("note", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-date", "-id"]},
        ),
    ]
