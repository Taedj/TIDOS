def line_total(quantity, unit_price, vat_rate):
    return quantity * unit_price * (1 + vat_rate)


def invoice_total(lines):
    """lines: iterable of (quantity, unit_price, vat_rate)."""
    return round(sum(line_total(*line) for line in lines), 2)
