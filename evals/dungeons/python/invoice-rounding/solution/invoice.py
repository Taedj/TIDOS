from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def _dec(value):
    return Decimal(str(value)) if isinstance(value, float) else Decimal(value)


def line_total(quantity, unit_price, vat_rate):
    total = _dec(quantity) * _dec(unit_price) * (1 + _dec(vat_rate))
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def invoice_total(lines):
    """lines: iterable of (quantity, unit_price, vat_rate)."""
    return sum((line_total(*line) for line in lines), Decimal("0.00")).quantize(CENT, rounding=ROUND_HALF_UP)
