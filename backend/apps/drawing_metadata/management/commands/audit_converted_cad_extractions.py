from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing


class Command(BaseCommand):
    help = "ICADと、ICADから変換したDXF/STEPの抽出結果を比較して確認用JSONを出力します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--drawing-id", required=True, help="元ICADの drawing id。")
        parser.add_argument("--output", default="", help="比較結果JSONの出力先。未指定時は標準出力へ表示します。")

    def handle(self, *args, **options) -> None:
        try:
            source_drawing = RegisteredDrawing.objects.get(pk=options["drawing_id"])
        except RegisteredDrawing.DoesNotExist as exc:
            raise CommandError(f"元ICAD drawing id が存在しません: {options['drawing_id']}") from exc
        if (source_drawing.source_format or "").lower() != "icad":
            raise CommandError(f"元図面はICADである必要があります: {source_drawing.source_format}")

        payload = build_converted_cad_audit_payload(source_drawing)
        output = options["output"]
        if output:
            output_path = Path(output).expanduser()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"wrote converted CAD audit: {output_path}"))
            return

        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))


def build_converted_cad_audit_payload(source_drawing: RegisteredDrawing) -> dict:
    source_snapshots = _snapshots_by_mode(source_drawing)
    converted = {
        source_format: _find_converted_drawing(source_drawing, source_format)
        for source_format in ("step", "dxf")
    }
    converted_snapshots = {
        source_format: _snapshots_by_mode(drawing) if drawing else {}
        for source_format, drawing in converted.items()
    }

    source_3d = (source_snapshots.get("3d") or {}).get("canonical_attributes_json") or {}
    source_2d = (source_snapshots.get("2d") or {}).get("canonical_attributes_json") or {}
    step_3d = (converted_snapshots.get("step", {}).get("3d") or {}).get("canonical_attributes_json") or {}
    dxf_2d = (converted_snapshots.get("dxf", {}).get("2d") or {}).get("canonical_attributes_json") or {}

    return {
        "schemaVersion": "converted_cad_extraction_audit.v1",
        "sourceDrawing": _drawing_summary(source_drawing),
        "convertedDrawings": {
            source_format: _drawing_summary(drawing) if drawing else None
            for source_format, drawing in converted.items()
        },
        "comparisons": {
            "step3d": _compare_3d(source_3d, step_3d, bool(converted["step"])),
            "dxf2d": _compare_2d(source_2d, dxf_2d, bool(converted["dxf"])),
        },
    }


def _find_converted_drawing(source_drawing: RegisteredDrawing, source_format: str) -> RegisteredDrawing | None:
    host_prefixes = [value for value in (source_drawing.host_drawing_id, str(source_drawing.id)) if value]
    host_ids = [f"{host_prefix}:{source_format}" for host_prefix in host_prefixes]
    return (
        RegisteredDrawing.objects.filter(source_format=source_format, host_drawing_id__in=host_ids)
        .order_by("-updated_at")
        .first()
    )


def _snapshots_by_mode(drawing: RegisteredDrawing) -> dict[str, dict]:
    return {
        snapshot.extraction_mode: {
            "canonical_attributes_json": snapshot.canonical_attributes_json or {},
            "raw_extract_json": snapshot.raw_extract_json or {},
        }
        for snapshot in DrawingMetadataSnapshot.objects.filter(drawing=drawing).order_by("extraction_mode")
    }


def _drawing_summary(drawing: RegisteredDrawing) -> dict:
    return {
        "id": str(drawing.id),
        "hostDrawingId": drawing.host_drawing_id,
        "filename": drawing.filename,
        "sourcePath": drawing.source_path,
        "sourceFormat": drawing.source_format,
    }


def _compare_3d(source: dict, converted: dict, converted_exists: bool) -> dict:
    source_materials = source.get("material_keywords") or []
    converted_materials = converted.get("material_keywords") or []
    source_parts = source.get("part_names") or []
    converted_parts = converted.get("part_names") or []
    return {
        "convertedDrawingExists": converted_exists,
        "sourceSnapshotExists": bool(source),
        "convertedSnapshotExists": bool(converted),
        "materialKeywordOverlap": _overlap(source_materials, converted_materials),
        "partNameOverlap": _overlap(source_parts, converted_parts),
        "convertedStepProductNames": converted.get("step_product_names") or [],
        "convertedStepAssemblyRelationshipCount": converted.get("step_assembly_relationship_count") or 0,
        "sourceMassAvailable": source.get("mass_value") is not None or source.get("weight_value") is not None,
        "convertedMassAvailable": converted.get("mass_value") is not None or converted.get("weight_value") is not None,
    }


def _compare_2d(source: dict, converted: dict, converted_exists: bool) -> dict:
    source_title_fields = source.get("title_block_fields") or {}
    converted_title_fields = converted.get("title_block_fields") or {}
    source_keys = sorted(source_title_fields)
    converted_keys = sorted(converted_title_fields)
    return {
        "convertedDrawingExists": converted_exists,
        "sourceSnapshotExists": bool(source),
        "convertedSnapshotExists": bool(converted),
        "titleBlockFieldKeyOverlap": _overlap(source_keys, converted_keys),
        "sourceMaterialKeywords": source.get("material_keywords") or [],
        "convertedMaterialKeywords": converted.get("material_keywords") or [],
        "convertedDxfLayers": converted.get("dxf_layers") or [],
        "convertedDxfBlockAttributeCount": converted.get("dxf_block_attribute_count") or 0,
        "convertedDxfBlockAttributeTokens": converted.get("dxf_block_attribute_tokens") or [],
    }


def _overlap(left: Iterable[str], right: Iterable[str]) -> dict:
    left_values = list(dict.fromkeys(str(value) for value in left if value))
    right_values = list(dict.fromkeys(str(value) for value in right if value))
    overlap_values = [value for value in left_values if value in right_values]
    return {
        "leftCount": len(left_values),
        "rightCount": len(right_values),
        "overlapCount": len(overlap_values),
        "overlapValues": overlap_values,
        "leftOnly": [value for value in left_values if value not in right_values],
        "rightOnly": [value for value in right_values if value not in left_values],
    }
