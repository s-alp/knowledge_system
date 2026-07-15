from __future__ import annotations

"""Adapters that normalize uploaded files into the same shape as fetched URLs."""

import hashlib

from apps.viewer.domain.types import FetchedSource


def uploaded_file_to_fetched_source(uploaded_file) -> FetchedSource:
    # upload も URL 取得と同じ FetchedSource に寄せると、後続 service を共通化できる。
    content = uploaded_file.read()
    uploaded_file.seek(0)
    filename = uploaded_file.name
    mime_type = getattr(uploaded_file, "content_type", "application/octet-stream") or "application/octet-stream"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return FetchedSource(
        source_url=build_uploaded_source_url(filename, content),
        filename=filename,
        extension=extension,
        mime_type=mime_type.split(";")[0].strip().lower(),
        content=content,
    )


def build_uploaded_source_url(filename: str, content: bytes) -> str:
    # 実在 URL ではなく疑似 URL を作り、upload でも hash とキャッシュキーの形をそろえる。
    content_hash = hashlib.sha256(content + filename.encode("utf-8")).hexdigest()
    return f"https://local-upload.invalid/{content_hash}/{filename}"
