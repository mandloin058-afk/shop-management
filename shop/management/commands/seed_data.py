from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import Customer, Expense, Payment, Product, Purchase, Sale


class Command(BaseCommand):
    help = "Adds sample products, purchases, sales, customer and expenses."

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Products already exist - sample data skipped.")
            return

        today = timezone.localdate()
        # name, purchase price, selling price, minimum stock
        items = [
            ("Basmati Rice 1kg", 90, 110, 5), ("Sugar 1kg", 40, 48, 10), ("Toor Dal 1kg", 120, 140, 5),
            ("Tea Powder 250g", 95, 115, 5), ("Soap Bar", 28, 35, 10), ("Biscuit Pack", 8, 10, 20),
            ("Cooking Oil 1L", 125, 145, 5),
        ]
        products = [Product.objects.create(name=n, purchase_price=c, selling_price=s, min_stock=m)
                    for n, c, s, m in items]

        # Buy stock (this increases product stock automatically)
        for p in products:
            Purchase.objects.create(supplier="Sharma Wholesale", product=p, quantity=30,
                                    purchase_price=p.purchase_price, date=today - timedelta(days=6))

        # A few days of cash/UPI sales (this decreases stock automatically)
        for d in range(5):
            for i, p in enumerate(products[:5]):
                Sale.objects.create(product=p, quantity=1 + (d + i) % 3, selling_price=p.selling_price,
                                    payment_method="UPI" if d % 2 else "Cash", date=today - timedelta(days=d))

        # Bulk sales so that a few products show up as low stock
        Sale.objects.create(product=products[4], quantity=12, selling_price=35, discount=10, date=today)
        Sale.objects.create(product=products[5], quantity=25, selling_price=10, date=today)

        # Udhaar customer
        ramesh = Customer.objects.create(name="Ramesh Kumar", mobile="9876543210")
        Sale.objects.create(customer=ramesh, product=products[2], quantity=3, selling_price=140,
                            payment_method="Udhaar", date=today - timedelta(days=2))
        Payment.objects.create(customer=ramesh, amount=100, date=today, note="Part payment")

        Expense.objects.create(category="Electricity", amount=450, description="Shop bill", date=today)
        Expense.objects.create(category="Transport", amount=150, description="Goods delivery", date=today)

        self.stdout.write(self.style.SUCCESS("Sample data added."))
