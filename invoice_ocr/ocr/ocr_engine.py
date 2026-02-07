from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en",
    show_log=False,
    use_gpu=False
)

def run_ocr(image):
    return ocr.ocr(image, cls=True)
