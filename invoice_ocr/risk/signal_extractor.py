def extract_risk_signals(validation_report, avg_ocr_confidence=None):
    signals = []

    # summary mismatch
    if validation_report["summary_checks"].get("total_match") is False:
        signals.append("TOTAL_MISMATCH")

    # line item failures
    for item in validation_report["line_items"]:
        if item.get("status") == "FAIL":
            signals.append("LINE_ITEM_MISMATCH")
            break

    # missing summary
    if not validation_report.get("summary"):
        signals.append("MISSING_SUMMARY")

    # OCR confidence (optional)
    if avg_ocr_confidence is not None and avg_ocr_confidence < 0.85:
        signals.append("LOW_OCR_CONFIDENCE")

    return signals
