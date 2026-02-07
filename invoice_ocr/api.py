from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Union

from invoice_ocr.pipeline import run_pipeline

PathLike = Union[str, Path]


@dataclass(frozen=True)
class OCRConfig:
    enable_deskew: bool = True


class DocumentIntelligenceEngine:
    def __init__(self, config: OCRConfig | None = None):
        self.config = config or OCRConfig()

    def process(self, input_path: PathLike) -> dict:
        return run_pipeline(Path(input_path), enable_deskew=self.config.enable_deskew)

    def process_many(self, input_paths: Iterable[PathLike]) -> list[dict]:
        return [self.process(path) for path in input_paths]


def process_document(input_path: PathLike, config: OCRConfig | None = None) -> dict:
    engine = DocumentIntelligenceEngine(config=config)
    return engine.process(input_path)


def process_documents(
    input_paths: Iterable[PathLike],
    config: OCRConfig | None = None,
) -> list[dict]:
    engine = DocumentIntelligenceEngine(config=config)
    return engine.process_many(input_paths)
