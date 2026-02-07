from invoice_ocr.table.geometry import center_y, y_close

def group_rows(blocks, header_y):
    rows = []

    for block in blocks:
        y = center_y(block["bbox"])

        # ignore header itself
        if y_close(y, header_y):
            continue

        placed = False
        for row in rows:
            if y_close(y, row["y"]):
                row["blocks"].append(block)
                placed = True
                break

        if not placed:
            rows.append({
                "y": y,
                "blocks": [block]
            })

    # sort top → bottom
    rows.sort(key=lambda r: r["y"])
    return rows
