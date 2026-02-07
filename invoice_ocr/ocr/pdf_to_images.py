import os
import tempfile
from pathlib import Path

from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError


def _normalize_poppler_bin(path_value):
    if not path_value:
        return None

    candidate = Path(path_value)

    # Allow POPPLER_PATH to be either the bin directory or pdfinfo.exe itself.
    if candidate.name.lower() == "pdfinfo.exe" and candidate.exists():
        return str(candidate.parent)

    if (candidate / "pdfinfo.exe").exists():
        return str(candidate)

    return None


def _resolve_poppler_path():
    configured = os.getenv("POPPLER_PATH")
    configured_bin = _normalize_poppler_bin(configured)
    if configured_bin:
        return configured_bin

    local_appdata = os.getenv("LOCALAPPDATA")
    if not local_appdata:
        return None

    winget_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
    if not winget_root.exists():
        return None

    matches = sorted(
        winget_root.glob(
            "oschwartz10612.Poppler_*/*/Library/bin"
        ),
        reverse=True,
    )
    for candidate in matches:
        if (candidate / "pdfinfo.exe").exists():
            return str(candidate)

    return None


def pdf_to_images(pdf_path, out_dir=None):
    """
    Convert PDF to images.

    Args:
        pdf_path (Path): input PDF
        out_dir (Path | None): optional output directory

    Returns:
        list[Path]: image paths
    """
    if out_dir is None:
        out_dir = Path(tempfile.mkdtemp(prefix="invoice_ocr_"))
        print(f"PDF pages saved to {out_dir}")
    else:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    poppler_path = _resolve_poppler_path()
    kwargs = {"dpi": 300}
    if poppler_path:
        kwargs["poppler_path"] = poppler_path

    try:
        pages = convert_from_path(str(pdf_path), **kwargs)
    except PDFInfoNotInstalledError as exc:
        raise RuntimeError(
            "Poppler is required for PDF OCR. Install Poppler and either add its 'bin' "
            "folder to PATH or set POPPLER_PATH to that folder. Example: "
            "$env:POPPLER_PATH='C:\\poppler\\Library\\bin'"
        ) from exc

    image_paths = []
    for i, page in enumerate(pages, start=1):
        img_path = out_dir / f"page-{i}.png"
        page.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths
