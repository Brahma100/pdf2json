import json
from pathlib import Path

from invoice_ocr import process_document


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "tests" / "golden"


def _read_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _dig(obj, path: str):
    cur = obj
    for token in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(token)]
        else:
            cur = cur[token]
    return cur


def _assert_golden(doc_path: str, golden_file: str):
    result = process_document(ROOT / doc_path)
    golden = _read_json(GOLDEN_DIR / golden_file)

    for key, expected in golden.items():
        actual = _dig(result, key)
        assert actual == expected, f"{doc_path}: {key} expected={expected!r} actual={actual!r}"


def test_sample_invoice_regression():
    _assert_golden("sample_invoice.pdf", "sample_invoice_golden.json")


def test_invoice_regression():
    _assert_golden("invoice.pdf", "invoice_golden.json")


def test_invoice2_regression():
    _assert_golden("invoice2.pdf", "invoice2_golden.json")
