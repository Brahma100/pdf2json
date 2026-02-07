# invoice-ocr

CPU-only invoice OCR package for Windows (`Python 3.10.11`).

## Clean Project Structure

```text
invoice-ocrV2/
  invoice_ocr/
    __init__.py
    cli.py
    converter.py
    pipeline.py
    ocr/
      __init__.py
      *.py
    table/
      __init__.py
      *.py
    schema/
      __init__.py
      *.py
    validation/
      __init__.py
      *.py
    risk/
      __init__.py
      *.py
    utils/
      __init__.py
      *.py
  pyproject.toml
  README.md
  .gitignore
```

## Runtime Target

- OS: Windows
- Python: `3.10.11`
- Environment: `venv`
- Compute: CPU only (`use_gpu=False` in OCR code)

## Stable Dependency Set

- `numpy==1.26.4`
- `opencv-python-headless==4.10.0.84`
- `pdf2image>=1.17,<2`
- `Pillow>=10.3,<11`
- `paddlepaddle==2.6.2` (Windows, Py3.10)
- `paddleocr==2.7.0.3` (Windows)

These pins avoid NumPy 2.x migration risk and keep OpenCV/OCR compatibility conservative.

## Install (Windows PowerShell)

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

## Build Wheel/sdist

```powershell
python -m pip install build
python -m build
```

## CLI Usage

```powershell
invoice-ocr sample_invoice.pdf
invoice-ocr sample_invoice.pdf -o out.json
invoice-ocr sample_invoice.pdf -o out.json --disable-deskew
```

## Public Python API

```python
from invoice_ocr import OCRConfig, process_document, process_documents, DocumentIntelligenceEngine

# One-shot
result = process_document("sample_invoice.pdf", config=OCRConfig(enable_deskew=True))

# Batch
results = process_documents(["invoice.pdf", "invoice2.pdf"])

# Reusable engine
engine = DocumentIntelligenceEngine(config=OCRConfig(enable_deskew=True))
result = engine.process("sample_invoice.pdf")
```

## Inference and Risk Policy

- Inference is deterministic and auditable.
- Utility line-item reconciliation uses source priority:
  - `amount`
  - `usage`
  - `rate`
- Inferred values are explicitly recorded in:
  - `normalized.line_items[*]._cost_confidence`
  - `validation.inferred_fields[]`
- Risk scoring is rule-based and additive (see `docs/INFERENCE_AND_RISK_POLICY.md`).

## Golden Regression Suite

Run regression tests against known PDFs and golden expectations:

```powershell
python -m pytest tests/test_golden_regression.py -q
```

Golden fixtures:
- `tests/golden/sample_invoice_golden.json`
- `tests/golden/invoice_golden.json`
- `tests/golden/invoice2_golden.json`

## Deskew Preprocess

- Pre-OCR deskew is enabled by default.
- API: `convert("file.pdf", enable_deskew=True)`
- Output includes preprocessing telemetry in `meta.preprocess`.

## Note for PDF OCR

`pdf2image` requires Poppler binaries available on `PATH` in Windows.
