from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django

django.setup()

from apps.drawing_metadata.models import RegisteredDrawing


STANDARD_GRAVITY = 9.80665
KG_TWO_DECIMAL_PATTERN = re.compile(r"^-?\d+\.\d{2} kg$")


def _path_key(value: str) -> str:
    return value.replace("/", "\\").rstrip("\\").casefold()


def _content_count(raw: dict) -> int:
    return sum(
        len(raw.get(key) or [])
        for key in ("texts", "dimensions", "geometry_primitives", "weld_notes", "balloons", "tolerances")
    )


def _coverage_values(raw: dict, field: str) -> set[str]:
    values: set[str] = set()
    for key in ("texts", "dimensions", "geometry_primitives", "weld_notes", "balloons", "tolerances"):
        for item in raw.get(key) or []:
            if isinstance(item, dict) and item.get(field) is not None:
                values.add(str(item[field]))
    return values


def _inspectable_items(raw: dict) -> list[dict]:
    items: list[dict] = []
    for key in ("texts", "dimensions", "geometry_primitives", "weld_notes", "balloons", "tolerances"):
        for item in raw.get(key) or []:
            if isinstance(item, dict):
                items.append(item)
    return items


def _inside_print_area_counts(raw: dict) -> dict[str, int]:
    counts = Counter()
    for item in _inspectable_items(raw):
        value = item.get("inside_print_area")
        if value is True:
            counts["inside"] += 1
        elif value is False:
            counts["outside"] += 1
        else:
            counts["unknown"] += 1
    return {"inside": counts["inside"], "outside": counts["outside"], "unknown": counts["unknown"]}


def _latest_job(snapshot) -> dict:
    job = getattr(snapshot, "latest_job", None) if snapshot else None
    if job is None:
        return {
            "status": "not_recorded",
            "profile": "",
            "createdAt": None,
            "startedAt": None,
            "finishedAt": None,
            "errorMessage": "",
            "warnings": [],
        }
    return {
        "status": job.status,
        "profile": job.extraction_profile,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
        "errorMessage": job.error_message,
        "warnings": job.warnings_json or [],
    }


def _mass_kg(canonical: dict) -> tuple[str | None, str]:
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
    return None, ""


def _source_access_status(source_path: str) -> str:
    try:
        return "exists" if Path(source_path).is_file() else "not_accessible"
    except OSError:
        return "not_accessible"


def _add_issue(issues: list[dict], *, severity: str, code: str, message: str, reextract_condition: str) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "reextractCondition": reextract_condition,
        }
    )


