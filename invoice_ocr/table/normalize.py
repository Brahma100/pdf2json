def normalize_table(table):
    rows = []
    for row in table["res"]["cells"]:
        rows.append([cell["text"] for cell in row])
    return rows
