from invoice_ocr.table.geometry import center_x, center_y

def is_row_aligned_with_columns(row, columns, tolerance=20):
    for block in row["blocks"]:
        cx = center_x(block["bbox"])
        for col in columns:
            if col["xmin"] - tolerance <= cx <= col["xmax"] + tolerance:
                return True
    return False
