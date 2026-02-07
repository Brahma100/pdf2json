from invoice_ocr.table.geometry import center_y, y_close

HEADER_KEYWORDS = [
    "date",
    "qty",
    "quantity",
    "description",
    "usage",
    "rate",
    "price",
    "unit price",
    "cost",
    "amount",
    "total"
]

def is_header_text(text):
    t = text.lower()
    return any(k in t for k in HEADER_KEYWORDS)

def detect_header_row(blocks):
    candidates = []

    for block in blocks:
        if is_header_text(block["text"]):
            candidates.append(block)

    # group header candidates by Y alignment
    header_rows = []
    for block in candidates:
        placed = False
        y = center_y(block["bbox"])

        for row in header_rows:
            if y_close(y, row["y"]):
                row["blocks"].append(block)
                placed = True
                break

        if not placed:
            header_rows.append({
                "y": y,
                "blocks": [block]
            })

    # pick the row with max header blocks
    if not header_rows:
        return None

    header_rows.sort(key=lambda r: len(r["blocks"]), reverse=True)
    best = header_rows[0]

    # require at least 3 headers to qualify
    return best if len(best["blocks"]) >= 3 else None
