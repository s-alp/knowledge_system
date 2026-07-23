from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.drawing_metadata.models import (
    EXTRACTION_MODE_2D,
    EXTRACTION_MODE_3D,
    DrawingMetadataExtractionJob,
    RegisteredDrawing,
)
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.persistence import save_extraction_snapshot
from apps.drawing_metadata.services.tag_builder import build_derived_tags


MODE_FILENAME_HINTS = {
    EXTRACTION_MODE_2D: ("_2d", "-2d", ".2d", "source_kind\": \"2d"),
    EXTRACTION_MODE_3D: ("_3d", "-3d", ".3d", "source_kind\": \"3d"),
}


class Command(BaseCommand):
    help = "抽出済み CAD メタデータ JSON を RegisteredDrawing / Snapshot へ取り込みます。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("json_paths", nargs="*", help="抽出済み JSON ファイルまたはディレクトリ。")
        parser.add_argument("--manifest", action="append", default=[], help="代表抽出JSON manifest。複数指定できます。")
        parser.add_argument(
            "--filename",
            action="append",
            default=[],
            help="manifest取込を指定したCADファイル名に限定します。複数指定できます。",
        )
        parser.add_argument(
            "--manifest-mode",
            choices=[EXTRACTION_MODE_2D, EXTRACTION_MODE_3D],
            help="manifest内のselectedFilesを指定modeだけに限定します。",
        )
        parser.add_argument("--glob", default="*.json", help="ディレクトリ指定時の検索パターン。既定は *.json。")
        parser.add_argument("--mode", choices=[EXTRACTION_MODE_2D, EXTRACTION_MODE_3D], help="全入力に適用する抽出mode。")
        parser.add_argument(
            "--skip-unknown-mode",
            action="store_true",
            help="modeを判定できないJSONをエラーにせずスキップします。",
        )
        parser.add_argument(
            "--use-json-path-as-source",
            action="store_true",
            help="JSON内に元ICADパスが無い場合だけ、JSONファイル自身のパスを source_path として使います。",
        )
        parser.add_argument("--executed-by", default="import_drawing_metadata_extracts")
        parser.add_argument(
            "--rebind-moved-source",
            action="store_true",
            help="source_path不一致時、同名図面が1件だけなら移動後パスへ付け替えます。",
        )

    def handle(self, *args, **options) -> None:
        input_specs = [(path, None) for path in self._collect_input_files(options["json_paths"], options["glob"])]
        input_specs.extend(
            self._collect_manifest_files(
                options["manifest"],
                options["filename"],
                options["manifest_mode"],
            )
        )
        deduplicated: dict[Path, str | None] = {}
        for input_file, source_path_override in input_specs:
            if input_file not in deduplicated or source_path_override:
                deduplicated[input_file] = source_path_override
        input_specs = sorted(deduplicated.items(), key=lambda item: item[0])
        if not input_specs:
            raise CommandError("取り込み対象JSONが見つかりません。")

        imported = 0
        created_drawings = 0
        updated_drawings = 0
        skipped = 0

        for input_file, source_path_override in input_specs:
            payload = self._load_payload(input_file)
            extraction_mode = options["mode"] or self._detect_mode(payload, input_file)
            if not extraction_mode:
                if options["skip_unknown_mode"]:
                    skipped += 1
                    self.stdout.write(f"SKIPPED unknown mode: {input_file}")
                    continue
                raise CommandError(f"抽出modeを判定できません: {input_file}")

            if "raw_extract" not in payload or not isinstance(payload["raw_extract"], dict):
                raise CommandError(f"raw_extract が存在しない、またはdictではありません: {input_file}")

            source_path = source_path_override or self._source_path(
                payload,
                input_file,
                options["use_json_path_as_source"],
            )
            source_file = self._source_file_payload(payload, source_path)
            raw_extract = dict(payload["raw_extract"])
            raw_extract["_source_file"] = source_file
            normalize_payload = dict(payload)
            normalize_payload["source_file"] = source_file
            normalize_payload["raw_extract"] = raw_extract

            with transaction.atomic():
                drawing, drawing_created, drawing_updated = self._upsert_drawing(
                    source_path=source_path,
                    filename=source_file["file_name"],
                    source_format=payload.get("source_format") or "icad",
                    rebind_moved_source=options["rebind_moved_source"],
                )
                job = self._create_import_job(
                    drawing=drawing,
                    extraction_mode=extraction_mode,
                    payload=payload,
                    executed_by=options["executed_by"],
                )
                canonical_attributes = normalize_raw_extract(normalize_payload)
                derived_tags = build_derived_tags(canonical_attributes)
                save_extraction_snapshot(
                    drawing=drawing,
                    extraction_mode=extraction_mode,
                    job=job,
                    raw_extract=raw_extract,
                    canonical_attributes=canonical_attributes,
                    derived_tags=derived_tags,
                    executed_by=options["executed_by"],
                )

            imported += 1
            created_drawings += int(drawing_created)
            updated_drawings += int(drawing_updated)
            self.stdout.write(f"IMPORTED {extraction_mode}: {source_file['file_name']} <= {input_file}")

        self.stdout.write(
            self.style.SUCCESS(
                "completed import "
                f"imported={imported} created_drawings={created_drawings} "
                f"updated_drawings={updated_drawings} skipped={skipped} total={len(input_specs)}"
            )
        )

    def _collect_input_files(self, raw_paths: list[str], glob_pattern: str) -> list[Path]:
        input_files: list[Path] = []
        for raw_path in raw_paths:
            path = Path(raw_path).expanduser()
            if not path.exists():
                raise CommandError(f"指定パスが存在しません: {path}")
            if path.is_file():
                input_files.append(path.resolve())
                continue
            if path.is_dir():
                input_files.extend(sorted(item.resolve() for item in path.rglob(glob_pattern) if item.is_file()))
                continue
            raise CommandError(f"指定パスがファイルでもディレクトリでもありません: {path}")
        return sorted(dict.fromkeys(input_files))

    def _collect_manifest_files(
        self,
        raw_manifest_paths: list[str],
        filenames: list[str],
        manifest_mode: str | None,
    ) -> list[tuple[Path, str | None]]:
        input_specs: list[tuple[Path, str | None]] = []
        for raw_manifest_path in raw_manifest_paths:
            manifest_path = Path(raw_manifest_path).expanduser()
            if not manifest_path.exists():
                raise CommandError(f"manifest が存在しません: {manifest_path}")
            payload = self._load_payload(manifest_path)
            entries = payload.get("entries", []) or []
            if filenames:
                requested_filenames = set(filenames)
                entries = [
                    entry
                    for entry in entries
                    if PureWindowsPath(str(entry.get("sourcePath") or "")).name in requested_filenames
                ]
            manifest_specs = [
                (selected_file.get("path"), entry.get("sourcePath"))
                for entry in entries
                for selected_file in entry.get("selectedFiles", []) or []
                if manifest_mode is None or selected_file.get("mode") == manifest_mode
            ]
            if not manifest_specs:
                paths = payload.get("selectedPaths")
                if paths is None:
                    paths = []
                if not isinstance(paths, list):
                    raise CommandError(f"manifest の selectedPaths がlistではありません: {manifest_path}")
                manifest_specs = [(path, None) for path in paths]
            for raw_path, source_path_override in manifest_specs:
                if not raw_path:
                    continue
                path = Path(str(raw_path)).expanduser()
                if not path.exists():
                    raise CommandError(f"manifest 内のJSONが存在しません: {path}")
                if not path.is_file():
                    raise CommandError(f"manifest 内のパスがファイルではありません: {path}")
                input_specs.append((path.resolve(), str(source_path_override) if source_path_override else None))
        return input_specs

    def _load_payload(self, input_file: Path) -> dict:
        try:
            payload = json.loads(input_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSONを読めません: {input_file}: {exc}") from exc
        if not isinstance(payload, dict):
            raise CommandError(f"JSONルートがdictではありません: {input_file}")
        return payload

    def _detect_mode(self, payload: dict, input_file: Path) -> str | None:
        source_kind = str(payload.get("source_kind") or "").lower()
        if source_kind in {EXTRACTION_MODE_2D, EXTRACTION_MODE_3D}:
            return source_kind
        lowered_name = input_file.name.lower()
        for mode, hints in MODE_FILENAME_HINTS.items():
            if any(hint in lowered_name for hint in hints[:3]):
                return mode
        return None

    def _source_path(self, payload: dict, input_file: Path, use_json_path_as_source: bool) -> str:
        raw_extract = payload.get("raw_extract", {}) or {}
        source_file = payload.get("source_file", {}) or raw_extract.get("_source_file", {}) or {}
        source_path = payload.get("input_path") or source_file.get("full_path")
        if source_path:
            return str(source_path)
        if use_json_path_as_source:
            return str(input_file)
        raise CommandError(f"元CADパスを判定できません: {input_file}")

    def _source_file_payload(self, payload: dict, source_path: str) -> dict:
        windows_path = PureWindowsPath(source_path)
        file_name = windows_path.name
        return {
            "full_path": source_path,
            "directory_path": str(windows_path.parent),
            "file_name": file_name,
            "file_name_without_extension": windows_path.stem,
            "extension": windows_path.suffix,
        }

    def _upsert_drawing(
        self,
        *,
        source_path: str,
        filename: str,
        source_format: str,
        rebind_moved_source: bool,
    ) -> tuple[RegisteredDrawing, bool, bool]:
        drawing = RegisteredDrawing.objects.filter(source_path=source_path).order_by("created_at").first()
        if drawing is None and rebind_moved_source:
            candidates = list(RegisteredDrawing.objects.filter(filename=filename).order_by("created_at")[:2])
            if len(candidates) > 1:
                raise CommandError(
                    f"同名図面が複数あるため source_path を付け替えできません: {filename}"
                )
            if candidates:
                drawing = candidates[0]
                drawing.source_path = source_path
                drawing.source_format = source_format
                drawing.save(update_fields=["source_path", "source_format", "updated_at"])
                return drawing, False, True
        if drawing is None:
            return (
                RegisteredDrawing.objects.create(
                    host_drawing_id="",
                    filename=filename,
                    source_path=source_path,
                    source_format=source_format,
                ),
                True,
                False,
            )

        update_fields: list[str] = []
        if drawing.filename != filename:
            drawing.filename = filename
            update_fields.append("filename")
        if drawing.source_format != source_format:
            drawing.source_format = source_format
            update_fields.append("source_format")
        if update_fields:
            drawing.save(update_fields=update_fields + ["updated_at"])
            return drawing, False, True
        return drawing, False, False

    def _create_import_job(
        self,
        *,
        drawing: RegisteredDrawing,
        extraction_mode: str,
        payload: dict,
        executed_by: str,
    ) -> DrawingMetadataExtractionJob:
        now = timezone.now()
        return DrawingMetadataExtractionJob.objects.create(
            drawing=drawing,
            extraction_mode=extraction_mode,
            status=DrawingMetadataExtractionJob.STATUS_SUCCEEDED,
            worker_name=executed_by,
            started_at=now,
            finished_at=now,
            elapsed_ms=payload.get("elapsed_ms"),
            warnings_json=payload.get("warnings", []),
            extractor_name=payload.get("extractor_name", ""),
            extractor_version=payload.get("extractor_version", ""),
            schema_version=payload.get("schema_version") or settings.DRAWING_METADATA_SCHEMA_VERSION,
        )
