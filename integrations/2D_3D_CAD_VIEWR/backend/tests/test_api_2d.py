from dataclasses import dataclass
from io import BytesIO
import ipaddress
from urllib.parse import urlparse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image

from apps.viewer.domain.types import FetchedSource

pytestmark = pytest.mark.django_db


class FakeStreamingResponse:
    def __init__(self, content_type: str, content: bytes, status_code: int = 200):
        self.headers = {"Content-Type": content_type}
        self._content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 8192):
        for index in range(0, len(self._content), chunk_size):
            yield self._content[index : index + chunk_size]


def build_test_tiff_bytes() -> bytes:
    buffer = BytesIO()
    first = Image.new("RGB", (16, 16), "white")
    second = Image.new("RGB", (16, 16), "black")
    first.save(buffer, format="TIFF", save_all=True, append_images=[second], compression="tiff_lzw")
    return buffer.getvalue()


@dataclass
class FakeFetcher:
    mime_type: str
    filename: str
    content: bytes

    def fetch(self, source_url: str) -> FetchedSource:
        return FetchedSource(
            source_url=source_url,
            filename=self.filename,
            extension=self.filename.rsplit(".", 1)[-1],
            mime_type=self.mime_type,
            content=self.content,
        )


@dataclass
class FakeResolvedDrawing:
    drawing_id: str
    title: str
    version: str | None
    metadata: dict
    source_2d_url: str | None
    source_3d_url: str | None


class FakeDrawingResolver:
    def __init__(self, resolved: FakeResolvedDrawing):
        self.resolved = resolved

    def resolve(self, drawing_id: str) -> FakeResolvedDrawing:
        assert drawing_id == self.resolved.drawing_id
        return self.resolved


