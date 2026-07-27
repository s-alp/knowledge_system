from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.drawing_metadata.services.extraction_runner import ExtractionRunnerError, run_icad_export_type_probe


class Command(BaseCommand):
    help = "SXNETのSxOptExport定数を確認し、ICADからDXF/STEPへ変換する際の数値指定要否を出力します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output",
            default="",
            help="probe結果JSONの出力先。未指定時はDRAWING_METADATA_STORAGE_ROOT/cad_conversions配下へ出力します。",
        )

    def handle(self, *args, **options) -> None:
        output = options["output"]
        output_path = Path(output).expanduser() if output else None
        try:
            result = run_icad_export_type_probe(output_path=output_path)
        except ExtractionRunnerError as exc:
            raise CommandError(str(exc)) from exc

        expected_formats = result.payload.get("expected_formats") or {}
        summary = {
            source_format: {
                "matchedFields": payload.get("matched_fields") or {},
                "requiresOverride": bool(payload.get("requires_export_file_type_override")),
            }
            for source_format, payload in expected_formats.items()
            if isinstance(payload, dict)
        }
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
        self.stdout.write(self.style.SUCCESS(f"wrote SXNET export type probe: {result.output_path}"))
