from invoice_ocr.table.geometry import center_x

def detect_columns(header_row):
    columns = []

    for block in header_row["blocks"]:
        bbox = block["bbox"]
        xmin = bbox[0][0] - 10
        xmax = bbox[1][0] + 10

        columns.append({
            "name": block["text"],
            "xmin": xmin,
            "xmax": xmax
        })

    # sort left → right
    columns.sort(key=lambda c: c["xmin"])
    return columns
