from __future__ import annotations

from copy import deepcopy

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.drawing_metadata.models import DrawingMetadataSnapshot
from apps.drawing_metadata.services.normalization import normalize_raw_extract
from apps.drawing_metadata.services.tag_builder import build_derived_tags


class Command(BaseCommand):
    help = "保存済み抽出結果を現行の正規化・タグ規則で再計算します。"

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
                canonical = normalize_raw_extract(payload)
                overrides = snapshot.manual_overrides_json or {}
                for key, item in (overrides.get("canonicalAttributes") or {}).items():
                    canonical[key] = item.get("value") if isinstance(item, dict) else item

                manual_tags = [
                    tag
                    for tag in (snapshot.derived_tags_json or [])
                    if isinstance(tag, dict) and bool(tag.get("manual_flag"))
                ]
                manual_values = {str(tag.get("tag") or "") for tag in manual_tags}
                generated_tags = [
                    tag
                    for tag in build_derived_tags(canonical)
                    if str(tag.get("tag") or "") not in manual_values
                ]
                snapshot.canonical_attributes_json = canonical
                snapshot.derived_tags_json = manual_tags + generated_tags
                snapshot.save(update_fields=["canonical_attributes_json", "derived_tags_json", "updated_at"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"正規化結果を再計算しました: {updated} snapshot"))
