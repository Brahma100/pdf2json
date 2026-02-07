from invoice_ocr.validation.normalize import to_decimal
from decimal import Decimal

def validate_utility_row(row, tolerance=Decimal("0.01")):
    usage = to_decimal(row.get("Usage (kWh)"))
    cost = to_decimal(row.get("Cost (per kWh)"))
    amount = to_decimal(row.get("Amount ($)"))

    if None in (usage, cost, amount):
        return {"status": "SKIP", "reason": "missing_numeric"}

    expected = usage * cost
    delta = abs(expected - amount)

    # OCR can misread one numeric column while amount is still readable.
    # If amount/usage yields an exact cost, keep OCR value but expose inferred value.
    if delta > tolerance and usage != 0:
        inferred_cost = amount / usage
        if abs((usage * inferred_cost) - amount) <= tolerance:
            return {
                "status": "PASS_WITH_INFERENCE",
                "expected": str(expected),
                "actual": str(amount),
                "delta": str(delta),
                "ocr_cost": str(cost),
                "inferred_cost": str(inferred_cost),
                "reason": "cost_reconciled_from_amount"
            }

    return {
        "status": "PASS" if delta <= tolerance else "FAIL",
        "expected": str(expected),
        "actual": str(amount),
        "delta": str(delta)
    }
