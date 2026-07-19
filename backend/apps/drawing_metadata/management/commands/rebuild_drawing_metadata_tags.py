from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.overrides import apply_tag_overrides, removed_tag_names
from apps.drawing_metadata.services.tag_builder import build_derived_tags


class Command(BaseCommand):
    help = "検索用タグを現行ルールで再生成します。手動タグと手動削除(removed)は維持されます。"

    def handle(self, *args, **options):
        updated = 0
        with transaction.atomic():
            for snapshot in DrawingMetadataSnapshot.objects.select_for_update().iterator():
                overrides = snapshot.manual_overrides_json or {}
                # 最終タグ = 自動再生成タグ - removed + added。
                # 旧データ互換のため、overrides 未記録の手動タグ行も removed でなければ引き継ぐ。
                tags = apply_tag_overrides(
                    build_derived_tags(snapshot.canonical_attributes_json or {}), overrides
                )
                present_tags = {str(tag.get("tag") or "") for tag in tags}
                removed = removed_tag_names(overrides)
                for tag in snapshot.derived_tags_json or []:
                    if not (isinstance(tag, dict) and tag.get("manual_flag")):
                        continue
                    display = str(tag.get("tag") or "")
                    if display and display not in present_tags and display not in removed:
                        present_tags.add(display)
                        tags.append(tag)

                snapshot.derived_tags_json = tags
                snapshot.save(update_fields=["derived_tags_json", "updated_at"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"タグを再生成しました: {updated} snapshot"))
