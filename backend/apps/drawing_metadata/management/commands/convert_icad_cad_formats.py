from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.extraction_runner import ExtractionRunnerError, run_icad_converter
from apps.drawing_metadata.services.reextract_planner import enqueue_missing_or_partial_reextract_jobs
from apps.drawing_metadata.services.source_formats import source_format_from_path
from apps.drawing_metadata.tasks.extraction_tasks import process_job


class Command(BaseCommand):
    help = "ICADをDXF/STEPへ変換し、必要に応じて変換後ファイルのタグ・属性抽出まで実行します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", action="append", default=[], help="対象ICAD drawing id。複数指定できます。")
        parser.add_argument(
            "--format",
            action="append",
            choices=["dxf", "step", "stp"],
            default=[],
            help="変換先形式。未指定の場合は dxf と step の両方を変換します。",
        )
        parser.add_argument(
            "--output-root",
            default=str(settings.DRAWING_METADATA_STORAGE_ROOT / "cad_conversions" / "files"),
            help="変換後CADファイルの出力ルートディレクトリ。",
        )
        parser.add_argument("--extract", action="store_true", help="変換後のDXF/STEPを登録し、その場で抽出ジョブも処理します。")
        parser.add_argument("--executed-by", default="convert_icad_cad_formats")
        parser.add_argument(
            "--export-file-type",
            type=int,
            default=None,
            help="SXNET環境固有の SxOptExport 数値を全形式共通で明示指定します。形式別指定を優先します。",
        )
        parser.add_argument(
            "--step-export-file-type",
            type=int,
            default=None,
            help="STEP/STP変換用のSXNET SxOptExport数値を明示指定します。",
        )
        parser.add_argument(
            "--dxf-export-file-type",
            type=int,
            default=None,
            help="DXF変換用のSXNET SxOptExport数値を明示指定します。",
        )

    def handle(self, *args, **options) -> None:
        drawing_ids = options["drawing_id"]
        if not drawing_ids:
            raise CommandError("--drawing-id を1つ以上指定してください。")

        formats = tuple("step" if item == "stp" else item for item in (options["format"] or ["dxf", "step"]))
        output_root = Path(options["output_root"]).expanduser().resolve()
        drawings = RegisteredDrawing.objects.filter(id__in=drawing_ids).order_by("created_at")
        drawings_by_id = {str(drawing.id): drawing for drawing in drawings}
        missing_ids = [drawing_id for drawing_id in drawing_ids if drawing_id not in drawings_by_id]
        if missing_ids:
            raise CommandError(f"指定された drawing id が存在しません: {', '.join(missing_ids)}")

        converted = 0
        registered = 0
        extracted = 0
        for drawing_id in drawing_ids:
            drawing = drawings_by_id[drawing_id]
            if (drawing.source_format or "").lower() != "icad":
                raise CommandError(f"ICAD以外は変換対象外です: {drawing.id} {drawing.source_format}")

            for output_format in formats:
                output_dir = output_root / str(drawing.id) / output_format
                output_base_name = Path(drawing.filename).stem
                try:
                    result = run_icad_converter(
                        drawing=drawing,
                        output_format=output_format,
                        output_dir=output_dir,
                        output_base_name=output_base_name,
                        export_file_type=options["export_file_type"],
                        step_export_file_type=options["step_export_file_type"],
                        dxf_export_file_type=options["dxf_export_file_type"],
                    )
                except (ExtractionRunnerError, FileNotFoundError, ValueError) as exc:
                    raise CommandError(str(exc)) from exc

                converted_path = result.converted_file_path
                if converted_path is None:
                    raise CommandError(f"変換結果に file_path が含まれていません: {result.output_path}")
                converted += 1
                self.stdout.write(f"CONVERTED {output_format}: {drawing.filename} -> {converted_path}")

                converted_drawing = _upsert_converted_drawing(
                    source_drawing=drawing,
                    converted_path=converted_path,
                    output_format=output_format,
                )
                registered += 1

                if not options["extract"]:
                    continue

                jobs = enqueue_missing_or_partial_reextract_jobs(
                    drawing=converted_drawing,
                    executed_by=options["executed_by"],
                    reason=f"converted from ICAD drawing {drawing.id}",
                )
                for job in jobs:
                    completed = process_job(job.id)
                    if completed.status == completed.STATUS_SUCCEEDED:
                        extracted += 1
                        self.stdout.write(
                            f"EXTRACTED {completed.extraction_mode}: {converted_drawing.filename} {completed.id}"
                        )
                    else:
                        raise CommandError(
                            f"変換後ファイルの抽出に失敗しました: {converted_drawing.filename} {completed.error_message}"
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"completed conversion converted={converted} registered={registered} extracted={extracted}"
            )
        )


def _upsert_converted_drawing(
    *,
    source_drawing: RegisteredDrawing,
    converted_path: Path,
    output_format: str,
) -> RegisteredDrawing:
    source_format = source_format_from_path(converted_path) or output_format
    host_drawing_id = f"{source_drawing.host_drawing_id or source_drawing.id}:{source_format}"
    drawing, created = RegisteredDrawing.objects.get_or_create(
        source_path=str(converted_path),
        defaults={
            "host_drawing_id": host_drawing_id,
            "filename": converted_path.name,
            "source_format": source_format,
        },
    )
    update_fields: list[str] = []
    if not created and drawing.filename != converted_path.name:
        drawing.filename = converted_path.name
        update_fields.append("filename")
    if not created and drawing.source_format != source_format:
        drawing.source_format = source_format
        update_fields.append("source_format")
    if not created and drawing.host_drawing_id != host_drawing_id:
        drawing.host_drawing_id = host_drawing_id
        update_fields.append("host_drawing_id")
    if update_fields:
        drawing.save(update_fields=update_fields + ["updated_at"])
    return drawing
