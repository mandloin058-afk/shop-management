"""
Maheshwer/Karahi godown ki "purchase and labour" / "sell and labour" Excel
sheets se data uthake shop_management project me daalta hai.

IS FILE FORMAT KI PEHCHAN (teeno file isi tarah ki hain):
    Row1 = title (jaise "Maheshwer Godown purchase and Labour sheet")
    Row2 = header: Date | Product name | Q | Buy | payment | Labour payment | Name
    Row3 onwards = data. Jin rows me Date/Name khali hai wo pichli row ki
    hi continuation maani jati hain (jaise same din ka dusra kata-weighing).

    "purchase" wali file me:
      - har transaction row -> Purchase banta hai (supplier=Name column se)
      - har "Labour payment" cell -> ek alag Expense banta hai (gadi bhada,
        majduri, mandi tax, bardan/palli waghera — category guess se tag
        hoti hai, baad me Admin panel se sahi category chun lena)
    "sell" wali file me (title me "sell" shabd se pehchana jata hai):
      - har transaction row -> Sale banta hai (customer=None rakha hai
        kyunki in sheets me customer ka naam alag se nahi likha)
      - us row ke aur uske baad wali "Labour payment" cells (jab tak agli
        transaction row na aaye) sab milake Sale ke "discount" field me
        jud jati hain (gadi bhada/majduri jaisa extra kharcha, isi tarah
        pichli Makka Excel import me bhi kiya gaya tha)

KAHA RAKHNA HAI:
    shop/management/commands/import_godown_sheets.py
  (management aur commands folder nahi hai to pehle banao, dono me
   ek khali __init__.py file bhi honi chahiye)

KAISE CHALANA HAI (ek baar me 1 ya kai files de sakte ho):
    python manage.py import_godown_sheets "Maheshwer_godown_purchse_sheet.xlsx" "karahi_purchase_sheet.xlsx" "maheshwer__sell_sheet.xlsx"
"""
import re
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from shop.models import Expense, Product, Purchase, Sale


def D(value):
    """Plain float/int ko Decimal me convert karta hai (Django ke Decimal
    fields ke saath float ko seedha jodna/ghatana TypeError deta hai)."""
    return Decimal(str(round(value, 2)))

NUM = r"[\d,]+(?:\.\d+)?"
PRODUCT_NAME = "Makka (W)"  # same product jo pehle wale import_makka_excel se bana tha


def to_float(s):
    return float(str(s).replace(",", "").strip())


def parse_qty_kg(text):
    """'23.23 (Q)kg' jaisa cell -> Quintal hai, kg me convert karke return karta hai."""
    if not text:
        return None
    text = str(text)
    m = re.search(rf"({NUM})\s*\(\s*Q\s*\)\s*kg", text, re.IGNORECASE)
    if m:
        return to_float(m.group(1)) * 100
    m2 = re.search(NUM, text)
    return to_float(m2.group(0)) * 100 if m2 else None


def parse_rate(text):
    """'1701 rs/kg' ya '1670 kgrs/kg' jaise cell se pehla number nikalta hai."""
    if not text:
        return None
    m = re.search(NUM, str(text))
    return to_float(m.group(0)) if m else None


def parse_name(text):
    if text is None:
        return None
    s = str(text).strip()
    return s if s else None


def sum_money(text):
    """Cell me jitne bhi 'Rs' amount likhe hain sabka jod + ajeeb-se numbers ki list."""
    if not text:
        return 0.0, []
    nums = re.findall(NUM, str(text))
    suspicious = [n for n in nums if re.match(r"^\d+\.\d{3,}$", n)]
    return round(sum(to_float(n) for n in nums), 2), suspicious


def parse_date(val, fallback=None):
    if val is None:
        return fallback
    if isinstance(val, datetime):
        return val.date()
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return fallback


def guess_category(text):
    t = text.lower()
    if any(k in t for k in ("gadi", "bhada", "bhado", "dijal", "diesel", "tractor")):
        return "Transport"
    if any(k in t for k in ("bardan", "palli", "katt", "bori", "sutali", "bharne")):
        return "Packaging"
    if any(k in t for k in ("marmat", "repair")):
        return "Repairs"
    return "Other"


def detect_mode(ws):
    title = ""
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
        for c in row:
            if c:
                title += " " + str(c)
    return "sell" if "sell" in title.lower() else "purchase"


