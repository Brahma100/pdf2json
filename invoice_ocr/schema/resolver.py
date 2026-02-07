from invoice_ocr.schema.utility_bill import UtilityBillSchema
from invoice_ocr.schema.product_invoice import ProductInvoiceSchema
from invoice_ocr.schema.service_invoice import ServiceInvoiceSchema

SCHEMAS = [
    UtilityBillSchema,
    ProductInvoiceSchema,
    ServiceInvoiceSchema
]

def resolve_schema(columns):
    normalized = [c.lower() for c in (columns or [])]
    joined = " ".join(normalized)

    # Disambiguate common Quantity/Rate/Amount headers from utility bills.
    has_qty = any("qty" in c or "quantity" in c or "hrs/qty" in c for c in normalized)
    has_usage = any("usage" in c or "kwh" in c for c in normalized)
    has_invoice_signals = any(k in joined for k in ("item", "quantity", "rate", "amount"))
    if has_qty and not has_usage and has_invoice_signals:
        return ProductInvoiceSchema

    best_schema = None
    best_score = 0

    for schema in SCHEMAS:
        score = schema.match_score(columns)
        if score > best_score:
            best_score = score
            best_schema = schema

    # Tie-break for product-like headers when score equality leaves utility first.
    if best_schema is UtilityBillSchema and has_qty and not has_usage:
        return ProductInvoiceSchema

    return best_schema
