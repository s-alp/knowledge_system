from __future__ import annotations

"""PDM drawing lookup adapter used by drawingId-based viewer entrypoints."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from django.http import HttpRequest

from apps.viewer.domain.types import ResolvedDrawing
from apps.viewer.services.errors import FetchError, NotFoundError


TWO_D_EXTENSIONS = {"pdf", "jpg", "jpeg", "tif", "tiff"}
THREE_D_EXTENSIONS = {"stl", "step", "stp"}


@dataclass(slots=True)
class PdmResolverConfig:
    base_url: str
    drawing_resolve_path_template: str
    timeout_seconds: int


class PdmDrawingResolver:
    def __init__(self, *, config: PdmResolverConfig, request: HttpRequest):
        self._config = config
        self._request = request

    def resolve(self, drawing_id: str) -> ResolvedDrawing:
        resolved_drawing_id = str(drawing_id)
        url = self._build_resolve_url(resolved_drawing_id)
        response = self._perform_request(url)
        payload = self._decode_json(response)
        return self._to_resolved_drawing(drawing_id=resolved_drawing_id, payload=payload)

    def _build_resolve_url(self, drawing_id: str) -> str:
        path = self._config.drawing_resolve_path_template.format(drawing_id=drawing_id).lstrip("/")
        return urljoin(f"{self._config.base_url.rstrip('/')}/", path)

    def _perform_request(self, url: str) -> requests.Response:
        headers = {"Accept": "application/json"}
        cookie_header = self._request.headers.get("Cookie")
        authorization_header = self._request.headers.get("Authorization")
        if cookie_header:
            headers["Cookie"] = cookie_header
        if authorization_header:
            headers["Authorization"] = authorization_header

        try:
            response = requests.get(url, headers=headers, timeout=self._config.timeout_seconds)
        except requests.Timeout as exc:
            raise FetchError("PDM API request timed out") from exc
        except requests.RequestException as exc:
            raise FetchError("Failed to fetch drawing detail from PDM API") from exc

        if response.status_code == 404:
            raise NotFoundError("Drawing not found")
        if response.status_code in {401, 403}:
            raise FetchError("Failed to authorize with PDM API")
        if response.status_code >= 400:
            raise FetchError(f"PDM API request failed with status {response.status_code}")
        return response

    @staticmethod
    def _decode_json(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise FetchError("PDM API returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise FetchError("PDM API returned unexpected payload")
        return payload

    def _to_resolved_drawing(self, *, drawing_id: str, payload: dict[str, Any]) -> ResolvedDrawing:
        source_2d_url, source_3d_url = self._resolve_source_urls(payload)
        title = self._first_text(
            payload.get("title"),
            payload.get("drawing_name"),
            payload.get("drawing_no"),
            drawing_id,
        )
        metadata = {
            "drawingNumber": self._first_text(payload.get("drawing_no")),
            "drawingName": self._first_text(payload.get("drawing_name")),
            "drawingType": self._nested_text(payload.get("drawing_type"), "type_name"),
            "paperSize": self._first_text(payload.get("paper_size")),
            "status": self._nested_text(payload.get("drawing_status"), "status"),
            "owner": self._owner_name(payload.get("owner")),
            "designPurpose": self._first_text(payload.get("intention")),
            "tags": self._coerce_tags(payload.get("tags")),
        }
        version = payload.get("version")
        return ResolvedDrawing(
            drawing_id=drawing_id,
            title=title,
            version=None if version in (None, "") else str(version),
            metadata=metadata,
            source_2d_url=source_2d_url,
            source_3d_url=source_3d_url,
        )

    def _resolve_source_urls(self, payload: dict[str, Any]) -> tuple[str | None, str | None]:
        top_level_2d = self._coerce_url(
            self._first_text(
                payload.get("source_2d_url"),
                payload.get("source2dUrl"),
                payload.get("viewer_2d_url"),
                payload.get("viewer2dUrl"),
            )
        )
        top_level_3d = self._coerce_url(
            self._first_text(
                payload.get("source_3d_url"),
                payload.get("source3dUrl"),
                payload.get("viewer_3d_url"),
                payload.get("viewer3dUrl"),
            )
        )
        if top_level_2d or top_level_3d:
            return top_level_2d, top_level_3d

        drawing_file_versions = payload.get("drawing_file_versions")
        if not isinstance(drawing_file_versions, list):
            return None, None

        source_2d_url: str | None = None
        source_3d_url: str | None = None
        for item in drawing_file_versions:
            if not isinstance(item, dict):
                continue
            candidate = self._coerce_url(
                self._first_text(
                    item.get("file_path"),
                    item.get("filePath"),
                    item.get("source_url"),
                    item.get("sourceUrl"),
                )
            )
            if not candidate:
                continue
            extension = self._extract_extension(
                self._first_text(item.get("file_name"), item.get("fileName"), candidate)
            )
            if not source_2d_url and extension in TWO_D_EXTENSIONS:
                source_2d_url = candidate
            if not source_3d_url and extension in THREE_D_EXTENSIONS:
                source_3d_url = candidate

        return source_2d_url, source_3d_url

    def _coerce_url(self, value: str | None) -> str | None:
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return urljoin(f"{self._config.base_url.rstrip('/')}/", value.lstrip("/"))

    @staticmethod
    def _first_text(*values: object) -> str | None:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _nested_text(value: object, key: str) -> str | None:
        if isinstance(value, dict):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        return None

    @staticmethod
    def _owner_name(value: object) -> str | None:
        if not isinstance(value, dict):
            return None
        last_name = value.get("last_name")
        first_name = value.get("first_name")
        parts = [part.strip() for part in (last_name, first_name) if isinstance(part, str) and part.strip()]
        return " ".join(parts) if parts else None

    @staticmethod
    def _coerce_tags(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        tags: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                tags.append(item.strip())
            elif isinstance(item, dict):
                tag_value = item.get("tag_name") or item.get("name") or item.get("value")
                if isinstance(tag_value, str) and tag_value.strip():
                    tags.append(tag_value.strip())
        return tags

    @staticmethod
    def _extract_extension(value: str | None) -> str:
        if not value or "." not in value:
            return ""
        normalized_value = value.split("?", 1)[0].split("#", 1)[0]
        return normalized_value.rsplit(".", 1)[-1].lower()
