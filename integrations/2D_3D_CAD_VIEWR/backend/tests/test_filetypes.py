"""test_filetypesの正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する。

テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。
外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。
"""
import pytest

from apps.viewer.services.errors import UnsupportedFormatError
from apps.viewer.services.filetypes import FileTypeResolver


def test_filetype_resolver_normalizes_extensions():
    resolver = FileTypeResolver()

    jpeg = resolver.resolve("photo.jpg", "image/jpeg")
    tiff = resolver.resolve("scan.tif", "image/tiff")
    step = resolver.resolve("assy.stp", "application/step")

    assert jpeg.normalized_extension == "jpeg"
    assert tiff.normalized_extension == "tiff"
    assert step.normalized_extension == "step"


def test_filetype_resolver_rejects_unknown_files():
    resolver = FileTypeResolver()

    with pytest.raises(UnsupportedFormatError):
        resolver.resolve("notes.txt", "text/plain")
