from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db.models import QuerySet

from apps.drawing_metadata.models import RegisteredDrawing


@dataclass(frozen=True)
class DrawingScope:
    source_paths: frozenset[str] | None
    mode: str
    manifest_path: str
    manifest_source_count: int


def get_active_drawing_scope() -> DrawingScope:
    manifest_value = str(getattr(settings, "DRAWING_METADATA_HANDOFF_MANIFEST", "") or "").strip()
    if not manifest_value:
        return DrawingScope(source_paths=None, mode="all", manifest_path="", manifest_source_count=0)

    manifest_path = Path(manifest_value)
    if not manifest_path.is_file():
        return DrawingScope(
            source_paths=None,
            mode="all_manifest_missing",
            manifest_path=str(manifest_path),
            manifest_source_count=0,
        )

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_paths = frozenset(str(entry["sourcePath"]) for entry in payload.get("entries", []) if entry.get("sourcePath"))
    return DrawingScope(
        source_paths=source_paths,
        mode="manifest",
        manifest_path=str(manifest_path),
        manifest_source_count=len(source_paths),
    )


def apply_active_drawing_scope(queryset: QuerySet[RegisteredDrawing]) -> tuple[QuerySet[RegisteredDrawing], DrawingScope]:
    scope = get_active_drawing_scope()
    if scope.source_paths is None:
        return queryset, scope
    return queryset.filter(source_path__in=scope.source_paths), scope


def build_scope_payload(*, scope: DrawingScope, total_registration_count: int, scoped_registration_count: int) -> dict:
    return {
        "mode": scope.mode,
        "manifestPath": scope.manifest_path,
        "manifestSourceCount": scope.manifest_source_count,
        "totalRegistrationCount": total_registration_count,
        "scopedRegistrationCount": scoped_registration_count,
        "excludedRegistrationCount": max(total_registration_count - scoped_registration_count, 0),
    }
