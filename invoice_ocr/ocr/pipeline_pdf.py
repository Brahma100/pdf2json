from invoice_ocr.ocr.run_text_ocr import run_text_ocr
from invoice_ocr.ocr.pdf_to_images import pdf_to_images


def run_ocr(input_path, enable_deskew=True):
    pages = pdf_to_images(input_path)
    all_pages = []
    all_blocks = []
    preprocess_pages = []

    for page_num, image_path in enumerate(pages, start=1):
        result, preprocess_meta = run_text_ocr(
            image_path,
            enable_deskew=enable_deskew,
            return_meta=True,
        )

        blocks = []
        for line in result[0]:
            bbox, (text, confidence) = line
            blocks.append({
                "text": text,
                "confidence": round(confidence, 3),
                "bbox": bbox,
                "page": page_num
            })

        all_pages.append({
            "page": page_num,
            "image": image_path.name,
            "blocks": blocks
        })
        preprocess_pages.append({
            "page": page_num,
            **preprocess_meta,
        })
        all_blocks.extend(blocks)

    return {
        "pages": all_pages,
        "blocks": all_blocks,
        "preprocess": {
            "deskew": {
                "enabled": bool(enable_deskew),
                "pages": preprocess_pages,
            }
        },
    }
