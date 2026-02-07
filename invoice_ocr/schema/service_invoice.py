from invoice_ocr.schema.base import TableSchema
from invoice_ocr.table.validators import is_number

class ServiceInvoiceSchema(TableSchema):
    name = "service_invoice"

    header_keywords = [
        "hour", "hrs", "service", "rate", "subtotal"
    ]

    required_columns = ["Service", "Subtotal"]

    numeric_columns = ["Hrs", "Rate", "Subtotal"]

    @classmethod
    def validate_row(cls, row):
        for col in cls.numeric_columns:
            if col in row and not is_number(row[col]):
                return False
        return True
