from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import django

django.setup()

from apps.drawing_metadata.models import RegisteredDrawing
from apps.drawing_metadata.services.drawing_scope import apply_active_drawing_scope, build_scope_payload


STANDARD_GRAVITY = 9.80665
KG_TWO_DECIMAL_PATTERN = re.compile(r"^\d+(?:\.\d{2}) kg$")


def _snapshot_by_mode(drawing: RegisteredDrawing) -> dict[str, Any]:
    return {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}


def _mass_kg(canonical: dict[str, Any]) -> tuple[str | None, str | None]:
    mass_value = canonical.get("mass_value")
    if isinstance(mass_value, (int, float)):
        return f"{mass_value:.2f} kg", "canonicalAttributes.mass_value"

    weight_value = canonical.get("weight_value")
    if isinstance(weight_value, (int, float)):
        return f"{weight_value / STANDARD_GRAVITY:.2f} kg", "canonicalAttributes.weight_value / 9.80665"

    if isinstance(weight_value, str) and weight_value.strip():
        normalized = weight_value.strip()
        if KG_TWO_DECIMAL_PATTERN.match(normalized):
            return normalized, "canonicalAttributes.weight_value"
        return None, "canonicalAttributes.weight_value (not normalized to kg 2 decimals)"

    return None, None


def _add_issue(
    issues: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    reextract_condition: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "reextractCondition": reextract_condition,
        }
    )


