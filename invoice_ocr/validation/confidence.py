import re


def _normalize_text(value):
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value).strip()).lower()
    text = text.replace(",", "").replace("$", "")
    return text


def _best_block_confidence_for_value(value, blocks):
    target = _normalize_text(value)
    if not target:
        return None

    best = None
    for b in blocks:
        text = _normalize_text(b.get("text"))
        if not text:
            continue

        if target == text or target in text or text in target:
            conf = b.get("confidence")
            if conf is None:
                continue
            if best is None or conf > best:
                best = conf

    return round(best, 3) if best is not None else None


def _confidence_for_structure(value, blocks):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out[k] = _confidence_for_structure(v, blocks)
        return out

    if isinstance(value, list):
        return [_confidence_for_structure(v, blocks) for v in value]

    return _best_block_confidence_for_value(value, blocks)


def extract_confidence_map(data, blocks):
    return _confidence_for_structure(data, blocks)
