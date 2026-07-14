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
    help = "創屋連携確認用に、図面メタデータ fixture JSON を出力します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", action="append", default=[], help="出力対象の drawing UUID。複数指定できます。")
        parser.add_argument("--output", help="出力先 JSON。未指定の場合は標準出力へ出します。")

    def handle(self, *args, **options) -> None:
        queryset = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            "jobs",
        ).order_by("filename", "id")

        drawing_ids = options["drawing_id"] or []
        if drawing_ids:
            queryset = queryset.filter(id__in=drawing_ids)

        drawings = list(queryset)
        if drawing_ids and len(drawings) != len(set(drawing_ids)):
            found_ids = {str(drawing.id) for drawing in drawings}
            missing_ids = sorted(set(drawing_ids) - found_ids)
            raise CommandError(f"指定された drawing-id が見つかりません: {', '.join(missing_ids)}")

        items = []
        for drawing in drawings:
            detail_payload = RegisteredDrawingDetailSerializer(drawing).data
            items.append(
                {
                    "drawingId": str(drawing.id),
                    "hostDrawingId": drawing.host_drawing_id,
                    "filename": drawing.filename,
                    "detailApiPayload": detail_payload,
                    "viewerBootstrap": detail_payload.get("viewerBootstrap"),
                    "ragPayload": build_rag_payload(drawing),
                }
            )

        payload = {
            "schemaVersion": "drawing_metadata_handoff_fixture.v1",
            "generatedAt": timezone.now().isoformat(),
            "itemCount": len(items),
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
