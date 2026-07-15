from __future__ import annotations

import uuid

import pytest
from django.test import RequestFactory

from apps.viewer.services.errors import FetchError, NotFoundError
from apps.viewer.services.pdm import PdmDrawingResolver, PdmResolverConfig


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


@pytest.fixture
def request_factory():
    return RequestFactory()


def build_resolver(request):
    return PdmDrawingResolver(
        config=PdmResolverConfig(
            base_url="http://210.165.3.139/api",
            drawing_resolve_path_template="/drawings/internals/{drawing_id}/",
            timeout_seconds=15,
        ),
        request=request,
    )


def test_resolver_forwards_cookie_and_authorization(monkeypatch, request_factory):
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse({"drawing_name": "テスト図面"})

    request = request_factory.get(
        "/api/v1/drawings/test/bootstrap",
        HTTP_COOKIE="refresh=abc; csrftoken=def",
        HTTP_AUTHORIZATION="Bearer viewer-token",
    )
    monkeypatch.setattr("apps.viewer.services.pdm.requests.get", fake_get)

    drawing_id = str(uuid.uuid4())
    resolver = build_resolver(request)
    resolved = resolver.resolve(drawing_id)

    assert resolved.drawing_id == drawing_id
    assert captured["url"] == f"http://210.165.3.139/api/drawings/internals/{drawing_id}/"
    assert captured["headers"]["Cookie"] == "refresh=abc; csrftoken=def"
    assert captured["headers"]["Authorization"] == "Bearer viewer-token"
    assert captured["timeout"] == 15


def test_resolver_extracts_metadata_and_source_urls(monkeypatch, request_factory):
    payload = {
        "drawing_name": "工程図",
        "drawing_no": "PART-001",
        "version": 3,
        "drawing_type": {"type_name": "部品図"},
        "drawing_status": {"status": "レビュー中"},
        "paper_size": "A3",
        "intention": "加工確認",
        "owner": {"last_name": "創屋", "first_name": "太郎"},
        "tags": [{"tag_name": "治具"}],
        "drawing_file_versions": [
            {"file_name": "part.pdf", "file_path": "/media/part.pdf"},
            {"file_name": "part.step", "file_path": "/media/part.step?download=1"},
        ],
    }

    monkeypatch.setattr("apps.viewer.services.pdm.requests.get", lambda url, headers, timeout: FakeResponse(payload))
    request = request_factory.get("/api/v1/drawings/test/bootstrap")
    resolver = build_resolver(request)

    resolved = resolver.resolve("35463219-5fe5-49a0-ae7f-ed25c5661be9")

    assert resolved.title == "工程図"
    assert resolved.version == "3"
    assert resolved.metadata["drawingNumber"] == "PART-001"
    assert resolved.metadata["drawingType"] == "部品図"
    assert resolved.metadata["status"] == "レビュー中"
    assert resolved.metadata["owner"] == "創屋 太郎"
    assert resolved.metadata["designPurpose"] == "加工確認"
    assert resolved.metadata["tags"] == ["治具"]
    assert resolved.source_2d_url == "http://210.165.3.139/api/media/part.pdf"
    assert resolved.source_3d_url == "http://210.165.3.139/api/media/part.step?download=1"


def test_resolver_raises_not_found_for_404(monkeypatch, request_factory):
    monkeypatch.setattr(
        "apps.viewer.services.pdm.requests.get",
        lambda url, headers, timeout: FakeResponse({"detail": "missing"}, status_code=404),
    )
    request = request_factory.get("/api/v1/drawings/test/bootstrap")
    resolver = build_resolver(request)

    with pytest.raises(NotFoundError):
        resolver.resolve("35463219-5fe5-49a0-ae7f-ed25c5661be9")


def test_resolver_raises_fetch_error_for_unauthorized(monkeypatch, request_factory):
    monkeypatch.setattr(
        "apps.viewer.services.pdm.requests.get",
        lambda url, headers, timeout: FakeResponse({"detail": "unauthorized"}, status_code=401),
    )
    request = request_factory.get("/api/v1/drawings/test/bootstrap")
    resolver = build_resolver(request)

    with pytest.raises(FetchError):
        resolver.resolve("35463219-5fe5-49a0-ae7f-ed25c5661be9")
