from __future__ import annotations

"""Shared datatypes passed between viewer services."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ViewerKind = Literal["2d", "3d"]
TwoDExtension = Literal["pdf", "jpeg", "tiff"]
ThreeDExtension = Literal["stl", "step"]
ThreeDModelFormat = Literal["stl"]


@dataclass(slots=True)
class FetchedSource:
    # URL 取得でも upload でも、この形にそろえば後段 service は入力元を意識しなくてよい。
    source_url: str
    filename: str
    extension: str
    mime_type: str
    content: bytes


@dataclass(slots=True)
class ResolvedFileType:
    # 拡張子のゆらぎを解消した、viewer 内部で使う判定結果。
    viewer_kind: ViewerKind
    normalized_extension: str
    mime_type: str


@dataclass(slots=True)
class StoredArtifact:
    # DB 保存用の relative_path と、実ファイル操作用の absolute_path を分けて持つ。
    relative_path: str
    absolute_path: Path


@dataclass(slots=True)
class ConversionResult:
    model_format: ThreeDModelFormat
    artifact: StoredArtifact


@dataclass(slots=True)
class ResolvedDrawing:
    drawing_id: str
    title: str
    version: str | None
    metadata: dict[str, Any]
    source_2d_url: str | None
    source_3d_url: str | None
