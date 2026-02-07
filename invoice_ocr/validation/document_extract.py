import re

from invoice_ocr.table.geometry import center_x, center_y


_PHONE_RE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"(?:https?://)?(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CITY_STATE_POSTAL_RE = re.compile(r"^\s*(.*?),\s*([A-Za-z][A-Za-z\s]+),\s*(\d{4,10})\s*$")
_REMINDER_RE = re.compile(r"^\s*\d+\.\s*(.+)")


def _sorted_page_blocks(blocks, page):
    page_blocks = [b for b in blocks if b.get("page") == page and b.get("text", "").strip()]
    page_blocks.sort(key=lambda b: (center_y(b["bbox"]), center_x(b["bbox"])))
    return page_blocks


def _get_contact_value(blocks, regex):
    for b in blocks:
        m = regex.search(b.get("text", ""))
        if m:
            return m.group(0)
    return None


def _extract_vendor(blocks):
    page1 = _sorted_page_blocks(blocks, 1)
    from_label = next((b for b in page1 if b["text"].strip().lower() == "from:"), None)
    to_label = next((b for b in page1 if b["text"].strip().lower() == "to:"), None)

    if from_label is not None:
        fy = center_y(from_label["bbox"])
        stop_y = center_y(to_label["bbox"]) if to_label is not None else fy + 500
        left = [
            b for b in page1
            if center_x(b["bbox"]) < 1200 and fy < center_y(b["bbox"]) < stop_y
        ]
        left.sort(key=lambda b: (center_y(b["bbox"]), center_x(b["bbox"])))

        lines = [b["text"].strip() for b in left if b["text"].strip()]
        name = lines[0] if lines else None
        addr = []
        email = None
        phone = None
        for ln in lines[1:]:
            em = _EMAIL_RE.search(ln)
            if em:
                email = re.sub(r"\s+", "", em.group(0)).lower()
                continue
            ph = _PHONE_RE.search(ln)
            if ph:
                phone = ph.group(0)
                continue
            if "invoice date" in ln.lower() or "order number" in ln.lower():
                continue
            addr.append(ln)

        inv_vendor = {
            "name": name,
            "address": ", ".join(addr[:3]) if addr else None,
            "phone": phone,
            "email": email,
            "website": None,
        }
        inv_vendor = {k: v for k, v in inv_vendor.items() if v}
        if inv_vendor:
            return inv_vendor

    top = [b for b in page1 if center_y(b["bbox"]) < 360]
    name = None
    for b in top:
        text = b["text"].strip()
        if "company" in text.lower():
            name = text
            break

    address_lines = []
    if name:
        name_block = next((b for b in top if b["text"].strip() == name), None)
        if name_block is not None:
            nx = center_x(name_block["bbox"])
            ny = center_y(name_block["bbox"])
            for b in top:
                text = b["text"].strip()
                if not text or b is name_block:
                    continue
                by = center_y(b["bbox"])
                bx = center_x(b["bbox"])
                if by > ny and abs(bx - nx) < 220:
                    if _PHONE_RE.search(text) or _EMAIL_RE.search(text) or "website" in text.lower():
                        continue
                    address_lines.append((by, text))
            address_lines.sort(key=lambda x: x[0])

    website = None
    for b in blocks:
        text = b.get("text", "")
        if "website" in text.lower():
            m = _URL_RE.search(text)
            if m:
                website = m.group(0)
                break
    if website is None:
        for b in blocks:
            text = b.get("text", "")
            if "@" in text:
                continue
            m = _URL_RE.search(text)
            if m and "." in m.group(0):
                website = m.group(0)
                break

    vendor = {
        "name": name,
        "address": ", ".join([t for _, t in address_lines[:2]]) if address_lines else None,
        "phone": _get_contact_value(blocks, _PHONE_RE),
        "email": _get_contact_value(blocks, _EMAIL_RE),
        "website": website,
    }
    return {k: v for k, v in vendor.items() if v}


def _extract_customer_address_full(blocks, fields):
    street = fields.get("address")
    line2 = None

    if street:
        for b in _sorted_page_blocks(blocks, 1):
            text = b["text"].strip()
            if street.lower() == text.lower():
                sy = center_y(b["bbox"])
                sx = center_x(b["bbox"])
                for c in _sorted_page_blocks(blocks, 1):
                    t = c["text"].strip()
                    if not t:
                        continue
                    cy = center_y(c["bbox"])
                    cx = center_x(c["bbox"])
                    if 0 < (cy - sy) <= 100 and abs(cx - sx) <= 300:
                        if "period statement" in t.lower() or "date" in t.lower():
                            continue
                        line2 = t
                        break
                break

    parsed = {
        "street": street,
        "city": None,
        "state": None,
        "postal_code": None,
        "full": ", ".join([x for x in (street, line2) if x]),
    }

    if line2:
        m = _CITY_STATE_POSTAL_RE.match(line2)
        if m:
            parsed["city"] = m.group(1).strip()
            parsed["state"] = m.group(2).strip()
            parsed["postal_code"] = m.group(3).strip()

    return {k: v for k, v in parsed.items() if v}


def _extract_sections(blocks):
    low = " ".join([b.get("text", "").lower() for b in blocks])
    return {
        "meter_information": "meter information" in low,
        "bill_summary": "bill summary" in low,
        "reminders": "reminders" in low,
    }


def _extract_reminders_and_notes(blocks):
    page2 = _sorted_page_blocks(blocks, 2)
    reminders = []
    notes = []

    i = 0
    while i < len(page2):
        b = page2[i]
        text = b["text"].strip()
        if not text:
            i += 1
            continue
        r = _REMINDER_RE.match(text)
        if r:
            reminder = r.group(1).strip()
            j = i + 1
            while j < len(page2):
                nxt = page2[j]["text"].strip()
                if _REMINDER_RE.match(nxt):
                    break
                if "for any questions" in nxt.lower() or "acme company" in nxt.lower() or "jotform" in nxt.lower():
                    break
                if nxt:
                    reminder = f"{reminder} {nxt}".strip()
                j += 1
            reminders.append(reminder)
            i = j
            continue

        if (
            "for any questions" in text.lower()
            or "if you have any questions" in text.lower()
            or "present your statement" in text.lower()
            or "please check your online accounts" in text.lower()
        ):
            notes.append(text)
        i += 1

    return {
        "reminders": reminders,
        "notes": notes,
    }


def extract_document_enrichment(blocks, fields):
    extra = {}

    vendor = _extract_vendor(blocks)
    if vendor:
        extra["vendor"] = vendor

    customer_full = _extract_customer_address_full(blocks, fields)
    if customer_full:
        extra["customer_address_full"] = customer_full

    extra["sections"] = _extract_sections(blocks)

    rn = _extract_reminders_and_notes(blocks)
    if rn["reminders"]:
        extra["reminders"] = rn["reminders"]
    if rn["notes"]:
        extra["notes"] = rn["notes"]

    return extra