def main() -> int:
    manifest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output/souya_handoff/icad_extract_import_manifest_all_shared_2026-07-15.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_source_counts = Counter(str(entry["sourcePath"]) for entry in manifest.get("entries", []))
    registered_drawings = list(RegisteredDrawing.objects.prefetch_related("snapshots__latest_job"))
    registered_source_counts = Counter(_path_key(drawing.source_path) for drawing in registered_drawings)
    drawings = {_path_key(drawing.source_path): drawing for drawing in registered_drawings}
    rows = []
    for entry in manifest.get("entries", []):
        source_path = str(entry["sourcePath"])
        drawing = drawings.get(_path_key(source_path))
        snapshots = {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()} if drawing else {}
        two_d = snapshots.get("2d")
        three_d = snapshots.get("3d")
        raw_2d = (two_d.raw_extract_json or {}) if two_d else {}
        raw_3d = (three_d.raw_extract_json or {}) if three_d else {}
        canonical_2d = (two_d.canonical_attributes_json or {}) if two_d else {}
        canonical_3d = (three_d.canonical_attributes_json or {}) if three_d else {}
        content_count = _content_count(raw_2d)
        view_count = len(_coverage_values(raw_2d, "view_name"))
        layer_count = len(_coverage_values(raw_2d, "layer_no"))
        print_frame_count = len(raw_2d.get("print_frames") or [])
        inside_counts = _inside_print_area_counts(raw_2d)
        parts = [part for part in raw_3d.get("parts") or [] if isinstance(part, dict)]
        part_extended_info_count = sum(bool(part.get("ex_info_fields")) for part in parts)
        material_candidate_count = len(canonical_3d.get("part_material_candidates") or [])
        mass_kg, mass_evidence = _mass_kg(canonical_3d)
        issues: list[dict] = []
        job_2d = _latest_job(two_d)
        job_3d = _latest_job(three_d)
        source_access_status = _source_access_status(source_path)

        if drawing is None:
            _add_issue(
                issues,
                severity="blocking",
                code="registration_missing",
                message="manifestのICADがRegisteredDrawingに登録されていません。",
                reextract_condition="登録処理を実行し、1 ICD = 1登録単位でsourcePathを一致させます。",
            )
        if drawing is not None and source_access_status != "exists":
            _add_issue(
                issues,
                severity="known_condition",
                code="source_not_accessible_current_environment",
                message="現在の実行環境から原本ICADパスにアクセスできませんが、登録済みsnapshotは存在します。",
                reextract_condition="再抽出が必要な場合はネットワークドライブ/共有パスを接続し直してから実行します。",
            )
        if manifest_source_counts[source_path] > 1:
            _add_issue(
                issues,
                severity="blocking",
                code="manifest_source_path_duplicated",
                message="manifest内で同じICAD sourcePathが複数回指定されています。",
                reextract_condition="manifest生成条件を見直し、1 ICD = 1 entryに正規化します。",
            )
        if registered_source_counts[_path_key(source_path)] > 1:
            _add_issue(
                issues,
                severity="blocking",
                code="registered_source_path_duplicated",
                message="RegisteredDrawingに同じICAD sourcePathの重複登録があります。",
                reextract_condition="登録重複を統合し、1 ICD = 1 RegisteredDrawingに正規化します。",
            )
        if two_d is None:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_snapshot_missing",
                message="2D snapshotがありません。",
                reextract_condition="2d_all_views_layers_print_frame条件で2D抽出を起票します。",
            )
        elif job_2d["status"] == "failed":
            _add_issue(
                issues,
                severity="blocking",
                code="2d_latest_job_failed",
                message=job_2d["errorMessage"] or "2D最新ジョブが失敗しています。",
                reextract_condition="失敗理由を確認し、ICAD起動状態・対象パス・抽出条件を修正して再抽出します。",
            )
        if three_d is None:
            _add_issue(
                issues,
                severity="blocking",
                code="3d_snapshot_missing",
                message="3D snapshotがありません。",
                reextract_condition="3d_model_part_attributes条件で3D抽出を起票します。",
            )
        elif job_3d["status"] == "failed":
            _add_issue(
                issues,
                severity="blocking",
                code="3d_latest_job_failed",
                message=job_3d["errorMessage"] or "3D最新ジョブが失敗しています。",
                reextract_condition="失敗理由を確認し、ICAD起動状態・対象パス・抽出条件を修正して再抽出します。",
            )
        if content_count > 0 and view_count == 0:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_content_without_view",
                message="2D要素はありますが、ビュー情報が付いていません。",
                reextract_condition="全ビュー走査条件を有効にして2D抽出器のview_name付与を確認します。",
            )
        if content_count > 0 and layer_count == 0:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_content_without_layer",
                message="2D要素はありますが、レイヤー情報が付いていません。",
                reextract_condition="全レイヤー走査条件を有効にして2D抽出器のlayer_no付与を確認します。",
            )
        if content_count > 0 and print_frame_count == 0:
            _add_issue(
                issues,
                severity="known_condition",
                code="2d_print_frame_not_defined_by_sxnet",
                message="2D要素はありますが、SXNETの印刷枠リストが空です。inside_print_areaはunknownとして保持します。",
                reextract_condition="必要に応じてprobe-2d-printで再確認します。印刷枠が返らない場合は図面側に印刷枠定義なしとして扱います。",
            )
        if three_d and not parts:
            _add_issue(
                issues,
                severity="blocking",
                code="3d_parts_missing",
                message="3D snapshotはありますが、parts配列が空です。",
                reextract_condition="3D構成取得条件を確認し、パーツツリー抽出を再実行します。",
            )
        mass_probe_status = raw_3d.get("mass_probe_status")
        if three_d and not mass_kg and mass_probe_status == "no_entities":
            _add_issue(
                issues,
                severity="known_condition",
                code="3d_mass_no_searchable_entities",
                message="SxWF.getEntListが質量計算対象の3D要素を返していないため、質量を算出できません。",
                reextract_condition="3D形状エンティティが存在するかICAD側で確認します。存在しない場合は質量取得不可理由として保持します。",
            )
        elif three_d and not mass_kg:
            _add_issue(
                issues,
                severity="warning",
                code="3d_mass_missing",
                message="3D質量・重量をkg表示へ正規化できていません。",
                reextract_condition="3D質量プローブを再実行し、取得不可なら取得不可理由を記録します。",
            )

        if content_count > 0:
            two_d_status = "content"
            two_d_reason = "2D snapshotに文字・寸法・形状・注記などの抽出対象要素があります。"
        elif two_d is not None and job_2d["status"] in {"succeeded", "not_recorded"}:
            two_d_status = "extracted_no_2d_entities"
            two_d_reason = "2D抽出は完了していますが、SXNETから対象要素が返っていません。3Dのみ、または2D要素なしのICDとして扱います。"
        else:
            two_d_status = "unresolved"
            two_d_reason = "2D抽出結果が利用可能か確認できません。"

        part_extended_info_status = "present" if part_extended_info_count else "not_provided"
        material_status = "present" if material_candidate_count else "not_provided"
        mass_status = "present" if mass_kg else "not_provided"

        rows.append(
            {
                "sourcePath": source_path,
                "filename": Path(source_path).name,
                "sourceAccessStatus": source_access_status,
                "registered": drawing is not None,
                "has2dSnapshot": two_d is not None,
                "has3dSnapshot": three_d is not None,
                "twoDContentStatus": two_d_status,
                "twoDContentReason": two_d_reason,
                "twoDContentCount": content_count,
                "viewSheetCount": len(raw_2d.get("view_sheets") or []),
                "viewCount": view_count,
                "layerDefinitionCount": len(raw_2d.get("layers") or []),
                "layerCount": layer_count,
                "printFrameCount": print_frame_count,
                "printFrameStatus": (
                    "defined"
                    if raw_2d.get("print_frames")
                    else "not_defined"
                    if content_count
                    else "not_applicable_no_2d_entities"
                ),
                "insidePrintArea": inside_counts,
                "partOccurrenceCount": len(parts),
                "partExtendedInfoStatus": part_extended_info_status,
                "partExtendedInfoCount": part_extended_info_count,
                "materialCandidateStatus": material_status,
                "materialCandidateCount": material_candidate_count,
                "massStatus": mass_status,
                "massKg": mass_kg,
                "massEvidence": mass_evidence,
                "massProbeStatus": mass_probe_status,
                "materialProbeStatus": raw_3d.get("material_probe_status"),
                "latestJobs": {"2d": job_2d, "3d": job_3d},
                "canonicalSourceEvidence": {
                    "2dTitleBlockFields": sorted((canonical_2d.get("title_block_fields") or {}).keys()),
                    "3dPartExtendedInfo": "rawExtract.parts[].ex_info_fields",
                    "3dMaterialCandidates": "canonicalAttributes.part_material_candidates",
                    "3dMass": mass_evidence,
                },
                "issues": issues,
            }
        )

    blocking_issues = [
        {"sourcePath": row["sourcePath"], **issue}
        for row in rows
        for issue in row["issues"]
        if issue["severity"] == "blocking"
    ]
    warning_issues = [
        {"sourcePath": row["sourcePath"], **issue}
        for row in rows
        for issue in row["issues"]
        if issue["severity"] == "warning"
    ]
    known_condition_issues = [
        {"sourcePath": row["sourcePath"], **issue}
        for row in rows
        for issue in row["issues"]
        if issue["severity"] == "known_condition"
    ]
    result = {
        "schemaVersion": "icad_shared_sample_current_audit.v2",
        "manifest": str(manifest_path),
        "validationPolicy": {
            "registrationUnit": "1 ICD sourcePath = 1 RegisteredDrawing",
            "blocking": [
                "manifest未登録",
                "2D/3D snapshot欠落",
                "最新2D/3Dジョブ失敗",
                "2D要素ありでビュー/レイヤー未付与",
                "3D snapshotありでparts欠落",
            ],
            "warning": [
                "3D質量をkgへ正規化できず、SXNETの失敗理由も既知条件化できない",
            ],
            "knownCondition": [
                "2D要素ありでSXNET印刷枠リストが空",
                "SXNETが質量計算対象の3D要素を返さない",
                "現環境から原本ICADパスにアクセスできないがsnapshotは存在する",
            ],
        },
        "sampleCount": len(rows),
        "registeredCount": sum(row["registered"] for row in rows),
        "manifestDuplicateSourcePathCount": sum(1 for _path, count in manifest_source_counts.items() if count > 1),
        "registeredDuplicateSourcePathCount": sum(1 for _path, count in registered_source_counts.items() if count > 1),
        "twoDSnapshotCount": sum(row["has2dSnapshot"] for row in rows),
        "threeDSnapshotCount": sum(row["has3dSnapshot"] for row in rows),
        "twoDContentStatusCounts": dict(Counter(row["twoDContentStatus"] for row in rows)),
        "contentWithViewCoverageCount": sum(row["twoDContentStatus"] == "content" and row["viewCount"] > 0 for row in rows),
        "contentWithLayerCoverageCount": sum(row["twoDContentStatus"] == "content" and row["layerCount"] > 0 for row in rows),
        "contentWithPrintFrameCount": sum(row["twoDContentStatus"] == "content" and row["printFrameCount"] > 0 for row in rows),
        "multiplePrintFrameDrawingCount": sum(row["printFrameCount"] > 1 for row in rows),
        "contentWithoutDefinedPrintFrameCount": sum(row["printFrameStatus"] == "not_defined" for row in rows),
        "partExtendedInfoDrawingCount": sum(row["partExtendedInfoCount"] > 0 for row in rows),
        "materialCandidateDrawingCount": sum(row["materialCandidateCount"] > 0 for row in rows),
        "massAvailableDrawingCount": sum(row["massStatus"] == "present" for row in rows),
        "sourceNotAccessibleCount": sum(row["sourceAccessStatus"] != "exists" for row in rows),
        "blockingIssueCount": len(blocking_issues),
        "warningIssueCount": len(warning_issues),
        "knownConditionCount": len(known_condition_issues),
        "gatePassed": not blocking_issues,
        "blockingIssues": blocking_issues,
        "warningIssues": warning_issues,
        "knownConditionIssues": known_condition_issues,
        "unresolved": [
            row
            for row in rows
            if any(issue["severity"] == "blocking" for issue in row["issues"])
        ],
        "no2dEntityRows": [row for row in rows if row["twoDContentStatus"] == "extracted_no_2d_entities"],
        "knownDataConditions": [
            {
                "sourcePath": row["sourcePath"],
                "condition": "print_frame_not_defined",
                "handling": "座標・ビュー・レイヤーは保持し、inside_print_areaは判定不明のままにする。",
            }
            for row in rows
            if row["printFrameStatus"] == "not_defined"
        ]
        + [
            {
                "sourcePath": row["sourcePath"],
                "condition": "mass_no_searchable_entities",
                "handling": "SxWF.getEntListが質量計算対象を返さないため、質量取得不可理由として保持する。",
            }
            for row in rows
            if row["massProbeStatus"] == "no_entities"
        ],
        "rows": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
        print(
            f"wrote {output_path} samples={result['sampleCount']} "
            f"registered={result['registeredCount']} 2d={result['twoDSnapshotCount']} "
            f"3d={result['threeDSnapshotCount']} blocking={result['blockingIssueCount']} "
            f"warnings={result['warningIssueCount']} gatePassed={result['gatePassed']}"
        )
    else:
        print(text)
    return 1 if blocking_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
