from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch
from django.utils import timezone

from apps.drawing_metadata.api.serializers import RegisteredDrawingDetailSerializer
from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.rag_payload import build_rag_payload


class Command(BaseCommand):
    help = "内部連携データ確認用に、図面メタデータ fixture JSON を出力します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", action="append", default=[], help="出力対象の drawing UUID。複数指定できます。")
        parser.add_argument("--manifest", help="ICAD抽出manifestの entries[].sourcePath に一致する図面だけを出力します。")
        parser.add_argument("--output", help="出力先 JSON。未指定の場合は標準出力へ出します。")
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
        for drawing in drawings:
            detail_payload = RegisteredDrawingDetailSerializer(drawing).data
            if not detail_payload.get("snapshotsByMode") and not include_empty_snapshots:
                skipped_empty_snapshot_count += 1
                continue
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
            "schemaVersion": "drawing_metadata_handoff_fixture.v1",
            "generatedAt": timezone.now().isoformat(),
            "itemCount": len(items),
            "sourceDrawingCount": len(drawings),
            "skippedEmptySnapshotCount": skipped_empty_snapshot_count,
            "exportPolicy": {
                "includeEmptySnapshots": include_empty_snapshots,
                "emptySnapshotHandling": "included" if include_empty_snapshots else "skipped",
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
