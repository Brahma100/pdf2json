import re
from datetime import datetime

from invoice_ocr.risk.ocr_confidence import average_ocr_confidence
from invoice_ocr.schema.universal import build_universal_invoice


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _slug(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")
    return s or "unknown_field"


def _to_float_list(values):
    out = [v for v in values if isinstance(v, (int, float))]
    return out


def _avg(values):
    vals = _to_float_list(values)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def _detect_languages(blocks):
    text = " ".join(b.get("text", "") for b in blocks)
    if not text:
        return [{"code": "unknown", "confidence": 0.0}]

    ascii_chars = sum(1 for ch in text if ord(ch) < 128)
    ratio = ascii_chars / max(len(text), 1)
    if ratio > 0.9:
        return [{"code": "en", "confidence": round(min(1.0, 0.8 + 0.2 * ratio), 3)}]
    return [{"code": "unknown", "confidence": 0.5}]


def _classify_document(schema_name, blocks, page_count):
    joined = " ".join(b.get("text", "") for b in blocks).lower()
    if schema_name and schema_name != "generic":
        doc_type = schema_name
        conf = 0.95
    elif "invoice" in joined:
        doc_type = "invoice"
        conf = 0.75
    elif "statement" in joined:
        doc_type = "statement"
        conf = 0.72
    elif "bill" in joined:
        doc_type = "bill"
        conf = 0.72
    else:
        doc_type = "unknown"
        conf = 0.5

    domain = "unknown"
    domain_conf = 0.5
    if any(x in joined for x in ("invoice", "bill", "tax", "amount", "charges", "statement")):
        domain = "finance"
        domain_conf = 0.86 if doc_type != "unknown" else 0.65
    elif "government" in joined:
        domain = "govt"
        domain_conf = 0.7
    elif "legal" in joined:
        domain = "legal"
        domain_conf = 0.7

    return {
        "document_type": doc_type if conf >= 0.7 else "unknown",
        "document_type_confidence": round(conf, 3),
        "domain": domain if domain_conf >= 0.7 else "unknown",
        "domain_confidence": round(domain_conf, 3),
        "pages": page_count,
        "languages": _detect_languages(blocks),
    }


def _detect_structure(pages, blocks, table_out, validation, normalized_line_items=None):
    headers = []
    footers = []
    repeated = {}

    for page in pages:
        pno = page.get("page")
        pblocks = [b for b in blocks if b.get("page") == pno]
        if not pblocks:
            continue
        ymax = max(max(pt[1] for pt in b["bbox"]) for b in pblocks)
        header_cut = ymax * 0.18
        footer_cut = ymax * 0.82

        for b in pblocks:
            cy = (b["bbox"][0][1] + b["bbox"][2][1]) / 2
            text = _norm(b.get("text"))
            if not text:
                continue
            if cy <= header_cut:
                headers.append({"page": pno, "text": text})
            if cy >= footer_cut:
                footers.append({"page": pno, "text": text})
            key = text.lower()
            repeated.setdefault(key, {"text": text, "pages": set()})
            repeated[key]["pages"].add(pno)

    repeated_blocks = [
        {"text": v["text"], "pages": sorted(v["pages"])}
        for v in repeated.values()
        if len(v["pages"]) > 1 and len(v["text"]) > 8
    ]

    sections = validation.get("sections", {})
    metadata_blocks = []
    for k, v in validation.get("fields", {}).items():
        metadata_blocks.append({"label": k, "value": str(v)})

    return {
        "headers": headers,
        "footers": footers,
        "tables": [{"schema": table_out.get("schema"), "columns": table_out.get("columns", [])}],
        "sections": sections,
        "line_items": normalized_line_items if normalized_line_items else table_out.get("rows", []),
        "summaries": validation.get("summary", {}),
        "metadata_blocks": metadata_blocks,
        "repeated_blocks": repeated_blocks,
    }


def _infer_type(key, value):
    s = str(value)
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", s) or re.fullmatch(r"[A-Za-z]+\s+\d{1,2},\s+\d{4}", s):
        return "date"
    if "@" in s:
        return "email"
    if re.fullmatch(r"\(\d{3}\)\s*\d{3}-\d{4}", s):
        return "phone"
    if re.fullmatch(r"\d+(\.\d+)?", s.replace(",", "").replace("$", "")):
        return "number"
    if any(x in key for x in ("address", "city", "state", "postal")):
        return "address"
    if any(x in key for x in ("id", "account", "no", "number", "reference")):
        return "identifier"
    return "text"


def _extract_fields_with_context(validation):
    field_conf = validation.get("field_confidence", {})
    out = []

    def add(path, value, conf):
        if value is None:
            return
        key = path.split(".")[-1]
        out.append({
            "key": path,
            "value": value,
            "inferred_type": _infer_type(path.lower(), value),
            "source_context": path.rsplit(".", 1)[0] if "." in path else "root",
            "confidence": conf,
        })

    for k, v in validation.get("fields", {}).items():
        add(f"fields.{k}", v, field_conf.get("fields", {}).get(k))

    for k, v in validation.get("summary", {}).items():
        add(f"summary.{k}", str(v), field_conf.get("summary", {}).get(k))

    for k, v in validation.get("vendor", {}).items():
        add(f"vendor.{k}", v, field_conf.get("vendor", {}).get(k))

    for k, v in validation.get("customer_address_full", {}).items():
        add(f"customer_address_full.{k}", v, field_conf.get("customer_address_full", {}).get(k))

    for idx, v in enumerate(validation.get("reminders", [])):
        conf = None
        arr = field_conf.get("reminders", [])
        if idx < len(arr):
            conf = arr[idx]
        add(f"reminders.{idx}", v, conf)

    for idx, v in enumerate(validation.get("notes", [])):
        conf = None
        arr = field_conf.get("notes", [])
        if idx < len(arr):
            conf = arr[idx]
        add(f"notes.{idx}", v, conf)

    return out


def _discover_unknown_fields(blocks, known_labels):
    unknown = {}
    for b in blocks:
        text = _norm(b.get("text"))
        if ":" not in text:
            continue
        label, value = text.split(":", 1)
        label = _norm(label).lower()
        value = _norm(value)
        if not label or not value:
            continue
        if label in known_labels:
            continue
        key = _slug(label)
        if key in unknown:
            continue
        unknown[key] = {
            "raw_label": label,
            "value": value,
            "normalized_key": key,
            "confidence": b.get("confidence"),
            "schema_discovery": True,
        }
    return dict(sorted(unknown.items(), key=lambda x: x[0]))


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%B %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def _build_validation(validation):
    checks = []
    mismatches = []
    inferred_fields = []

    for item in validation.get("line_items", []):
        ok = item.get("status") in ("PASS", "PASS_WITH_INFERENCE")
        checks.append({"name": "line_item_check", "passed": ok, "details": item})
        if item.get("status") == "PASS_WITH_INFERENCE":
            inferred_fields.append({
                "field": "line_items.cost_per_kwh",
                "reason": item.get("reason"),
                "ocr_value": item.get("ocr_cost"),
                "inferred_value": item.get("inferred_cost"),
                "source_priority": ["amount", "usage", "rate"],
            })
        if not ok:
            mismatches.append({
                "type": "LINE_ITEM_MISMATCH",
                "details": item,
            })

    total_match = validation.get("summary_checks", {}).get("total_match")
    if total_match is not None:
        checks.append({"name": "total_math_check", "passed": bool(total_match)})
        if not total_match:
            mismatches.append({
                "type": "TOTAL_MISMATCH",
                "details": validation.get("summary", {}),
            })

    fields = validation.get("fields", {})
    period_from = _parse_date(fields.get("period_from"))
    period_until = _parse_date(fields.get("period_until"))
    issue_date = _parse_date(fields.get("statement_date"))
    due_date = _parse_date(fields.get("due_date"))
    date_ok = True
    if period_from and period_until:
        date_ok = date_ok and (period_from <= period_until)
    if issue_date and due_date:
        date_ok = date_ok and (issue_date <= due_date)
    checks.append({"name": "date_range_check", "passed": date_ok})
    if not date_ok:
        mismatches.append({
            "type": "DATE_RANGE_INCONSISTENT",
            "details": {
                "period_from": fields.get("period_from"),
                "period_until": fields.get("period_until"),
                "statement_date": fields.get("statement_date"),
                "due_date": fields.get("due_date"),
            },
        })

    return {
        "checks": checks,
        "mismatches": mismatches,
        "inferred_fields": inferred_fields,
        "raw": validation,
    }


def _build_confidence(validation, blocks):
    field_conf = validation.get("field_confidence", {})
    section_level = {
        "fields": _avg((field_conf.get("fields", {}) or {}).values()),
        "vendor": _avg((field_conf.get("vendor", {}) or {}).values()),
        "summary": _avg((field_conf.get("summary", {}) or {}).values()),
        "reminders": _avg(field_conf.get("reminders", []) or []),
        "notes": _avg(field_conf.get("notes", []) or []),
    }

    overall = average_ocr_confidence(blocks)
    if overall is not None:
        overall = round(overall, 3)

    return {
        "field_level": field_conf,
        "section_level": section_level,
        "overall_document": overall,
    }


def _build_variant_data(universal):
    variant = universal.get("variant", "generic")
    out = {"variant": variant}
    if variant == "utility":
        out["utility"] = {"meter": universal.get("meter", {})}
    if variant == "telecom":
        out["telecom"] = {"service_account": universal.get("service_account", {})}
    if variant == "gst":
        out["gst"] = {"tax_id": (universal.get("seller") or {}).get("tax_id")}
    return out


def build_universal_document_output(ocr_result, table_out, validation, risk):
    blocks = ocr_result.get("blocks", [])
    pages = ocr_result.get("pages", [])
    schema_name = table_out.get("schema", "unknown")

    universal = build_universal_invoice(schema_name, table_out, validation, blocks)
    document = _classify_document(schema_name, blocks, len(pages))
    structure = _detect_structure(
        pages, blocks, table_out, validation, universal.get("line_items", [])
    )
    extracted_fields = _extract_fields_with_context(validation)

    known_labels = set(validation.get("fields", {}).keys())
    known_labels.update([
        "phone", "email", "website", "account no", "statement date", "due date",
        "invoice number", "invoice date", "order number", "total due"
    ])
    unknown_fields = _discover_unknown_fields(blocks, known_labels)

    normalized = {
        "seller": universal.get("seller"),
        "buyer": universal.get("buyer"),
        "document_title": universal.get("document_title"),
        "document_id": universal.get("invoice_id"),
        "order_number": universal.get("order_number"),
        "account_no": universal.get("account_no"),
        "currency": universal.get("currency"),
        "payment_terms_days": universal.get("payment_terms_days"),
        "label_map": universal.get("label_map"),
        "issue_date": universal.get("issue_date"),
        "due_date": universal.get("due_date"),
        "line_items": universal.get("line_items", []),
        "line_item_source_priority": universal.get("line_item_source_priority"),
        "totals": universal.get("totals", {}),
        "taxes": {"tax": (universal.get("totals") or {}).get("tax")},
        "payments": universal.get("payments") or {"status": universal.get("payment_status")},
        "period": universal.get("meter") or universal.get("service_account") or {},
        "notes": (universal.get("metadata") or {}).get("notes", []),
        "reminders": (universal.get("metadata") or {}).get("reminders", []),
    }

    extracted_content = {
        "structure": structure,
        "fields": extracted_fields,
        "logical_blocks": [
            {
                "page": b.get("page"),
                "text": _norm(b.get("text")),
                "confidence": b.get("confidence"),
            }
            for b in blocks
            if _norm(b.get("text"))
        ],
    }

    confidence = _build_confidence(validation, blocks)
    validation_out = _build_validation(validation)
    variant_data = _build_variant_data(universal)
    if unknown_fields:
        variant_data["schema_discovery"] = True

    return {
        "document": document,
        "extracted_content": extracted_content,
        "tables": [table_out],
        "normalized": normalized,
        "variant_data": variant_data,
        "unknown_fields": unknown_fields,
        "validation": validation_out,
        "confidence": confidence,
        "risk": risk,
        "meta": {
            "engine_version": "2.0.0",
            "schema_version": universal.get("schema_version", "1.1.0"),
            "ocr_engine": "PaddleOCR",
            "preprocess": {
                "version": "1.0.0",
            },
        },
    }
