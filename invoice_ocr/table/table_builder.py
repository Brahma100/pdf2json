from invoice_ocr.table.geometry import center_x
from invoice_ocr.table.header_detector import detect_header_row
from invoice_ocr.table.columns import detect_columns
from invoice_ocr.table.rows import group_rows
from invoice_ocr.table.context import TableContext
from invoice_ocr.table.continuation import is_row_aligned_with_columns
from invoice_ocr.table.row_validator import is_valid_row

def assign_cells_to_columns(row, columns):
    record = {}

    for block in row["blocks"]:
        cx = center_x(block["bbox"])

        for col in columns:
            if col["xmin"] <= cx <= col["xmax"]:
                record[col["name"]] = block["text"]
                break

    return record

def extract_table(blocks, previous_context=None):
    header = detect_header_row(blocks)

    # CASE 1 — New table found
    if header:
        columns = detect_columns(header)
        rows = group_rows(blocks, header["y"])

        table_rows = []
        last_y = header["y"]

        for row in rows:
            record = assign_cells_to_columns(row, columns)
            if len(record) >= 2:
                table_rows.append(record)
                last_y = row["y"]

        context = TableContext(columns, last_y)

        return {
            "rows": table_rows,
            "context": context
        }

    # CASE 2 — No header, but continuation possible
    if previous_context:
        rows = group_rows(blocks, previous_context.last_y)

        continued_rows = []
        last_y = previous_context.last_y

        for row in rows:
            if is_row_aligned_with_columns(row, previous_context.columns):
                record = assign_cells_to_columns(row, previous_context.columns)
                if is_valid_row(record):
                    continued_rows.append(record)
        if continued_rows:
            previous_context.last_y = last_y
            return {
                "rows": continued_rows,
                "context": previous_context
            }

    return None