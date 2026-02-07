from invoice_ocr.schema.base import TableSchema
from invoice_ocr.table.validators import is_number

class ProductInvoiceSchema(TableSchema):
    name = "product_invoice"

    header_keywords = [
        "qty", "quantity", "description", "unit", "price", "amount"
    ]

    required_columns = []

    numeric_columns = [
        "Qty", "Quantity", "Unit Price", "Amount",
        "Hrs/Qty", "Rate/Price", "Sub Total", "Subtotal"
    ]

    @classmethod
    def validate_row(cls, row):
        seen_numeric = False
        for col in cls.numeric_columns:
            if col in row:
                seen_numeric = True
                if not is_number(row[col]):
                    return False
        return seen_numeric