def test_open_2d_session_and_download_source(monkeypatch):
    client = APIClient()
    fake_fetcher = FakeFetcher("application/pdf", "drawing.pdf", b"%PDF-1.4 test")
    monkeypatch.setattr("apps.viewer.api.views.get_source_fetcher", lambda: fake_fetcher)

    response = client.post("/api/v1/viewer2d/open", {"url": "https://example.com/drawing.pdf"}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "drawing.pdf"
    assert payload["extension"] == "pdf"

    source_response = client.get(urlparse(payload["sourceUrl"]).path)
    assert source_response.status_code == 200
    assert b"".join(source_response.streaming_content) == b"%PDF-1.4 test"


def test_upload_2d_session_and_download_source():
    client = APIClient()
    upload = SimpleUploadedFile("local.pdf", b"%PDF-1.4 local", content_type="application/pdf")

    response = client.post("/api/v1/viewer2d/upload", {"file": upload}, format="multipart")

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "local.pdf"
    source_response = client.get(urlparse(payload["sourceUrl"]).path)
    assert source_response.status_code == 200
    assert b"".join(source_response.streaming_content) == b"%PDF-1.4 local"


def test_upload_tiff_session_exposes_page_images():
    client = APIClient()
    upload = SimpleUploadedFile(
        "local.tif",
        build_test_tiff_bytes(),
        content_type="image/tiff",
    )

    response = client.post("/api/v1/viewer2d/upload", {"file": upload}, format="multipart")

    assert response.status_code == 201
    payload = response.json()
    assert payload["extension"] == "tiff"
    assert payload["pageCount"] == 2
    assert len(payload["pageImageUrls"]) == 2

    page_response = client.get(urlparse(payload["pageImageUrls"][0]).path)
    assert page_response.status_code == 200
    assert page_response["Content-Type"] == "image/png"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content", "expected_extension", "expected_page_count"),
    [
        ("drawing.pdf", "application/pdf", b"%PDF-1.4 test", "pdf", 1),
        ("photo.jpeg", "image/jpeg", b"\xff\xd8\xff\xe0fakejpeg", "jpeg", 1),
        ("scan.tiff", "image/tiff", build_test_tiff_bytes(), "tiff", 2),
    ],
)
def test_open_2d_session_accepts_allowlisted_internal_urls(
    monkeypatch,
    settings,
    filename: str,
    mime_type: str,
    content: bytes,
    expected_extension: str,
    expected_page_count: int,
):
    client = APIClient()
    settings.VIEWER_INTERNAL_URLS_ENABLED = True
    settings.VIEWER_INTERNAL_HOST_ALLOWLIST = ("fileserver.example.local",)
    settings.VIEWER_INTERNAL_CIDR_ALLOWLIST = ()
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )
    monkeypatch.setattr(
        "apps.viewer.services.fetchers.requests.get",
        lambda source_url, timeout, stream: FakeStreamingResponse(mime_type, content),
    )

    response = client.post("/api/v1/viewer2d/open", {"url": f"https://fileserver.example.local/{filename}"}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == filename
    assert payload["extension"] == expected_extension
    assert payload["pageCount"] == expected_page_count
    assert len(payload["pageImageUrls"]) == (expected_page_count if expected_extension == "tiff" else 0)


def test_open_2d_session_rejects_unallowlisted_internal_url(monkeypatch, settings):
    client = APIClient()
    settings.VIEWER_INTERNAL_URLS_ENABLED = True
    settings.VIEWER_INTERNAL_HOST_ALLOWLIST = ("viewer-demo.internal",)
    settings.VIEWER_INTERNAL_CIDR_ALLOWLIST = ()
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )

    response = client.post("/api/v1/viewer2d/open", {"url": "https://fileserver.example.local/drawing.pdf"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "security_error"


def test_upload_2d_is_disabled_when_flag_is_false(settings):
    settings.VIEWER_LOCAL_FILE_ENABLED = False
    client = APIClient()
    upload = SimpleUploadedFile("local.pdf", b"%PDF-1.4 local", content_type="application/pdf")

    response = client.post("/api/v1/viewer2d/upload", {"file": upload}, format="multipart")

    assert response.status_code == 404


def test_bootstrap_returns_metadata_and_availability(monkeypatch):
    client = APIClient()
    drawing_id = "35463219-5fe5-49a0-ae7f-ed25c5661be9"
    fake_resolved = FakeResolvedDrawing(
        drawing_id=drawing_id,
        title="工程図",
        version="2",
        metadata={
            "drawingNumber": "PART-001",
            "drawingName": "工程図",
            "drawingType": "部品図",
            "paperSize": "A3",
            "status": "レビュー中",
            "owner": "創屋 太郎",
            "designPurpose": "加工確認",
            "tags": ["治具"],
        },
        source_2d_url="https://example.com/drawing.pdf",
        source_3d_url=None,
    )
    monkeypatch.setattr(
        "apps.viewer.api.views.get_pdm_drawing_resolver",
        lambda request: FakeDrawingResolver(fake_resolved),
    )

    response = client.get(f"/api/v1/drawings/{drawing_id}/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["drawingId"] == drawing_id
    assert payload["title"] == "工程図"
    assert payload["defaultMode"] == "2d"
    assert payload["availability"] == {"has2d": True, "has3d": False}
    assert payload["metadata"]["drawingNumber"] == "PART-001"


def test_open_2d_session_from_drawing_id(monkeypatch):
    client = APIClient()
    drawing_id = "35463219-5fe5-49a0-ae7f-ed25c5661be9"
    fake_resolved = FakeResolvedDrawing(
        drawing_id=drawing_id,
        title="工程図",
        version="1",
        metadata={},
        source_2d_url="https://example.com/from-pdm.pdf",
        source_3d_url=None,
    )
    fake_fetcher = FakeFetcher("application/pdf", "drawing.pdf", b"%PDF-1.4 test")
    monkeypatch.setattr(
        "apps.viewer.api.views.get_pdm_drawing_resolver",
        lambda request: FakeDrawingResolver(fake_resolved),
    )
    monkeypatch.setattr("apps.viewer.api.views.get_source_fetcher", lambda: fake_fetcher)

    response = client.post(f"/api/v1/drawings/{drawing_id}/viewer2d/open", {}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "drawing.pdf"
    assert payload["extension"] == "pdf"


def test_open_2d_session_from_drawing_id_rejects_missing_source(monkeypatch):
    client = APIClient()
    drawing_id = "35463219-5fe5-49a0-ae7f-ed25c5661be9"
    fake_resolved = FakeResolvedDrawing(
        drawing_id=drawing_id,
        title="工程図",
        version="1",
        metadata={},
        source_2d_url=None,
        source_3d_url=None,
    )
    monkeypatch.setattr(
        "apps.viewer.api.views.get_pdm_drawing_resolver",
        lambda request: FakeDrawingResolver(fake_resolved),
    )

    response = client.post(f"/api/v1/drawings/{drawing_id}/viewer2d/open", {}, format="json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
