from invoice_ocr.api import OCRConfig, process_document
from pathlib import Path


def convert(input_path: str | Path, enable_deskew: bool = True) -> dict:
    """
    Convert a PDF or image into structured JSON.

    Args:
        input_path (str | Path): PDF or image file

    Returns:
        dict: Unified JSON output
    """
    config = OCRConfig(enable_deskew=enable_deskew)
    return process_document(Path(input_path), config=config)
