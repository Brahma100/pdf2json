import re

def is_number(text):
    if not text:
        return False
    text = text.replace(",", "").replace("$", "").strip()
    return re.fullmatch(r"\d+(\.\d+)?", text) is not None
