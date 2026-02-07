def serialize_ocr(page_no, ocr_result, table_result):
    return {
        "page": page_no,
        "text_blocks": ocr_result,
        "tables": table_result
    }
