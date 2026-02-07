import cv2

from invoice_ocr.preprocess.deskew import deskew_image

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=False,
        )
    return _ocr


def run_text_ocr(image_path, enable_deskew=True, return_meta=False):
    ocr = get_ocr()
    img = cv2.imread(str(image_path))
    meta = {"deskew": {"applied": False, "enabled": bool(enable_deskew)}}
    if enable_deskew:
        img, deskew_meta = deskew_image(img)
        deskew_meta["enabled"] = True
        meta["deskew"] = deskew_meta

    result = ocr.ocr(img, cls=True)
    if return_meta:
        return result, meta
    return result
