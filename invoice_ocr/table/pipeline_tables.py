import json
from os import PathLike
from pathlib import Path

from invoice_ocr.table.table_builder import extract_table
from invoice_ocr.schema.resolver import resolve_schema


def _load_page_data(page_ref):
    """
    Accepts either:
    - in-memory page dict with a 'blocks' key (current pipeline), or
    - path to page JSON file (legacy pipeline).
    """
    if isinstance(page_ref, dict):
        return page_ref

    if isinstance(page_ref, (str, PathLike, Path)):
        with open(page_ref, encoding="utf-8") as f:
            return json.load(f)

    raise TypeError(
        f"Unsupported page reference type: {type(page_ref).__name__}. "
        "Expected dict or path-like value."
    )


def process_pages(page_refs):
    """
    Runs table extraction across multiple OCR pages.
    Handles multi-page continuation.
    """

    rows = []
    table_context = None

    for page_ref in page_refs:
        data = _load_page_data(page_ref)

        result = extract_table(data["blocks"], table_context)

        if result:
            rows.extend(result["rows"])
            table_context = result["context"]

    return rows


def apply_schema(table):
    """
    Applies dynamic schema resolution + validation.
    """

    schema = resolve_schema(table["columns"])

    if not schema:
        return {
            "schema": "generic",
            "columns": table["columns"],
            "rows": table["rows"],
        }

    valid_rows = [row for row in table["rows"] if schema.validate_row(row)]

    return {
        "schema": schema.name,
        "columns": table["columns"],
        "rows": valid_rows,
    }
