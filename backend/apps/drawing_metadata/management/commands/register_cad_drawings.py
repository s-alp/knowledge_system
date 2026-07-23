from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.path_constraints import normalize_icad_display_filename
from apps.drawing_metadata.services.source_formats import is_supported_cad_source, source_format_from_path


class Command(BaseCommand):
    help = "cad_data 配下の .icd/.step/.stp/.dxf を RegisteredDrawing へ一括登録します。"

    def add_arguments(self, parser) -> None:
        default_cad_root = Path(settings.BASE_DIR).parent / "cad_data"
        parser.add_argument(
            "--cad-root",
            default=str(default_cad_root),
            help="登録対象の CAD ルートディレクトリを指定します。",
        )

    def handle(self, *args, **options) -> None:
        cad_root = Path(options["cad_root"]).expanduser()
        if not cad_root.exists():
            raise CommandError(f"CAD ルートが存在しません: {cad_root}")
        if not cad_root.is_dir():
            raise CommandError(f"CAD ルートがディレクトリではありません: {cad_root}")

        created = 0
        updated = 0
        skipped = 0

        cad_paths = sorted(path.resolve() for path in cad_root.rglob("*") if path.is_file() and is_supported_cad_source(path))
        if not cad_paths:
            self.stdout.write("登録対象の .icd/.step/.stp/.dxf は見つかりませんでした。")
            return

        for input_path in cad_paths:
            source_format = source_format_from_path(input_path)
            if source_format is None:
                continue
            display_filename = (
                normalize_icad_display_filename(input_path.name) if source_format == "icad" else input_path.name
            )

            existing = RegisteredDrawing.objects.filter(source_path=str(input_path)).order_by("created_at").first()
            if existing is None:
                RegisteredDrawing.objects.create(
                    host_drawing_id="",
                    filename=display_filename,
                    source_path=str(input_path),
                    source_format=source_format,
                )
                created += 1
                self.stdout.write(f"CREATED: {display_filename}")
                continue

            update_fields: list[str] = []
            if existing.filename != display_filename:
                existing.filename = display_filename
                update_fields.append("filename")
            if existing.source_format != source_format:
                existing.source_format = source_format
                update_fields.append("source_format")

            if update_fields:
                existing.save(update_fields=update_fields + ["updated_at"])
                updated += 1
                self.stdout.write(f"UPDATED: {existing.id} {display_filename}")
                continue

            skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"completed scan created={created} updated={updated} skipped={skipped} total={len(cad_paths)}"
            )
        )
