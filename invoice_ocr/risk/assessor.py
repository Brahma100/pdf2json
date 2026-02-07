from invoice_ocr.risk.signal_extractor import extract_risk_signals
from invoice_ocr.risk.scorer import score_risk
from invoice_ocr.risk.ocr_confidence import average_ocr_confidence

def assess_risk(validation_report, ocr_blocks=None):
    avg_conf = average_ocr_confidence(ocr_blocks) if ocr_blocks else None
    signals = extract_risk_signals(validation_report, avg_conf)
    return score_risk(signals)
