from __future__ import annotations

"""TIFF-specific helpers kept separate from generic 2D session handling."""

from io import BytesIO

from PIL import Image, ImageSequence

from apps.viewer.services.errors import ValidationError


def get_tiff_page_count(content: bytes) -> int:
    # TIFF のページ数確定は backend が担当し、frontend は count を受け取るだけにする。
    with Image.open(BytesIO(content)) as image:
        return sum(1 for _ in ImageSequence.Iterator(image))


def render_tiff_page_png(content: bytes, page_index: int) -> bytes:
    with Image.open(BytesIO(content)) as image:
        frame_count = sum(1 for _ in ImageSequence.Iterator(image))
        if page_index < 0 or page_index >= frame_count:
            raise ValidationError("TIFF page index is out of range")

        # ブラウザ依存を避けるため、表示時は毎回 PNG へ正規化して返す。
        image.seek(page_index)
        rendered = image.convert("RGBA")
        buffer = BytesIO()
        rendered.save(buffer, format="PNG")
        return buffer.getvalue()
