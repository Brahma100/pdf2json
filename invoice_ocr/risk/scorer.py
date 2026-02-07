from invoice_ocr.risk.signals import RISK_SIGNALS

def score_risk(signals):
    risk_score = 0.0
    explanations = {}

    for sig in set(signals):
        meta = RISK_SIGNALS.get(sig)
        if not meta:
            continue

        risk_score += meta["weight"]
        explanations[sig] = meta["description"]

    risk_score = min(risk_score, 1.0)
    confidence_score = round(1.0 - risk_score, 2)

    return {
        "confidence_score": confidence_score,
        "risk_score": round(risk_score, 2),
        "risk_flags": list(explanations.keys()),
        "explanations": explanations
    }
