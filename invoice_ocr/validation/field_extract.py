from invoice_ocr.table.geometry import center_x, center_y
import re


FIELD_LABELS = {
    "invoice_number": ["invoice number", "invoice no"],
    "invoice_date": ["invoice date"],
    "order_number": ["order number"],
    "total_due": ["total due"],
    "account_no": ["account no", "account number"],
    "statement_date": ["statement date"],
    "account_name": ["account name"],
    "period_from": ["period statement from", "period from"],
    "period_until": ["period statement until", "period until"],
    "address": ["address"],
    "due_date": ["due date"],
}


FIELD_PATTERNS = {
    "invoice_number": re.compile(r"[A-Za-z]{2,}[-]?\d+|\d{4,}"),
    "invoice_date": re.compile(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}"),
    "total_due": re.compile(r"\$?\s*\d+(?:,\d{3})*(?:\.\d+)?"),
    "account_no": re.compile(r"\d{6,}"),
    "statement_date": re.compile(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}"),
    "period_from": re.compile(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}"),
    "period_until": re.compile(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}"),
    "due_date": re.compile(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}"),
}


def _all_keywords(field_labels):
    return [kw for labels in field_labels.values() for kw in labels]


def _is_valid_candidate(field_key, text, keywords):
    t = text.strip()
    if not t:
        return False

    lower = t.lower()
    if any(k in lower for k in keywords):
        return False

    pattern = FIELD_PATTERNS.get(field_key)
    if pattern is not None and pattern.search(t) is None:
        return False

    return True


def _extract_value_for_label(
    blocks, label_block, field_key, all_label_keywords, y_tol=20, x_tol=300, y_down=120
):
    ly = center_y(label_block["bbox"])
    lx = center_x(label_block["bbox"])
    page = label_block.get("page")

    candidates = []

    for b in blocks:
        if b is label_block:
            continue

        if page is not None and b.get("page") != page:
            continue

        by = center_y(b["bbox"])
        bx = center_x(b["bbox"])
        text = b["text"].strip()
        if not _is_valid_candidate(field_key, text, all_label_keywords):
            continue

        # Prefer value on same line, to the right of the label.
        if abs(by - ly) <= y_tol and bx > lx:
            score = (abs(by - ly) * 5) + (bx - lx)
            candidates.append((score, text))
            continue

        # Fallback: value appears directly below the label.
        if 0 < (by - ly) <= y_down and abs(bx - lx) <= x_tol:
            score = (abs(bx - lx) * 2) + (by - ly)
            candidates.append((score, text))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    return None


def extract_document_fields(blocks, field_labels=FIELD_LABELS):
    fields = {}
    label_keywords = _all_keywords(field_labels)

    for field_key, keywords in field_labels.items():
        labels = [
            b for b in blocks
            if any(k in b["text"].lower() for k in keywords)
        ]

        for label in labels:
            value = _extract_value_for_label(blocks, label, field_key, label_keywords)
            if value:
                fields[field_key] = value
                break

    return fields
