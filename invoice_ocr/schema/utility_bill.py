from invoice_ocr.schema.base import TableSchema
from invoice_ocr.table.validators import is_number

class UtilityBillSchema(TableSchema):
    name = "utility_bill"

    header_keywords = [
        "date", "usage", "kwh", "cost", "rate", "amount"
    ]

    required_columns = ["Date", "Amount ($)"]

    numeric_columns = [
        "Usage (kWh)",
        "Cost (per kWh)",
        "Amount ($)"
    ]

    @classmethod
    def validate_row(cls, row):
        # numeric validation
        for col in cls.numeric_columns:
            if col in row and not is_number(row[col]):
                return False

        return super().validate_row(row)
