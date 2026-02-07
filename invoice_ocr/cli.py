import argparse
import json
from invoice_ocr import convert
from invoice_ocr.utils.json_encoder import DecimalEncoder


def main():
    parser = argparse.ArgumentParser(
        description="PDF/Image to JSON Invoice OCR Engine"
    )
    parser.add_argument("input", help="PDF or image file")
    parser.add_argument("-o", "--out", help="Output JSON file")
    parser.add_argument(
        "--disable-deskew",
        action="store_true",
        help="Disable pre-OCR deskew correction.",
    )

    args = parser.parse_args()

    result = convert(args.input, enable_deskew=not args.disable_deskew)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2, cls=DecimalEncoder)
    else:
        print(json.dumps(result, indent=2, cls=DecimalEncoder))
