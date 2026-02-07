import time
from pathlib import Path
from invoice_ocr.ocr.pipeline_pdf import run_ocr
from invoice_ocr.table.pipeline_tables import process_pages, apply_schema
from invoice_ocr.schema.universal import build_universal_invoice
from invoice_ocr.universal_engine import build_universal_document_output
from invoice_ocr.validation.validator import validate_document
from invoice_ocr.risk.assessor import assess_risk


def run_pipeline(input_path, enable_deskew=True):
    start = time.time()
    input_path = Path(input_path)

    # Phase 1–2: OCR
    ocr_result = run_ocr(input_path, enable_deskew=enable_deskew)

    # Phase 3–4: Tables + schema
    tables = process_pages(ocr_result["pages"])
    table = {
        "columns": list(tables[0].keys()) if tables else [],
        "rows": tables
    }
    table_out = apply_schema(table)

    # Phase 5: Validation
    validation = validate_document(
        table_out["schema"],
        table_out["rows"],
        ocr_result["blocks"]
    )

    # Phase 6: Risk
    risk = assess_risk(validation, ocr_result["blocks"])
    universal = build_universal_invoice(
        table_out["schema"],
        table_out,
        validation,
        ocr_result["blocks"]
    )

    end = time.time()
    out = build_universal_document_output(ocr_result, table_out, validation, risk)
    out["meta"]["processing_time_ms"] = int((end - start) * 1000)
    preprocess = ocr_result.get("preprocess", {})
    if isinstance(preprocess, dict):
        preprocess["version"] = out["meta"].get("preprocess", {}).get("version", "1.0.0")
    out["meta"]["preprocess"] = preprocess
    out["meta"]["legacy_universal"] = universal
    return out
