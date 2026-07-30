"""独立タグ生成コアへDjangoの規則バージョンを渡す互換adapter。"""
from __future__ import annotations

from apps.drawing_metadata.services.core_adapter import get_extraction_config
from icad_tag_extraction.configuration import ExtractionConfig
from icad_tag_extraction.tag_builder import build_derived_tags as _build_derived_tags


def build_derived_tags(
    canonical_attributes: dict,
    excluded_sources: set[str] | None = None,
    *,
    config: ExtractionConfig | None = None,
) -> list[dict]:
    """既存Django呼び出しを維持し、タグ生成本体は独立コアだけで実行する。"""

    return _build_derived_tags(
        canonical_attributes,
        excluded_sources=excluded_sources,
        config=config or get_extraction_config(),
    )


__all__ = ["build_derived_tags"]
