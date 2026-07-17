from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.composition import refresh_composed_metadata
from apps.drawing_metadata.services.persistence import re_normalize_snapshot


class Command(BaseCommand):
    help = (
        "保存済み raw_extract から正規化・タグ生成を再実行する。"
        "辞書やタグ生成ルールの改訂を、ICAD 再抽出なしで既存図面へ反映するためのコマンド。"
    )

    def add_arguments(self, parser):
        parser.add_argument("--drawing-id", help="対象図面IDを絞る(省略時は全件)")
        parser.add_argument("--mode", choices=["2d", "3d"], help="抽出モードを絞る")
        parser.add_argument(
            "--stale-only",
            action="store_true",
            help="normalizer_version / tag_rule_version が現行と異なるスナップショットだけを対象にする",
        )

    def handle(self, *args, **options):
        queryset = DrawingMetadataSnapshot.objects.select_related("drawing", "latest_job")
        if options.get("drawing_id"):
            queryset = queryset.filter(drawing_id=options["drawing_id"])
        if options.get("mode"):
            queryset = queryset.filter(extraction_mode=options["mode"])
        if options.get("stale_only"):
            queryset = queryset.exclude(
                Q(normalizer_version=settings.DRAWING_METADATA_NORMALIZER_VERSION)
                & Q(tag_rule_version=settings.DRAWING_METADATA_TAG_RULE_VERSION)
            )

        processed = 0
        touched_drawings = {}
        for snapshot in queryset:
            re_normalize_snapshot(snapshot=snapshot, executed_by="command:re_normalize_snapshots")
            touched_drawings[snapshot.drawing_id] = snapshot.drawing
            processed += 1

        for drawing in touched_drawings.values():
            refresh_composed_metadata(drawing)

        self.stdout.write(
            self.style.SUCCESS(
                f"re-normalized snapshots={processed} drawings={len(touched_drawings)} "
                f"normalizer={settings.DRAWING_METADATA_NORMALIZER_VERSION} "
                f"tag_rule={settings.DRAWING_METADATA_TAG_RULE_VERSION}"
            )
        )
