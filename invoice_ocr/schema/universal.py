import re
from datetime import datetime

from invoice_ocr.table.geometry import center_x, center_y, y_close


GSTIN_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")
MONEY_RE = re.compile(r"\$?\s*\d+(?:,\d{3})*(?:\.\d+)?")
CITY_STATE_POSTAL_RE = re.compile(r"^\s*(.*?)[,\s]+([A-Za-z]{2,})\s+(\d{4,10})\s*$")
ACC_RE = re.compile(r"(?:acc(?:ount)?\s*#?\s*)([0-9 ]{6,})", re.IGNORECASE)
BSB_RE = re.compile(r"(?:bsb\s*#?\s*)([0-9 ]{6,})", re.IGNORECASE)


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _norm_lower(text):
    return _norm(text).lower()


def _sanitize_email(text):
    m = EMAIL_RE.search(text or "")
    if not m:
        return None
    return re.sub(r"\s+", "", m.group(0)).lower()


def _money(value):
    return str(value) if value is not None else None


def _to_decimal_str(text):
    if text is None:
        return None
    s = str(text).replace("$", "").replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None
    return s


def _detect_currency(blocks):
    text = " ".join(_norm(b.get("text")) for b in blocks)
    has_usd = "$" in text
    has_eur = "€" in text
    has_gbp = "£" in text
    if has_usd and not has_eur and not has_gbp:
        return "USD"
    if has_eur and not has_usd and not has_gbp:
        return "EUR"
    if has_gbp and not has_usd and not has_eur:
        return "GBP"
    return None


