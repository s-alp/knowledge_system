from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.path_constraints import validate_icad_filename_length, validate_icad_path_length


class Command(BaseCommand):
    help = "cad_data 配下の .icd を RegisteredDrawing へ一括登録します。"

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

        icd_paths = sorted(path.resolve() for path in cad_root.rglob("*") if path.is_file() and path.suffix.lower() == ".icd")
        if not icd_paths:
            self.stdout.write("登録対象の .icd は見つかりませんでした。")
            return

        for input_path in icd_paths:
            try:
                validate_icad_filename_length(input_path.name)
                validate_icad_path_length(input_path)
            except ValueError as exc:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"SKIPPED path limit: {input_path} ({exc})"))
                continue

            existing = RegisteredDrawing.objects.filter(source_path=str(input_path)).order_by("created_at").first()
            if existing is None:
                RegisteredDrawing.objects.create(
                    host_drawing_id="",
                    filename=input_path.name,
                    source_path=str(input_path),
                    source_format="icad",
                )
                created += 1
                self.stdout.write(f"CREATED: {input_path.name}")
                continue

            update_fields: list[str] = []
            if existing.filename != input_path.name:
                existing.filename = input_path.name
                update_fields.append("filename")
            if existing.source_format != "icad":
                existing.source_format = "icad"
                update_fields.append("source_format")

            if update_fields:
                existing.save(update_fields=update_fields + ["updated_at"])
                updated += 1
                self.stdout.write(f"UPDATED: {existing.id} {input_path.name}")
                continue

            skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"completed scan created={created} updated={updated} skipped={skipped} total={len(icd_paths)}"
            )
        )
