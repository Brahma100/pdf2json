from invoice_ocr.table.schema import COLUMN_SCHEMA
from invoice_ocr.table.validators import is_number

def is_valid_row(record):
    if len(record) < 2:
        return False

    numeric_count = 0
    for col, value in record.items():
        col_type = COLUMN_SCHEMA.get(col)

        if col_type == "number":
            if not is_number(value):
                return False
            numeric_count += 1

    return numeric_count >= 1
