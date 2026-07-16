from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch
from django.utils import timezone

from apps.drawing_metadata.api.serializers import RegisteredDrawingDetailSerializer
from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata
from apps.drawing_metadata.services.knowledge_payload_preview import build_knowledge_system_payload_preview
from apps.drawing_metadata.services.rag_payload import build_rag_payload


REVIEW_SUMMARY_SCHEMA_VERSION = "drawing_metadata_handoff_review_summary.v1"


def _source_folder(source_path: str) -> str:
    if not source_path:
        return ""
    return str(Path(source_path).parent)


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _limit_list(values, *, max_items: int = 12) -> dict:
    if not isinstance(values, list):
        values = [values] if _has_value(values) else []
    compact_values = [value for value in values if _has_value(value)]
    return {
        "values": compact_values[:max_items],
        "count": len(compact_values),
        "truncated": len(compact_values) > max_items,
    }


def _tag_names(tags) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        name = tag.get("tag") if isinstance(tag, dict) else tag
        if not _has_value(name):
            continue
        name_text = str(name)
        if name_text in seen:
            continue
        seen.add(name_text)
        names.append(name_text)
    return names


def _selected_attributes(canonical: dict) -> dict:
    selected_keys = (
        "customer_name",
        "project_name",
        "equipment_name",
        "equipment_category",
        "module_name",
        "drawing_number",
        "drawing_name",
        "part_number",
        "paper_size",
        "drawing_size",
        "scale",
        "mass_value",
        "weight_value",
        "material_keywords",
        "unresolved_material_keywords",
        "surface_treatment_tokens",
        "heat_treatment_keywords",
        "part_names",
        "part_attributes",
    )
    summary = {}
    for key in selected_keys:
        value = canonical.get(key)
        if not _has_value(value):
            continue
        summary[key] = _limit_list(value) if isinstance(value, list) else value
    return summary


def _snapshot_summary(drawing: RegisteredDrawing) -> dict:
    snapshots = {}
    for snapshot in drawing.snapshots.all():
        latest_job = snapshot.latest_job
        job_summary = None
        if latest_job:
            job_summary = {
                "jobId": str(latest_job.id),
                "status": latest_job.status,
                "profile": latest_job.extraction_profile,
                "createdAt": latest_job.created_at.isoformat() if latest_job.created_at else None,
                "startedAt": latest_job.started_at.isoformat() if latest_job.started_at else None,
                "finishedAt": latest_job.finished_at.isoformat() if latest_job.finished_at else None,
                "elapsedMs": latest_job.elapsed_ms,
                "warningCount": len(latest_job.warnings_json or []),
            }
            if latest_job.error_message:
                job_summary["errorMessage"] = latest_job.error_message[:500]
        snapshots[snapshot.extraction_mode] = {
            "reviewStatus": snapshot.review_status,
            "normalizerVersion": snapshot.normalizer_version,
            "tagRuleVersion": snapshot.tag_rule_version,
            "updatedAt": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
            "rawExtractKeys": sorted((snapshot.raw_extract_json or {}).keys()),
            "canonicalAttributeCount": len(snapshot.canonical_attributes_json or {}),
            "derivedTagCount": len(snapshot.derived_tags_json or []),
            "latestJob": job_summary,
        }
    return snapshots


def _target_summary(target: dict) -> dict:
    payload_preview = target.get("payloadPreview") or {}
    return {
        "targetKey": target.get("targetKey"),
        "targetLabel": target.get("targetLabel"),
        "writePolicy": target.get("writePolicy"),
        "reviewRequired": target.get("reviewRequired"),
        "existingReception": target.get("existingReception"),
        "attributeCount": len(target.get("attributes") or []),
        "payloadAttributeCount": len(payload_preview.get("attributes") or []),
        "payloadTagCount": len(payload_preview.get("tags") or []),
    }


def _ranking_signal_summary(rag_payload: dict) -> dict:
    ranking = rag_payload.get("rankingSignals") or {}
    return {key: _limit_list(value) for key, value in ranking.items() if _has_value(value)}


def _build_review_summary_item(drawing: RegisteredDrawing) -> dict:
    composed = compose_drawing_metadata(drawing)
    canonical = composed.get("canonicalAttributes", {}) or {}
    knowledge_preview = build_knowledge_system_payload_preview(drawing=drawing, composed_metadata=composed)
    rag_payload = build_rag_payload(drawing)
    tags = _tag_names(composed.get("derivedTags", []) or [])
    review_flags = rag_payload.get("reconciliation", {}).get("reviewFlags", []) or []
    return {
        "drawingId": str(drawing.id),
        "hostDrawingId": drawing.host_drawing_id,
        "filename": drawing.filename,
        "sourcePath": drawing.source_path,
        "sourceFolder": _source_folder(drawing.source_path),
        "sourceFormat": drawing.source_format,
        "snapshotSummary": _snapshot_summary(drawing),
        "selectedAttributes": _selected_attributes(canonical),
        "derivedTags": _limit_list(tags, max_items=30),
        "knowledgeTargets": [_target_summary(target) for target in knowledge_preview.get("targets", [])],
        "ragSummary": {
            "preFilters": rag_payload.get("preFilters") or {},
            "rankingSignals": _ranking_signal_summary(rag_payload),
            "reviewFlags": review_flags[:20],
            "reviewFlagCount": len(review_flags),
            "reviewFlagsTruncated": len(review_flags) > 20,
        },
    }


