from decimal import ROUND_HALF_UP, Decimal


def final_grade(marks, weights):
    if len(marks) != len(weights):
        raise ValueError("marks and weights differ in length")
    if any(w < 0 for w in weights) or not any(weights):
        raise ValueError("weights must be >= 0 and not all zero")
    values = [0 if m is None else m for m in marks]
    if any(not 0 <= m <= 20 for m in values):
        raise ValueError("marks must be within 0..20")
    mean = sum(Decimal(str(m)) * Decimal(str(w)) for m, w in zip(values, weights)) / sum(
        Decimal(str(w)) for w in weights)
    quarters = (mean * 4).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(quarters / 4)