def _extract_payment_terms_days(blocks):
    text = " ".join(_norm(b.get("text")) for b in blocks).lower()
    m = re.search(r"due\s+within\s+(\d+)\s+days", text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _was_email_normalized(email, blocks):
    if not email:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain:
        return False
    # Detect OCR forms like "admin @ slicedinvoices.com"
    patt = re.compile(
        rf"\b{re.escape(local)}\s*@\s*{re.escape(domain)}\b",
        re.IGNORECASE
    )
    compact = f"{local}@{domain}"
    for b in blocks:
        t = _norm(b.get("text"))
        if not t:
            continue
        if patt.search(t) and compact not in t:
            return True
    return False


def _extract_document_title(blocks):
    for b in blocks:
        t = _norm(b.get("text"))
        if t.lower() in ("invoice", "utility bill", "statement", "receipt"):
            return t
    return None


def _extract_label_map(blocks):
    lower = {_norm_lower(b.get("text")) for b in blocks}
    label_map = {}
    if "from:" in lower:
        label_map["seller"] = "From"
    if "to:" in lower:
        label_map["buyer"] = "To"
    elif "bill to:" in lower:
        label_map["buyer"] = "Bill To"
    return label_map or None


def _normalize_date_text(text):
    if not text:
        return None
    t = _norm(text).replace(",", "")
    for fmt in ("%b %d %Y", "%B %d %Y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(t, fmt)
            return d.strftime("%B %-d, %Y")
        except ValueError:
            continue
    # Windows strftime may not support %-d
    for fmt in ("%b %d %Y", "%B %d %Y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(t, fmt)
            return d.strftime("%B %d, %Y").replace(" 0", " ")
        except ValueError:
            continue
    return text


def _extract_header_invoice_number(blocks):
    for b in blocks:
        t = _norm(b.get("text"))
        m = re.fullmatch(r"#\s*([A-Za-z0-9-]+)", t)
        if m:
            return m.group(1)
    return None


def _extract_issue_date(blocks):
    v = _find_value_right_of_label(blocks, ["date:", "date"])
    return _normalize_date_text(v) if v else None


def _clean_address_line(text):
    t = _norm(text)
    t = re.sub(r",\s*e$", "", t, flags=re.IGNORECASE)
    t = t.replace("United.", "United")
    return t


def _find_value_right_of_label(blocks, label_keywords, y_tol=20):
    labels = [
        b for b in blocks
        if any(k in _norm_lower(b.get("text")) for k in label_keywords)
    ]
    for label in labels:
        ly = center_y(label["bbox"])
        lx = center_x(label["bbox"])
        page = label.get("page")

        cands = []
        for b in blocks:
            if b is label:
                continue
            if page is not None and b.get("page") != page:
                continue
            by = center_y(b["bbox"])
            bx = center_x(b["bbox"])
            if abs(by - ly) <= y_tol and bx > lx:
                text = _norm(b.get("text"))
                if text:
                    cands.append((bx - lx, text))
        if cands:
            cands.sort(key=lambda x: x[0])
            return cands[0][1]
    return None


def _variant_from_context(schema_name, blocks):
    joined = " ".join((b.get("text", "") for b in blocks)).lower()

    if "gst" in joined or GSTIN_RE.search(" ".join((b.get("text", "") for b in blocks))):
        return "gst"
    if "telecom" in joined or "phone bill" in joined or "mobile" in joined:
        return "telecom"
    if schema_name == "utility_bill" or "meter" in joined or "kwh" in joined:
        return "utility"
    return "generic"


def _extract_invoice_parties(blocks):
    from_label = next((b for b in blocks if _norm_lower(b.get("text")) == "from:"), None)
    to_label = next((b for b in blocks if _norm_lower(b.get("text")) == "to:"), None)
    bill_to_label = next((b for b in blocks if "bill to:" == _norm_lower(b.get("text"))), None)

    if not from_label and not to_label and not bill_to_label:
        return {}

    top_y = center_y(from_label["bbox"]) if from_label else None
    to_y = center_y(to_label["bbox"]) if to_label else None
    page = (from_label or to_label or bill_to_label).get("page")

    left_blocks = [
        b for b in blocks
        if b.get("page") == page and center_x(b["bbox"]) < 1200
    ]
    left_blocks.sort(key=lambda b: (center_y(b["bbox"]), center_x(b["bbox"])))

    vendor_lines = []
    buyer_lines = []

    if top_y is not None:
        end_y = to_y if to_y is not None else top_y + 500
        for b in left_blocks:
            y = center_y(b["bbox"])
            if y <= top_y:
                continue
            if y >= end_y:
                continue
            t = _norm(b.get("text"))
            if not t:
                continue
            vendor_lines.append(t)

    if to_y is not None:
        stop_y = to_y + 380
        table_header = next((b for b in left_blocks if _norm_lower(b.get("text")) in ("hrs/qty", "service")), None)
        if table_header is not None:
            stop_y = min(stop_y, center_y(table_header["bbox"]) - 20)
        for b in left_blocks:
            y = center_y(b["bbox"])
            if y <= to_y:
                continue
            if y >= stop_y:
                continue
            t = _norm(b.get("text"))
            if not t:
                continue
            if any(h in t.lower() for h in ("hrs/qty", "service", "rate/price", "sub total", "invoice date", "due date")):
                continue
            buyer_lines.append(t)

    # Fallback for invoice layouts with "Bill To:" and no explicit From/To pair.
    if not vendor_lines and bill_to_label is not None:
        by = center_y(bill_to_label["bbox"])
        # Seller name: highest left/top title-like text before Bill To.
        seller_candidates = []
        for b in left_blocks:
            t = _norm(b.get("text"))
            y = center_y(b["bbox"])
            if not t:
                continue
            if y >= by:
                continue
            if any(k in t.lower() for k in ("invoice", "date:", "#", "bill to:", "ship to:", "ship mode:")):
                continue
            seller_candidates.append((y, t))
        if seller_candidates:
            seller_candidates.sort(key=lambda x: x[0])
            vendor_lines = [seller_candidates[0][1]]

        # Buyer lines: right below Bill To until table section starts.
        item_header = next((b for b in blocks if _norm_lower(b.get("text")) == "item"), None)
        stop_y = center_y(item_header["bbox"]) - 20 if item_header is not None else by + 420
        for b in left_blocks:
            y = center_y(b["bbox"])
            if y <= by or y >= stop_y:
                continue
            t = _norm(b.get("text"))
            if not t:
                continue
            if any(k in t.lower() for k in ("ship to:", "ship mode:", "second class")):
                continue
            buyer_lines.append(t)

    def parse_party(lines):
        if not lines:
            return {"name": None, "address": {}}
        name_idx = 0
        for i, l in enumerate(lines):
            # Prefer person/org-like line over postal/zip-like line.
            if not re.match(r"^\d", l) and re.search(r"[A-Za-z]", l):
                name_idx = i
                break
        name = lines[name_idx]
        addr_lines = [l for i, l in enumerate(lines) if i != name_idx]
        email = None
        phone = None
        cleaned = []
        for l in addr_lines:
            se = _sanitize_email(l)
            if se:
                email = se
                continue
            pm = PHONE_RE.search(l)
            if pm:
                phone = pm.group(0)
                continue
            cleaned.append(_clean_address_line(l))

        address = {}
        if cleaned:
            address["line1"] = cleaned[0]
        if len(cleaned) > 1:
            address["line2"] = cleaned[1]
        if len(cleaned) > 2:
            m = CITY_STATE_POSTAL_RE.match(cleaned[2])
            if m:
                address["city"] = m.group(1).strip()
                address["state"] = m.group(2).strip()
                address["postal_code"] = m.group(3).strip()
            else:
                address["line3"] = cleaned[2]
        elif len(cleaned) > 1:
            m = CITY_STATE_POSTAL_RE.match(cleaned[1])
            if m:
                address["city"] = m.group(1).strip()
                address["state"] = m.group(2).strip()
                address["postal_code"] = m.group(3).strip()

        out = {"name": name, "address": address}
        if email:
            out["email"] = email
        if phone:
            out["phone"] = phone
        return out

    return {
        "seller": parse_party(vendor_lines),
        "buyer": parse_party(buyer_lines),
    }


def _extract_invoice_line_items(blocks):
    headers = {}
    for b in blocks:
        t = _norm_lower(b.get("text"))
        if t in ("hrs/qty", "service", "rate/price", "adjust", "sub total"):
            headers[t] = b

    required = ("hrs/qty", "service", "rate/price", "adjust", "sub total")
    if not all(k in headers for k in required):
        return []

    hy = center_y(headers["service"]["bbox"])
    x_qty = center_x(headers["hrs/qty"]["bbox"])
    x_service = center_x(headers["service"]["bbox"])
    x_rate = center_x(headers["rate/price"]["bbox"])
    x_adjust = center_x(headers["adjust"]["bbox"])
    x_subtotal = center_x(headers["sub total"]["bbox"])
    page = headers["service"].get("page")

    summary_start = None
    for b in blocks:
        if b.get("page") != page:
            continue
        t = _norm_lower(b.get("text"))
        if t == "sub total" and center_y(b["bbox"]) > hy + 80 and center_x(b["bbox"]) > x_rate:
            summary_start = center_y(b["bbox"])
            break
    if summary_start is None:
        summary_start = hy + 600

    row_blocks = [
        b for b in blocks
        if b.get("page") == page and (hy + 35) <= center_y(b["bbox"]) <= (summary_start - 20)
    ]
    rows = []
    for b in row_blocks:
        y = center_y(b["bbox"])
        placed = False
        for r in rows:
            if y_close(y, r["y"], tolerance=24):
                r["blocks"].append(b)
                placed = True
                break
        if not placed:
            rows.append({"y": y, "blocks": [b]})
    rows.sort(key=lambda r: r["y"])

    items = []
    for r in rows:
        rec = {}
        for b in r["blocks"]:
            x = center_x(b["bbox"])
            t = _norm(b.get("text"))
            if not t:
                continue
            if abs(x - x_qty) < 120:
                rec["quantity"] = _to_decimal_str(t)
            elif abs(x - x_service) < 280:
                if "description" in rec:
                    rec["description"] = f"{rec['description']} {t}".strip()
                else:
                    rec["description"] = t
            elif abs(x - x_rate) < 180:
                rec["unit_price"] = _to_decimal_str(t)
            elif abs(x - x_adjust) < 170:
                rec["adjustment_percent"] = _to_decimal_str(t.replace("%", ""))
            elif abs(x - x_subtotal) < 180:
                rec["line_total"] = _to_decimal_str(t)

        if rec.get("description") and not any(k in rec["description"].lower() for k in ("invoice date", "order number", "due date", "total due")):
            items.append(rec)
        elif rec.get("quantity") and rec.get("unit_price") and rec.get("line_total"):
            items.append(rec)

    merged = []
    for rec in items:
        if rec.get("quantity") and rec.get("unit_price") and rec.get("line_total"):
            merged.append(rec)
            continue
        if merged and rec.get("description") and "quantity" not in rec:
            if "description" in merged[-1]:
                merged[-1]["details"] = rec["description"]
            else:
                merged[-1]["description"] = rec["description"]
            continue
        merged.append(rec)

    return merged


def _extract_product_line_items(blocks):
    headers = {}
    for b in blocks:
        t = _norm_lower(b.get("text"))
        if t in ("item", "quantity", "rate", "amount"):
            headers[t] = b

    required = ("item", "quantity", "rate", "amount")
    if not all(k in headers for k in required):
        return []

    page = headers["item"].get("page")
    hy = center_y(headers["item"]["bbox"])
    x_item = center_x(headers["item"]["bbox"])
    x_qty = center_x(headers["quantity"]["bbox"])
    x_rate = center_x(headers["rate"]["bbox"])
    x_amount = center_x(headers["amount"]["bbox"])
    item_right = (x_item + x_qty) / 2
    qty_right = (x_qty + x_rate) / 2
    rate_right = (x_rate + x_amount) / 2

    summary_start = None
    for b in blocks:
        if b.get("page") != page:
            continue
        t = _norm_lower(b.get("text"))
        if t in ("subtotal:", "subtotal"):
            summary_start = center_y(b["bbox"])
            break
    if summary_start is None:
        summary_start = hy + 700

    row_blocks = [
        b for b in blocks
        if b.get("page") == page and (hy + 25) <= center_y(b["bbox"]) <= (summary_start - 15)
    ]
    rows = []
    for b in row_blocks:
        y = center_y(b["bbox"])
        placed = False
        for r in rows:
            if y_close(y, r["y"], tolerance=22):
                r["blocks"].append(b)
                placed = True
                break
        if not placed:
            rows.append({"y": y, "blocks": [b]})
    rows.sort(key=lambda r: r["y"])

    items = []
    for r in rows:
        rec = {}
        for b in r["blocks"]:
            x = center_x(b["bbox"])
            t = _norm(b.get("text"))
            if not t:
                continue
            if x <= item_right:
                if "description" in rec:
                    rec["description"] = f"{rec['description']} {t}".strip()
                else:
                    rec["description"] = t
            elif x <= qty_right:
                rec["quantity"] = _to_decimal_str(t)
            elif x <= rate_right:
                rec["unit_price"] = _to_decimal_str(t)
            else:
                rec["line_total"] = _to_decimal_str(t)

        if rec.get("description") and rec.get("quantity") and rec.get("unit_price") and rec.get("line_total"):
            items.append(rec)
            continue
        # Details/category rows beneath main item row
        if rec.get("description") and items:
            text = rec["description"]
            parts = [p.strip() for p in text.split(",")]
            if parts and re.fullmatch(r"[A-Z]{2,}-[A-Z]{2,}-\d+", parts[-1]):
                items[-1]["sku"] = parts[-1]
                if len(parts) > 1:
                    items[-1]["category"] = ", ".join(parts[:-1])
            else:
                items[-1]["details"] = text

    return items


def _extract_payment_status(blocks):
    for b in blocks:
        t = _norm_lower(b.get("text"))
        if t == "paid":
            return "paid"
        if re.search(r"\bpayment\s*status\b.*\bpaid\b", t):
            return "paid"
        if re.search(r"\bstatus\b.*\bpaid\b", t):
            return "paid"
        if re.search(r"\bpayment\s*received\b", t):
            return "paid"
    return None


def _extract_payment_details(blocks):
    bank = {}
    status = _extract_payment_status(blocks)
    acc_y = None
    bsb_y = None
    bsb_text = None

    for b in blocks:
        text = _norm(b.get("text"))
        if not text:
            continue

        m_acc = ACC_RE.search(text)
        if m_acc:
            bank["account_number"] = _norm(m_acc.group(1))
            acc_y = center_y(b["bbox"])
            continue

        m_bsb = BSB_RE.search(text)
        if m_bsb:
            bank["bsb"] = _norm(m_bsb.group(1))
            bsb_y = center_y(b["bbox"])
            bsb_text = text
            if re.search(r"\bpaid\b", text.lower()):
                status = "paid"

    if acc_y is not None:
        page = next((b.get("page") for b in blocks if ACC_RE.search(_norm(b.get("text")))), None)
        cands = []
        for b in blocks:
            if page is not None and b.get("page") != page:
                continue
            text = _norm(b.get("text"))
            if not text:
                continue
            y = center_y(b["bbox"])
            x = center_x(b["bbox"])
            if acc_y - 120 <= y <= acc_y and x < 900:
                if any(k in text.lower() for k in ("acc #", "account #", "bsb #")):
                    continue
                if MONEY_RE.search(text):
                    continue
                cands.append((abs(acc_y - y), x, text))
        if cands:
            cands.sort(key=lambda z: (z[0], z[1]))
            bank["name"] = cands[0][2]

    if status is None and bsb_text:
        if re.search(r"\bpaid\b", bsb_text.lower()):
            status = "paid"

    out = {"status": status}
    if bank:
        out["bank"] = bank
    return out


def build_universal_invoice(schema_name, table_out, validation, blocks):
    variant = _variant_from_context(schema_name, blocks)
    fields = validation.get("fields", {})
    summary = validation.get("summary", {})
    vendor = validation.get("vendor", {})
    field_conf = validation.get("field_confidence", {})

    parties = _extract_invoice_parties(blocks) if "invoice" in schema_name else {}
    line_items = table_out.get("rows", [])
    if schema_name == "product_invoice":
        extracted_items = _extract_product_line_items(blocks)
        if not extracted_items:
            extracted_items = _extract_invoice_line_items(blocks)
        if extracted_items:
            line_items = extracted_items

    invoice_id = (
        fields.get("invoice_number")
        or fields.get("account_no")
        or _find_value_right_of_label(blocks, ["invoice number", "invoice no"])
        or _extract_header_invoice_number(blocks)
    )
    issue_date = (
        fields.get("invoice_date")
        or fields.get("statement_date")
        or _find_value_right_of_label(blocks, ["invoice date"])
        or _extract_issue_date(blocks)
    )

    subtotal = (
        summary.get("subtotal")
        or summary.get("current_charges")
        or _find_value_right_of_label(blocks, ["sub total"])
    )
    order_number = fields.get("order_number") or _find_value_right_of_label(blocks, ["order number"])
    currency = _detect_currency(blocks)
    document_title = _extract_document_title(blocks)
    label_map = _extract_label_map(blocks)
    payment_terms_days = _extract_payment_terms_days(blocks)

    seller = {
        "name": parties.get("seller", {}).get("name") or vendor.get("name"),
        "address": parties.get("seller", {}).get("address") or vendor.get("address"),
        "phone": parties.get("seller", {}).get("phone") or vendor.get("phone"),
        "email": parties.get("seller", {}).get("email") or vendor.get("email"),
        "website": vendor.get("website"),
        "tax_id": None,
    }
    if seller.get("email"):
        seller["email_normalized"] = _was_email_normalized(seller["email"], blocks)

    buyer = {
        "name": parties.get("buyer", {}).get("name") or fields.get("account_name"),
        "address": parties.get("buyer", {}).get("address") or validation.get("customer_address_full", {}),
        "email": parties.get("buyer", {}).get("email"),
        "phone": parties.get("buyer", {}).get("phone"),
    }

    universal = {
        "schema_version": "1.1.0",
        "variant": variant,
        "invoice_id": invoice_id,
        "order_number": order_number,
        "document_title": document_title,
        "currency": currency,
        "label_map": label_map,
        "issue_date": issue_date,
        "due_date": fields.get("due_date"),
        "payment_terms_days": payment_terms_days,
        "seller": seller,
        "buyer": buyer,
        "line_items": line_items,
        "totals": {
            "subtotal": _money(subtotal),
            "shipping": _money(_to_decimal_str(_find_value_right_of_label(blocks, ["shipping:","shipping"]))),
            "tax": _money(summary.get("tax")),
            "total": _money(summary.get("total") or fields.get("total_due")),
            "previous_charges": _money(summary.get("previous_charges")),
            "current_charges": _money(summary.get("current_charges")),
            "subtotal_decimal": float(_to_decimal_str(subtotal)) if _to_decimal_str(subtotal) else None,
            "shipping_decimal": float(_to_decimal_str(_find_value_right_of_label(blocks, ["shipping:","shipping"]))) if _to_decimal_str(_find_value_right_of_label(blocks, ["shipping:","shipping"])) else None,
            "tax_decimal": float(_to_decimal_str(summary.get("tax"))) if _to_decimal_str(summary.get("tax")) else None,
            "total_decimal": float(_to_decimal_str(summary.get("total") or fields.get("total_due"))) if _to_decimal_str(summary.get("total") or fields.get("total_due")) else None,
        },
        "payments": _extract_payment_details(blocks),
        "payment_status": _extract_payment_status(blocks),
        "metadata": {
            "source_schema": schema_name,
            "section_flags": validation.get("sections", {}),
            "reminders": validation.get("reminders", []),
            "notes": validation.get("notes", []),
        },
        "confidence": {
            "invoice_id": field_conf.get("fields", {}).get("invoice_number") or field_conf.get("fields", {}).get("account_no"),
            "issue_date": field_conf.get("fields", {}).get("invoice_date") or field_conf.get("fields", {}).get("statement_date"),
            "due_date": field_conf.get("fields", {}).get("due_date"),
            "seller": field_conf.get("vendor", {}),
            "buyer": {
                "name": field_conf.get("fields", {}).get("account_name"),
                "address": field_conf.get("customer_address_full", {}),
            },
            "totals": field_conf.get("summary", {}),
        },
    }

    if schema_name == "utility_bill":
        # For utility documents, account number is not always the statement/bill id.
        universal["account_no"] = fields.get("account_no")
        universal["invoice_id"] = fields.get("statement_id")
        universal["line_item_source_priority"] = ["amount", "usage", "rate"]

        canonical_rows = []
        for row in universal["line_items"]:
            rec = dict(row)
            inferred = rec.get("_cost_per_kwh_inferred")
            ocr_cost = rec.get("_ocr_cost_per_kwh")
            if inferred is not None:
                original_cost = rec.get("Cost (per kWh)")
                rec["Cost (per kWh)"] = inferred
                rec["_ocr_cost_per_kwh"] = ocr_cost or original_cost
                rec["_cost_confidence"] = "inferred"
                rec["_source_priority"] = ["amount", "usage", "rate"]
            else:
                rec["_cost_confidence"] = "ocr"
                rec["_source_priority"] = ["ocr"]
            canonical_rows.append(rec)
        universal["line_items"] = canonical_rows

    if (
        schema_name == "product_invoice"
        and len(universal["line_items"]) == 1
        and universal["line_items"][0].get("line_total") is None
        and universal["totals"].get("subtotal") is not None
    ):
        universal["line_items"][0]["line_total"] = _to_decimal_str(universal["totals"]["subtotal"])

    raw_text = " ".join((b.get("text", "") for b in blocks))
    m = GSTIN_RE.search(raw_text)
    if variant == "gst" and m:
        universal["seller"]["tax_id"] = m.group(0)

    if variant == "telecom":
        universal["service_account"] = {
            "account_no": fields.get("account_no"),
            "period_from": fields.get("period_from"),
            "period_until": fields.get("period_until"),
        }

    if variant == "utility":
        universal["meter"] = {
            "period_from": fields.get("period_from"),
            "period_until": fields.get("period_until"),
        }

    return universal