class Command(BaseCommand):
    help = "Import Maheshwer/Karahi godown purchase & sell Excel sheets into shop_management."

    def add_arguments(self, parser):
        parser.add_argument("xlsx_paths", nargs="+", type=str)

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError:
            raise CommandError("openpyxl install karo pehle: pip install openpyxl")

        product, created = Product.objects.get_or_create(
            name=PRODUCT_NAME,
            defaults={"purchase_price": 17, "selling_price": 18, "stock": 0, "min_stock": 500},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Product '{PRODUCT_NAME}' bana diya."))

        total_purchases = total_sales = total_expenses = 0

        for path in options["xlsx_paths"]:
            self.stdout.write(self.style.HTTP_INFO(f"\n--- Processing: {path} ---"))
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb["Sheet1"]
            mode = detect_mode(ws)
            self.stdout.write(f"Pehchana gaya type: {mode}")

            last_date = None
            last_name = None
            pending_sale = None

            def flush_sale():
                nonlocal total_sales
                if pending_sale:
                    Sale.objects.create(
                        customer=None,
                        product=product,
                        quantity=round(pending_sale["qty_kg"]),
                        selling_price=D(pending_sale["rate"]),
                        discount=D(pending_sale["discount"]),
                        payment_method="Cash",
                        date=pending_sale["date"],
                    )
                    total_sales += 1

            for row in ws.iter_rows(min_row=3, max_col=7, values_only=True):
                if all(c is None for c in row):
                    continue
                date_val, _prod, qty_text, rate_text, _payment_text, labour_text, name_text = row

                if date_val is not None:
                    d = parse_date(date_val, last_date)
                    if d:
                        last_date = d
                    last_name = parse_name(name_text)  # naya block -> purani party carry mat karo
                elif name_text:
                    last_name = parse_name(name_text)

                qty_kg = parse_qty_kg(qty_text)
                rate = parse_rate(rate_text)
                is_txn = qty_kg is not None and rate is not None

                if mode == "purchase":
                    if is_txn:
                        Purchase.objects.create(
                            supplier=last_name or "Unknown Supplier",
                            product=product,
                            quantity=round(qty_kg),
                            purchase_price=D(rate),
                            date=last_date,
                        )
                        total_purchases += 1
                    if labour_text:
                        amt, suspicious = sum_money(labour_text)
                        Expense.objects.create(
                            category=guess_category(str(labour_text)),
                            amount=D(amt),
                            description=str(labour_text).strip(),
                            date=last_date,
                        )
                        total_expenses += 1
                        if suspicious:
                            self.stdout.write(self.style.WARNING(
                                f"Check kar lena ye amount sahi se nikla ya nahi ({suspicious}): {labour_text!r}"
                            ))
                else:  # sell
                    if is_txn:
                        flush_sale()
                        amt, suspicious = sum_money(labour_text) if labour_text else (0.0, [])
                        pending_sale = {"date": last_date, "qty_kg": qty_kg, "rate": rate, "discount": amt}
                        if suspicious:
                            self.stdout.write(self.style.WARNING(
                                f"Check kar lena ye amount sahi se nikla ya nahi ({suspicious}): {labour_text!r}"
                            ))
                    elif labour_text and pending_sale is not None:
                        amt, suspicious = sum_money(labour_text)
                        pending_sale["discount"] += amt
                        if suspicious:
                            self.stdout.write(self.style.WARNING(
                                f"Check kar lena ye amount sahi se nikla ya nahi ({suspicious}): {labour_text!r}"
                            ))
                    elif labour_text:
                        # kisi sale se pehle hi labour cost mil gaya (rare) -> alag Expense bana do
                        amt, _ = sum_money(labour_text)
                        Expense.objects.create(
                            category=guess_category(str(labour_text)),
                            amount=D(amt),
                            description=str(labour_text).strip(),
                            date=last_date,
                        )
                        total_expenses += 1

            flush_sale()

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {total_purchases} purchase, {total_sales} sale, {total_expenses} expense entries import ho gaye."
        ))
        self.stdout.write(self.style.WARNING(
            "Dhyan rakhna: jahan Name column khali tha wahan supplier 'Unknown Supplier' save hua hai — "
            "Admin panel (/admin/) me jaake Purchases list se sahi party laga dena. Labour/kharche "
            "ek guess se category (Transport/Packaging/Other) me daale gaye hain, wo bhi check kar lena."
        ))
