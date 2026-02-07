# Inference and Risk Policy

## Scope
This policy defines when the engine may infer values, how it records those inferences, and how risk is scored.

## Inference Rules

1. Never overwrite OCR evidence silently.
2. Prefer explicit document values over inferred values.
3. Only infer when the relation is deterministic and auditable.
4. Every inferred field must record:
   - original OCR value
   - inferred value
   - reason
   - source priority used

### Utility line-item precedence
For utility line items:
1. `Amount`
2. `Usage`
3. `Rate`

If `usage * ocr_rate != amount` but `amount / usage` is exact within tolerance, the system:
- marks the item `PASS_WITH_INFERENCE`
- keeps OCR rate in `_ocr_cost_per_kwh`
- writes inferred canonical rate to `Cost (per kWh)`
- sets `_cost_confidence = "inferred"`
- logs the inference in `validation.inferred_fields[]`

## Compliance Rules

1. Payment status must not be inferred from reminders or due-date text.
2. Payment status is `null` unless an explicit payment marker exists.
3. Unknown fields are preserved under `unknown_fields` with `schema_discovery=true`.

## Risk Scoring Rules

Risk is additive and capped at `1.0`.

- `TOTAL_MISMATCH`: +0.25
- `LINE_ITEM_MISMATCH`: +0.20
- `MISSING_SUMMARY`: +0.15
- `LOW_OCR_CONFIDENCE`: +0.10

Output:
- `risk_score`
- `confidence_score = 1.0 - risk_score`
- `risk_flags`
- `explanations`

## Determinism Rules

1. No random thresholds at runtime.
2. Deskew gate is fixed (`0.7 <= abs(angle) <= 15.0`).
3. Inference reasons use stable enum-like labels (for example: `cost_reconciled_from_amount`).
