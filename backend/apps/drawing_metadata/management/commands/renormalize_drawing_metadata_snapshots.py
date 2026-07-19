from __future__ import annotations

from copy import deepcopy

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.overrides import (
    apply_attribute_overrides,
    apply_tag_overrides,
    removed_tag_names,
)
from apps.drawing_metadata.services.tag_builder import build_derived_tags


class Command(BaseCommand):
    help = "保存済み抽出結果を現行の正規化・タグ規則で再計算します。手動補正(属性上書き・タグ追加/削除)は維持されます。"

    def handle(self, *args, **options):
        updated = 0
        with transaction.atomic():
            snapshots = DrawingMetadataSnapshot.objects.select_related("drawing").select_for_update()
            for snapshot in snapshots.iterator():
                raw_extract = deepcopy(snapshot.raw_extract_json or {})
                source_file = raw_extract.pop("_source_file", None) or {
                    "full_path": snapshot.drawing.source_path,
                    "directory_path": "",
                    "file_name": snapshot.drawing.filename,
                    "file_name_without_extension": snapshot.drawing.filename.rsplit(".", 1)[0],
                    "extension": ".icd",
                }
                payload = {
                    "source_format": snapshot.drawing.source_format,
                    "source_kind": snapshot.extraction_mode,
                    "source_file": source_file,
                    "raw_extract": raw_extract,
                }
                overrides = snapshot.manual_overrides_json or {}
                canonical = apply_attribute_overrides(normalize_raw_extract(payload), overrides)

                # 最終タグ = 自動再生成タグ - removed + added。
                # 旧データ互換のため、overrides に記録されていない手動タグ行(manual_flag)も
                # removed に入っていない限り引き継ぐ。
                tags = apply_tag_overrides(build_derived_tags(canonical), overrides)
                present_tags = {str(tag.get("tag") or "") for tag in tags}
                removed = removed_tag_names(overrides)
                for tag in snapshot.derived_tags_json or []:
                    if not (isinstance(tag, dict) and tag.get("manual_flag")):
                        continue
                    display = str(tag.get("tag") or "")
                    if display and display not in present_tags and display not in removed:
                        present_tags.add(display)
                        tags.append(tag)

                snapshot.canonical_attributes_json = canonical
                snapshot.derived_tags_json = tags
                snapshot.save(update_fields=["canonical_attributes_json", "derived_tags_json", "updated_at"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"正規化結果を再計算しました: {updated} snapshot"))
