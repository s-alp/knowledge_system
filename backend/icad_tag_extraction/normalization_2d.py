"""2D正規化の後方互換な内部入口を提供する。

呼び出し側が2Dの細分化を意識しなくてよいよう、セクション、図枠、形状の
各処理を同じ名前で再公開する。実装変更は責務に対応する各モジュールで行う。
"""
from __future__ import annotations

from icad_tag_extraction.normalization_2d_geometry import *  # noqa: F403
from icad_tag_extraction.normalization_2d_geometry import __all__ as _geometry_exports
from icad_tag_extraction.normalization_2d_identity import *  # noqa: F403
from icad_tag_extraction.normalization_2d_identity import __all__ as _identity_exports
from icad_tag_extraction.normalization_2d_sections import *  # noqa: F403
from icad_tag_extraction.normalization_2d_sections import __all__ as _section_exports

__all__ = [*_section_exports, *_identity_exports, *_geometry_exports]
