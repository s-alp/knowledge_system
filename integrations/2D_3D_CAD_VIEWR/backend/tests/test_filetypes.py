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
