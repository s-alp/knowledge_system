from dataclasses import dataclass
import ipaddress
from pathlib import Path
from urllib.parse import urlparse

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.viewer.domain.types import ConversionResult, FetchedSource, StoredArtifact
from apps.viewer.services.converters import CadQueryOcctBackend

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


class FakeConverter:
    def convert(self, source_path: Path, source_extension: str, output_artifact: StoredArtifact) -> ConversionResult:
        output_artifact.absolute_path.write_bytes(b"solid converted")
        return ConversionResult(model_format="stl", artifact=output_artifact)


def test_open_3d_stl_job_and_download_model(monkeypatch):
    client = APIClient()
    fake_fetcher = FakeFetcher("model/stl", "mesh.stl", b"solid test")
    monkeypatch.setattr("apps.viewer.api.views.get_source_fetcher", lambda: fake_fetcher)

    response = client.post("/api/v1/viewer3d/open", {"url": "https://example.com/mesh.stl"}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["modelFormat"] == "stl"

    model_response = client.get(urlparse(payload["modelUrl"]).path)
    assert model_response.status_code == 200
    assert b"".join(model_response.streaming_content) == b"solid test"


def test_open_3d_step_job_uses_converter(monkeypatch):
    client = APIClient()
    fake_fetcher = FakeFetcher("application/step", "assy.step", b"ISO-10303-21;")
    monkeypatch.setattr("apps.viewer.api.views.get_source_fetcher", lambda: fake_fetcher)
    monkeypatch.setattr("apps.viewer.api.views.get_conversion_backend", lambda: FakeConverter())

    response = client.post("/api/v1/viewer3d/open", {"url": "https://example.com/assy.step"}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["modelFormat"] == "stl"


def test_upload_3d_step_job_uses_converter(monkeypatch):
    client = APIClient()
    monkeypatch.setattr("apps.viewer.api.views.get_conversion_backend", lambda: FakeConverter())
    upload = SimpleUploadedFile("assy.step", b"ISO-10303-21;", content_type="application/step")

    response = client.post("/api/v1/viewer3d/upload", {"file": upload}, format="multipart")

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["modelFormat"] == "stl"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content", "converter_factory", "expected_format"),
    [
        ("mesh.stl", "model/stl", b"solid test", None, "stl"),
        ("assy.step", "application/step", b"ISO-10303-21;", FakeConverter, "stl"),
    ],
)
def test_open_3d_job_accepts_allowlisted_internal_urls(
    monkeypatch,
    settings,
    filename: str,
    mime_type: str,
    content: bytes,
    converter_factory,
    expected_format: str,
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
    if converter_factory is not None:
        monkeypatch.setattr("apps.viewer.api.views.get_conversion_backend", lambda: converter_factory())

    response = client.post("/api/v1/viewer3d/open", {"url": f"https://fileserver.example.local/{filename}"}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == filename
    assert payload["modelFormat"] == expected_format


def test_open_3d_job_rejects_unallowlisted_internal_url(monkeypatch, settings):
    client = APIClient()
    settings.VIEWER_INTERNAL_URLS_ENABLED = True
    settings.VIEWER_INTERNAL_HOST_ALLOWLIST = ("viewer-demo.internal",)
    settings.VIEWER_INTERNAL_CIDR_ALLOWLIST = ()
    monkeypatch.setattr(
        "apps.viewer.services.fetchers._resolve_host_ips",
        lambda _hostname: {ipaddress.ip_address("10.10.4.20")},
    )

    response = client.post("/api/v1/viewer3d/open", {"url": "https://fileserver.example.local/mesh.stl"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "security_error"


def test_upload_3d_is_disabled_when_flag_is_false(settings):
    settings.VIEWER_LOCAL_FILE_ENABLED = False
    client = APIClient()
    upload = SimpleUploadedFile("mesh.stl", b"solid test", content_type="model/stl")

    response = client.post("/api/v1/viewer3d/upload", {"file": upload}, format="multipart")

    assert response.status_code == 404


def test_open_3d_job_from_drawing_id(monkeypatch):
    client = APIClient()
    drawing_id = "35463219-5fe5-49a0-ae7f-ed25c5661be9"
    fake_resolved = FakeResolvedDrawing(
        drawing_id=drawing_id,
        title="工程図",
        version="1",
        metadata={},
        source_2d_url=None,
        source_3d_url="https://example.com/model.stl",
    )
    fake_fetcher = FakeFetcher("model/stl", "model.stl", b"solid test")
    monkeypatch.setattr(
        "apps.viewer.api.views.get_pdm_drawing_resolver",
        lambda request: FakeDrawingResolver(fake_resolved),
    )
    monkeypatch.setattr("apps.viewer.api.views.get_source_fetcher", lambda: fake_fetcher)

    response = client.post(f"/api/v1/drawings/{drawing_id}/viewer3d/open", {}, format="json")

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["modelFormat"] == "stl"


def test_open_3d_job_from_drawing_id_rejects_missing_source(monkeypatch):
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

    response = client.post(f"/api/v1/drawings/{drawing_id}/viewer3d/open", {}, format="json")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_real_step_converter_smoke(tmp_path):
    cadquery = pytest.importorskip("cadquery")
    workplane = cadquery.Workplane("XY").box(1, 1, 1)
    source_path = tmp_path / "cube.step"
    output_path = tmp_path / "cube.stl"
    workplane.export(str(source_path))

    artifact = StoredArtifact(relative_path="cube.stl", absolute_path=output_path)
    result = CadQueryOcctBackend().convert(source_path, "step", artifact)

    assert result.model_format == "stl"
    assert output_path.exists()
