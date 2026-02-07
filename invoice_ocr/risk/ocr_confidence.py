def average_ocr_confidence(blocks):
    if not blocks:
        return None

    total = sum(b.get("confidence", 0) for b in blocks)
    return total / len(blocks)
