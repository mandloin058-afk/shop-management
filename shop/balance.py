"""Balance sheet arithmetic (no database code here, so it is easy to check)."""
from decimal import Decimal

ZERO = Decimal("0")


def compute(manual, receivable, inventory, earned):
    """Work out every balance-sheet line for one date.

    manual      dict kind -> total of the hand-entered amounts (see models.ENTRY_KINDS)
    receivable  customers' unpaid udhaar
    inventory   value of stock in hand
    earned      profit made so far (sales profit minus expenses)
    """
    def m(kind):
        return manual.get(kind) or ZERO

    r = {
        "cash": m("cash"),
        "receivable": receivable,
        "inventory": inventory,
        "other_current_asset": m("other_current_asset"),
        "ppe": m("ppe"),
        "depreciation": -m("accumulated_depreciation"),  # shown as "(Less ...)"
        "accounts_payable": m("accounts_payable"),
        "customer_credit": m("customer_credit"),
        "tax_payable": m("tax_payable"),
        "other_current_liability": m("other_current_liability"),
        "long_term_debt": m("long_term_debt"),
        "equity_capital": m("equity_capital"),
        "retained": earned + m("retained_earnings_opening"),
    }
    r["total_current_assets"] = r["cash"] + r["receivable"] + r["inventory"] + r["other_current_asset"]
    r["total_fixed_assets"] = r["ppe"] + r["depreciation"]
    r["total_assets"] = r["total_current_assets"] + r["total_fixed_assets"]
    r["total_current_liabilities"] = (r["accounts_payable"] + r["customer_credit"]
                                      + r["tax_payable"] + r["other_current_liability"])
    r["total_long_term_liabilities"] = r["long_term_debt"]
    r["total_liabilities"] = r["total_current_liabilities"] + r["total_long_term_liabilities"]
    r["total_equity"] = r["equity_capital"] + r["retained"]
    r["total_liabilities_equity"] = r["total_liabilities"] + r["total_equity"]
    r["difference"] = r["total_assets"] - r["total_liabilities_equity"]
    return r


# (label, kind, key). kind: head / sub / item / total / grand
LAYOUT = [
    ("Assets", "head", None),
    ("Current assets:", "sub", None),
    ("Cash / Bank", "item", "cash"),
    ("Account receivable (customers ka udhaar)", "item", "receivable"),
    ("Inventory (stock)", "item", "inventory"),
    ("Other current assets", "item", "other_current_asset"),
    ("Total current assets", "total", "total_current_assets"),
    ("Fixed assets:", "sub", None),
    ("Property, plant and equipment", "item", "ppe"),
    ("(Less accumulated depreciation)", "item", "depreciation"),
    ("Total fixed assets", "total", "total_fixed_assets"),
    ("Total assets", "grand", "total_assets"),
    ("Liabilities", "head", None),
    ("Current liabilities:", "sub", None),
    ("Accounts payable (suppliers ko baki)", "item", "accounts_payable"),
    ("Customer credit", "item", "customer_credit"),
    ("Tax payable (GST)", "item", "tax_payable"),
    ("Other current liabilities", "item", "other_current_liability"),
    ("Total current liabilities", "total", "total_current_liabilities"),
    ("Long term liabilities:", "sub", None),
    ("Long term debt", "item", "long_term_debt"),
    ("Total long term liabilities", "total", "total_long_term_liabilities"),
    ("Total liabilities", "grand", "total_liabilities"),
    ("Equity", "head", None),
    ("Equity capital", "item", "equity_capital"),
    ("Retained earnings (ab tak ka munafa)", "item", "retained"),
    ("Total equity", "total", "total_equity"),
    ("Total liabilities and equity", "grand", "total_liabilities_equity"),
]


def rows(columns):
    """Turn one or two compute() results into table rows for the template."""
    out = []
    for label, kind, key in LAYOUT:
        out.append({"label": label, "kind": kind,
                    "cells": [c[key] for c in columns] if key else []})
    return out
