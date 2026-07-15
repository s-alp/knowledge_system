from __future__ import annotations

"""Resolve incoming filename / MIME pairs into the viewer's supported types."""

from dataclasses import dataclass

from apps.viewer.domain.types import ResolvedFileType
from apps.viewer.services.errors import UnsupportedFormatError


@dataclass(slots=True)
class FileTypeResolver:
    def resolve(self, filename: str, mime_type: str) -> ResolvedFileType:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime = mime_type.lower()

        # URL 取得と upload の両方で同じ基準にしたいので、拡張子と MIME を両方見る。
        if extension in {"jpg", "jpeg"} or mime == "image/jpeg":
            return ResolvedFileType("2d", "jpeg", "image/jpeg")
        if extension in {"tif", "tiff"} or mime in {"image/tiff", "image/tif"}:
            return ResolvedFileType("2d", "tiff", "image/tiff")
        if extension == "pdf" or mime == "application/pdf":
            return ResolvedFileType("2d", "pdf", "application/pdf")
        if extension == "stl" or mime in {"model/stl", "application/sla", "application/vnd.ms-pki.stl"}:
            return ResolvedFileType("3d", "stl", "model/stl")
        if extension in {"step", "stp"} or mime in {"model/step", "application/step"}:
            return ResolvedFileType("3d", "step", "model/step")

        raise UnsupportedFormatError(f"Unsupported file type: {filename} ({mime_type})")
