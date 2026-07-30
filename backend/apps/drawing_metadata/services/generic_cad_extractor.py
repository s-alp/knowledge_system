"""独立STEP/DXF抽出コアへDjangoのスキーマバージョンを渡す互換adapter。"""
from __future__ import annotations

from apps.drawing_metadata.services.core_adapter import get_extraction_config
from icad_tag_extraction.configuration import ExtractionConfig
from icad_tag_extraction.generic_cad_extractor import (
    extract_generic_cad_metadata as _extract_generic_cad_metadata,
)


def extract_generic_cad_metadata(
    *,
    input_path: str,
    source_format: str,
    source_kind: str,
    output_path,
    extraction_profile: str = "default",
    extraction_options: dict | None = None,
    config: ExtractionConfig | None = None,
) -> dict:
    """既存worker契約を維持し、ファイル解析本体は独立コアだけで実行する。"""

    return _extract_generic_cad_metadata(
        input_path=input_path,
        source_format=source_format,
        source_kind=source_kind,
        output_path=output_path,
        extraction_profile=extraction_profile,
        extraction_options=extraction_options,
        config=config or get_extraction_config(),
    )


__all__ = ["extract_generic_cad_metadata"]
