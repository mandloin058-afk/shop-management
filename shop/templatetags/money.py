from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def inr(value):
    """12345678.5 -> ₹1,23,45,678.50 (Indian digit grouping)."""
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if d < 0 else ""
    whole, frac = f"{abs(d):.2f}".split(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"{sign}₹{whole}.{frac}"