def _row_for_drawing(drawing: RegisteredDrawing) -> dict[str, Any]:
    snapshots = _snapshot_by_mode(drawing)
    snapshot = snapshots.get("3d")
    raw_extract = snapshot.raw_extract_json or {} if snapshot else {}
    canonical = snapshot.canonical_attributes_json or {} if snapshot else {}
    parts = [part for part in raw_extract.get("parts") or [] if isinstance(part, dict)]
    parts_with_extended_info = [part for part in parts if part.get("ex_info_fields")]
    material_candidates = canonical.get("part_material_candidates") or []
    if not isinstance(material_candidates, list):
        material_candidates = []
    mass_kg, mass_evidence = _mass_kg(canonical)
    mass_probe_status = raw_extract.get("mass_probe_status")
    material_probe_status = raw_extract.get("material_probe_status")
    issues: list[dict[str, Any]] = []

    if snapshot is None:
        _add_issue(
            issues,
            severity="blocking",
            code="3d_snapshot_missing",
            message="3D snapshotがありません。",
            reextract_condition="3d_model_part_attributes条件で3D抽出を起票します。",
        )
    else:
        if not parts:
            _add_issue(
                issues,
                severity="blocking",
                code="3d_parts_missing",
                message="3D snapshotはありますが、parts配列が空です。",
                reextract_condition="getInfPartTree取得結果と部品列挙処理を確認し、3D抽出を再実行します。",
            )
        if parts and not parts_with_extended_info:
            _add_issue(
                issues,
                severity="known_condition",
                code="3d_part_extended_info_not_provided",
                message="パーツ付加情報は取得対象ですが、この図面では付加情報付き部品が見つかりません。",
                reextract_condition="パーツ付加情報を持つ客先データか確認し、必要なら3d_model_part_attributes条件で再抽出します。",
            )
        if not material_candidates:
            _add_issue(
                issues,
                severity="known_condition",
                code="3d_material_candidates_not_detected",
                message="3D側の材質候補は見つかっていません。2D図枠や注記側の候補と照合対象にします。",
                reextract_condition="material_probe_statusと部品付加情報を確認し、材質表記がある図面なら再抽出します。",
            )
        if not mass_kg and mass_probe_status == "no_entities":
            _add_issue(
                issues,
                severity="known_condition",
                code="3d_mass_no_searchable_entities",
                message="3D質量は検索対象実体なしとして記録されています。",
                reextract_condition="形状実体や質量プロパティがあるデータか確認し、必要なら3D質量取得条件で再抽出します。",
            )
        elif not mass_kg:
            _add_issue(
                issues,
                severity="blocking",
                code="3d_mass_missing_without_reason",
                message="3D質量がなく、既知条件として説明できるprobe状態もありません。",
                reextract_condition="mass_probe_statusを記録できる条件で再抽出し、取得不可理由を残します。",
            )
        elif not KG_TWO_DECIMAL_PATTERN.match(mass_kg):
            _add_issue(
                issues,
                severity="blocking",
                code="3d_mass_format_invalid",
                message="3D質量がkg小数点以下2桁に正規化されていません。",
                reextract_condition="質量正規化を再実行し、kg小数点以下2桁へそろえます。",
            )

    return {
        "drawingId": str(drawing.id),
        "filename": drawing.filename,
        "sourcePath": drawing.source_path,
        "has3dSnapshot": snapshot is not None,
        "partOccurrenceCount": len(parts),
        "partExtendedInfoCount": len(parts_with_extended_info),
        "materialCandidateCount": len(material_candidates),
        "massKg": mass_kg,
        "massEvidence": mass_evidence,
        "massProbeStatus": mass_probe_status,
        "materialProbeStatus": material_probe_status,
        "coverageStatus": "content" if parts else "missing_parts" if snapshot else "missing_snapshot",
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="共有ICADの3D構成・材質・質量・パーツ付加情報カバレッジを監査します。")
    parser.add_argument("--include-rows", action="store_true", help="全図面の詳細行も出力します。通常の納品監査では使いません。")
    parser.add_argument("--output", help="JSON出力先。省略時は標準出力します。")
    args = parser.parse_args()

    base_queryset = RegisteredDrawing.objects.prefetch_related("snapshots").order_by("filename", "id")
    total_registration_count = base_queryset.count()
    scoped_queryset, scope = apply_active_drawing_scope(base_queryset)
    rows = [_row_for_drawing(drawing) for drawing in scoped_queryset]
    blocking_issues = [
        {"drawingId": row["drawingId"], "filename": row["filename"], **issue}
        for row in rows
        for issue in row["issues"]
        if issue["severity"] == "blocking"
    ]
    known_conditions = [
        {"drawingId": row["drawingId"], "filename": row["filename"], **issue}
        for row in rows
        for issue in row["issues"]
        if issue["severity"] == "known_condition"
    ]
    content_rows = [row for row in rows if row["coverageStatus"] == "content"]
    result = {
        "schemaVersion": "icad_3d_structure_material_mass_audit.v1",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(rows),
        ),
        "drawingCount": len(rows),
        "threeDSnapshotCount": sum(row["has3dSnapshot"] for row in rows),
        "coverageStatusCounts": dict(Counter(row["coverageStatus"] for row in rows)),
        "partOccurrenceDrawingCount": sum(row["partOccurrenceCount"] > 0 for row in rows),
        "partOccurrenceCount": sum(row["partOccurrenceCount"] for row in rows),
        "partExtendedInfoDrawingCount": sum(row["partExtendedInfoCount"] > 0 for row in rows),
        "partExtendedInfoCount": sum(row["partExtendedInfoCount"] for row in rows),
        "materialCandidateDrawingCount": sum(row["materialCandidateCount"] > 0 for row in rows),
        "materialCandidateCount": sum(row["materialCandidateCount"] for row in rows),
        "massAvailableDrawingCount": sum(bool(row["massKg"]) for row in rows),
        "massMissingKnownConditionCount": sum(
            any(issue["code"] == "3d_mass_no_searchable_entities" for issue in row["issues"]) for row in rows
        ),
        "massProbeStatusCounts": dict(Counter(row["massProbeStatus"] or "not_recorded" for row in rows)),
        "materialProbeStatusCounts": dict(Counter(row["materialProbeStatus"] or "not_recorded" for row in rows)),
        "blockingIssueCount": len(blocking_issues),
        "knownConditionCount": len(known_conditions),
        "gatePassed": not blocking_issues,
        "blockingIssues": blocking_issues,
        "knownConditionSamples": known_conditions[:20],
        "contentSamples": [
            {
                "filename": row["filename"],
                "partOccurrenceCount": row["partOccurrenceCount"],
                "partExtendedInfoCount": row["partExtendedInfoCount"],
                "materialCandidateCount": row["materialCandidateCount"],
                "massKg": row["massKg"],
            }
            for row in content_rows[:10]
        ],
    }
    if args.include_rows:
        result["rows"] = rows
        result["knownConditions"] = known_conditions

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
