from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.drawing_metadata.models import TagDictionaryEntry
from apps.drawing_metadata.services.dictionaries import KIND_TO_SEED


class Command(BaseCommand):
    help = "コード内 seed 辞書を TagDictionaryEntry へ投入します(以後はGUI/adminでの編集が正本)。"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for kind, mapping in KIND_TO_SEED.items():
            for priority, (canonical, candidates) in enumerate(mapping.items()):
                aliases = [candidate for candidate in candidates if candidate != canonical]
                _, was_created = TagDictionaryEntry.objects.update_or_create(
                    kind=kind,
                    canonical_value=canonical,
                    defaults={"aliases_json": aliases, "priority": priority, "enabled": True},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f"タグ辞書を投入しました: created={created} updated={updated}"))
