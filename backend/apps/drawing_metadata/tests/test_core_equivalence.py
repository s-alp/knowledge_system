"""独立PythonコアとDjango adapterが同じ結果を返すことを検証する。

代表2D・3D fixtureを両方の入口へ渡し、canonical属性とderived tagsの完全一致を確認する。
失敗時はDjango adapterが設定・辞書を変換する境界に差分が入っていないかを確認する。
"""
from __future__ import annotations

from pathlib import Path
import json

import pytest

from apps.drawing_metadata.services.core_adapter import get_normalization_dependencies
from apps.drawing_metadata.services.normalization import normalize_raw_extract as django_normalize
from apps.drawing_metadata.services.tag_builder import build_derived_tags as django_build_tags
from icad_tag_extraction.normalization import normalize_raw_extract as core_normalize
from icad_tag_extraction.tag_builder import build_derived_tags as core_build_tags


ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = ROOT / "scripts" / "fixtures" / "drawing_metadata"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fixture_name",
    ["sample_2d_extract.json", "sample_3d_extract.json"],
)
def test_django_adapter_matches_independent_core(fixture_name: str) -> None:
    payload = json.loads((FIXTURE_ROOT / fixture_name).read_text(encoding="utf-8"))
    config, provider = get_normalization_dependencies()

    core_canonical = core_normalize(
        payload,
        config=config,
        dictionary_provider=provider,
    )
    django_canonical = django_normalize(payload)
    assert django_canonical == core_canonical

    core_tags = core_build_tags(core_canonical, config=config)
    django_tags = django_build_tags(django_canonical)
    assert django_tags == core_tags
