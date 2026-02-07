import cv2

from invoice_ocr.preprocess.deskew import deskew_image

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        try:
            from paddleocr import PaddleOCR
        except Exception as exc:
            raise RuntimeError(
                "PaddleOCR runtime is not available. Install Paddle dependencies for your OS. "
                "Windows: pip install paddlepaddle==2.6.2 paddleocr==2.7.0.3 ; "
                "macOS (Apple Silicon/Intel): pip install 'paddlepaddle>=3,<4' paddleocr==2.7.0.3"
            ) from exc

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
