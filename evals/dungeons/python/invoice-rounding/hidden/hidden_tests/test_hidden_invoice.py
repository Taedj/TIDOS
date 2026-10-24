from decimal import Decimal
from invoice import invoice_total, line_total

def test_line_total():
    assert line_total(3, "19.99", "0.19") == Decimal("71.36")
    assert isinstance(line_total(1, 1, 0), Decimal)

def test_half_up():
    assert invoice_total([(1, "0.125", "0")]) == Decimal("0.13")
    assert invoice_total([(1, 2.675, 0)]) == Decimal("2.68")

def test_float_inputs():
    assert invoice_total([(1, 0.1, 0), (1, 0.2, 0)]) == Decimal("0.30")

def test_rounds_each_line_first():
    # 2 lines of 0.005 -> each rounds to 0.01 -> 0.02 (not 0.01)
    assert invoice_total([(1, "0.005", 0), (1, "0.005", 0)]) == Decimal("0.02")

def test_empty():
    assert invoice_total([]) == Decimal("0.00")
