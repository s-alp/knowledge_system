from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.tag_builder import build_derived_tags


class Command(BaseCommand):
    help = "検索用タグを現行ルールで再生成し、手動タグだけを引き継ぎます。"

    def handle(self, *args, **options):
        updated = 0
        with transaction.atomic():
            for snapshot in DrawingMetadataSnapshot.objects.select_for_update().iterator():
                manual_tags = [
                    tag
                    for tag in (snapshot.derived_tags_json or [])
                    if isinstance(tag, dict) and bool(tag.get("manual_flag"))
                ]
                generated = build_derived_tags(snapshot.canonical_attributes_json or {})
                manual_values = {str(tag.get("tag") or "") for tag in manual_tags}
                snapshot.derived_tags_json = manual_tags + [
                    tag for tag in generated if str(tag.get("tag") or "") not in manual_values
                ]
                snapshot.save(update_fields=["derived_tags_json", "updated_at"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"タグを再生成しました: {updated} snapshot"))
