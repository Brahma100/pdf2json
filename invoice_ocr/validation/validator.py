from invoice_ocr.validation.line_items import validate_utility_row
from invoice_ocr.validation.normalize import to_decimal
from invoice_ocr.validation.confidence import extract_confidence_map
from invoice_ocr.validation.document_extract import extract_document_enrichment
from invoice_ocr.validation.field_extract import extract_document_fields
from invoice_ocr.validation.summary_extract import extract_summary
from invoice_ocr.validation.summary_validate import validate_summary

def validate_document(schema, rows, ocr_blocks):
    line_reports = []

    for row in rows:
        row["_amount_decimal"] = to_decimal(row.get("Amount ($)"))
        if schema == "utility_bill":
            report = validate_utility_row(row)
            if report.get("inferred_cost"):
                row["_ocr_cost_per_kwh"] = row.get("Cost (per kWh)")
                row["_cost_per_kwh_inferred"] = report["inferred_cost"]
            line_reports.append(report)

    summary = extract_summary(ocr_blocks)
    fields = extract_document_fields(ocr_blocks)
    enrichment = extract_document_enrichment(ocr_blocks, fields)
    confidence_source = {
        "fields": fields,
        **enrichment,
        "summary": summary,
    }
    field_confidence = extract_confidence_map(confidence_source, ocr_blocks)
    summary_report = validate_summary(schema, rows, summary)


    return {
        "line_items": line_reports,
        "fields": fields,
        **enrichment,
        "summary": summary,
        "field_confidence": field_confidence,
        "summary_checks": summary_report
    }