class Command(BaseCommand):
    help = "内部連携データ確認用に、図面メタデータ fixture JSON を出力します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", action="append", default=[], help="出力対象の drawing UUID。複数指定できます。")
        parser.add_argument("--manifest", help="ICAD抽出manifestの entries[].sourcePath に一致する図面だけを出力します。")
        parser.add_argument("--output", help="出力先 JSON。未指定の場合は標準出力へ出します。")
        parser.add_argument(
            "--profile",
            choices=("full", "review-summary"),
            default="full",
            help=(
                "full は機械連携用の完全JSON、review-summary は人が開いて確認するための短い要約JSONです。"
            ),
        )
        parser.add_argument(
            "--include-empty-snapshots",
            action="store_true",
            help="抽出snapshotが未作成の図面もfixtureに含めます。通常の内部連携データ確認では指定しません。",
        )

    def handle(self, *args, **options) -> None:
        queryset = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            "jobs",
        ).order_by("filename", "id")

        drawing_ids = options["drawing_id"] or []
        manifest_source_paths: list[str] = []
        manifest_path_value = options.get("manifest")
        if manifest_path_value:
            manifest_path = Path(manifest_path_value)
            if not manifest_path.is_file():
                raise CommandError(f"manifest が見つかりません: {manifest_path}")
            try:
                manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CommandError(f"manifest を読めません: {manifest_path}: {exc}") from exc
            manifest_source_paths = [
                str(entry["sourcePath"])
                for entry in manifest_payload.get("entries", [])
                if entry.get("sourcePath")
            ]
            if not manifest_source_paths:
                raise CommandError(f"manifest に entries[].sourcePath がありません: {manifest_path}")
            queryset = queryset.filter(source_path__in=manifest_source_paths)
        if drawing_ids:
            queryset = queryset.filter(id__in=drawing_ids)

        drawings = list(queryset)
        if drawing_ids and len(drawings) != len(set(drawing_ids)):
            found_ids = {str(drawing.id) for drawing in drawings}
            missing_ids = sorted(set(drawing_ids) - found_ids)
            raise CommandError(f"指定された drawing-id が見つかりません: {', '.join(missing_ids)}")
        if manifest_source_paths and len(drawings) != len(set(manifest_source_paths)):
            found_paths = {drawing.source_path for drawing in drawings}
            missing_paths = sorted(set(manifest_source_paths) - found_paths)
            raise CommandError(f"manifest の sourcePath に一致する図面が見つかりません: {', '.join(missing_paths)}")

        items = []
        skipped_empty_snapshot_count = 0
        include_empty_snapshots = bool(options["include_empty_snapshots"])
        profile = options["profile"]
        for drawing in drawings:
            has_snapshots = drawing.snapshots.exists()
            if not has_snapshots and not include_empty_snapshots:
                skipped_empty_snapshot_count += 1
                continue
            if profile == "review-summary":
                items.append(_build_review_summary_item(drawing))
                continue
            detail_payload = RegisteredDrawingDetailSerializer(drawing).data
            items.append(
                {
                    "drawingId": str(drawing.id),
                    "hostDrawingId": drawing.host_drawing_id,
                    "filename": drawing.filename,
                    "detailApiPayload": detail_payload,
                    "viewerBootstrap": detail_payload.get("viewerBootstrap"),
                    "knowledgeSystemPayloadPreview": detail_payload.get("knowledgeSystemPayloadPreview"),
                    "ragPayload": build_rag_payload(drawing),
                }
            )

        payload = {
            "schemaVersion": (
                REVIEW_SUMMARY_SCHEMA_VERSION
                if profile == "review-summary"
                else "drawing_metadata_handoff_fixture.v1"
            ),
            "generatedAt": timezone.now().isoformat(),
            "itemCount": len(items),
            "sourceDrawingCount": len(drawings),
            "skippedEmptySnapshotCount": skipped_empty_snapshot_count,
            "exportPolicy": {
                "profile": profile,
                "includeEmptySnapshots": include_empty_snapshots,
                "emptySnapshotHandling": "included" if include_empty_snapshots else "skipped",
                "fileSizePolicy": (
                    "human_review_compact_no_raw_extract"
                    if profile == "review-summary"
                    else "machine_handoff_full_payload"
                ),
            },
            "items": items,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)

        output = options.get("output")
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(text + "\n", encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"exported {len(items)} drawing fixture(s): {output_path}"))
            return

        self.stdout.write(text)
