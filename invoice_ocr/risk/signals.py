RISK_SIGNALS = {
    "TOTAL_MISMATCH": {
        "weight": 0.25,
        "description": "Subtotal + tax does not equal total"
    },
    "LINE_ITEM_MISMATCH": {
        "weight": 0.20,
        "description": "Line item calculation mismatch"
    },
    "MISSING_SUMMARY": {
        "weight": 0.15,
        "description": "Summary totals missing"
    },
    "LOW_OCR_CONFIDENCE": {
        "weight": 0.10,
        "description": "OCR confidence below threshold"
    }
}
