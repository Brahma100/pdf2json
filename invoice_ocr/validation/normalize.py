import re
from decimal import Decimal

def to_decimal(text):
    if text is None:
        return None
    text = text.replace(",", "").replace("$", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return Decimal(text)
