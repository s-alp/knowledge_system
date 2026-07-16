from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
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


INSPECTABLE_KEYS = (
    "texts",
    "dimensions",
    "geometry_primitives",
    "weld_notes",
    "balloons",
    "tolerances",
)


def _inspectable_items(raw_extract: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in INSPECTABLE_KEYS:
        for item in raw_extract.get(key, []) or []:
            if isinstance(item, dict):
                items.append(item | {"_coverageSource": key})
    return items


def _inside_print_area_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in items:
        value = item.get("inside_print_area")
        if value is True:
            counts["inside"] += 1
        elif value is False:
            counts["outside"] += 1
        else:
            counts["unknown"] += 1
    return {
        "inside": counts["inside"],
        "outside": counts["outside"],
        "unknown": counts["unknown"],
    }


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


def _snapshot_by_mode(drawing: RegisteredDrawing) -> dict[str, Any]:
    return {snapshot.extraction_mode: snapshot for snapshot in drawing.snapshots.all()}


def _row_for_drawing(drawing: RegisteredDrawing) -> dict[str, Any]:
    snapshots = _snapshot_by_mode(drawing)
    snapshot = snapshots.get("2d")
    raw_extract = snapshot.raw_extract_json or {} if snapshot else {}
    items = _inspectable_items(raw_extract)
    view_sheets = raw_extract.get("view_sheets") or []
    layers = raw_extract.get("layers") or []
    print_frames = raw_extract.get("print_frames") or []
    items_without_view = [item for item in items if not item.get("view_name")]
    items_with_layer = [item for item in items if item.get("layer_no") is not None]
    items_without_layer = [item for item in items if item.get("layer_no") is None]
    inside_counts = _inside_print_area_counts(items)
    classified_print_area_count = inside_counts["inside"] + inside_counts["outside"]
    issues: list[dict[str, Any]] = []

    if snapshot is None:
        _add_issue(
            issues,
            severity="blocking",
            code="2d_snapshot_missing",
            message="2D snapshotがありません。",
            reextract_condition="2d_all_views_layers_print_frame条件で2D抽出を起票します。",
        )
    elif items:
        if not view_sheets:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_view_sheets_missing",
                message="2D要素はありますが、VS/ビュー一覧がありません。",
                reextract_condition="scanAllViewsを有効にして2D抽出を再実行します。",
            )
        if items_without_view:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_items_without_view",
                message="2D要素の一部にview_nameが付いていません。",
                reextract_condition="全ビュー走査時のview_name付与処理を確認し、再抽出します。",
            )
        if not layers:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_layers_missing",
                message="2D要素はありますが、レイヤー一覧がありません。",
                reextract_condition="scanAllLayersを有効にして2D抽出を再実行します。",
            )
        if not items_with_layer:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_no_items_with_layer",
                message="2D要素にレイヤー番号が1件も付いていません。",
                reextract_condition="要素ごとのlayer_no付与処理を確認し、再抽出します。",
            )
        elif items_without_layer:
            _add_issue(
                issues,
                severity="known_condition",
                code="2d_items_without_layer_remain",
                message="一部の2D要素はSXNETの要素数とレイヤー数の不一致などでlayer_noを付与できません。",
                reextract_condition="geometry_layer_count_mismatchの発生ビューと要素型を確認し、紐づけ可能な型からlayer_no取得を追加します。",
            )
        if not print_frames:
            _add_issue(
                issues,
                severity="known_condition",
                code="2d_print_frame_not_defined",
                message="2D要素はありますが、SXNETの印刷枠リストが空です。",
                reextract_condition="probe-2d-printで印刷枠定義を再確認します。返らない場合は印刷枠未定義として保持します。",
            )
        elif classified_print_area_count == 0:
            _add_issue(
                issues,
                severity="blocking",
                code="2d_print_area_classification_missing",
                message="印刷枠はありますが、印刷枠内外の判定結果がありません。",
                reextract_condition="capturePrintFramesを有効にし、座標取得と枠内外判定を確認して再抽出します。",
            )
        elif inside_counts["unknown"]:
            _add_issue(
                issues,
                severity="known_condition",
                code="2d_print_area_unknown_items_remain",
                message="一部の2D要素は座標欠落などで印刷枠内外を判定できません。",
                reextract_condition="unknown要素のgeometry_typeと座標有無を確認し、必要な型だけ座標取得を追加します。",
            )

    return {
        "drawingId": str(drawing.id),
        "filename": drawing.filename,
        "sourcePath": drawing.source_path,
        "has2dSnapshot": snapshot is not None,
        "contentStatus": "content" if items else "extracted_no_2d_entities" if snapshot else "missing_snapshot",
        "viewSheetCount": len(view_sheets),
        "layerDefinitionCount": len(layers),
        "printFrameCount": len(print_frames),
        "inspectableItemCount": len(items),
        "itemsWithoutViewCount": len(items_without_view),
        "itemsWithLayerCount": len(items_with_layer),
        "itemsWithoutLayerCount": len(items_without_layer),
        "insidePrintArea": inside_counts,
        "multiplePrintFrames": len(print_frames) > 1,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="共有ICADの2Dビュー・レイヤー・印刷枠カバレッジを監査します。")
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
    content_rows = [row for row in rows if row["contentStatus"] == "content"]
    result = {
        "schemaVersion": "icad_2d_view_layer_print_frame_audit.v1",
        "scope": build_scope_payload(
            scope=scope,
            total_registration_count=total_registration_count,
            scoped_registration_count=len(rows),
        ),
        "drawingCount": len(rows),
        "twoDSnapshotCount": sum(row["has2dSnapshot"] for row in rows),
        "contentStatusCounts": dict(Counter(row["contentStatus"] for row in rows)),
        "contentDrawingCount": len(content_rows),
        "contentWithViewSheetsCount": sum(row["viewSheetCount"] > 0 for row in content_rows),
        "contentWithLayerDefinitionsCount": sum(row["layerDefinitionCount"] > 0 for row in content_rows),
        "contentWithPrintFramesCount": sum(row["printFrameCount"] > 0 for row in content_rows),
        "multiplePrintFrameDrawingCount": sum(row["multiplePrintFrames"] for row in content_rows),
        "itemsWithoutViewCount": sum(row["itemsWithoutViewCount"] for row in content_rows),
        "itemsWithoutLayerCount": sum(row["itemsWithoutLayerCount"] for row in content_rows),
        "insidePrintAreaCount": sum(row["insidePrintArea"]["inside"] for row in content_rows),
        "outsidePrintAreaCount": sum(row["insidePrintArea"]["outside"] for row in content_rows),
        "unknownPrintAreaCount": sum(row["insidePrintArea"]["unknown"] for row in content_rows),
        "blockingIssueCount": len(blocking_issues),
        "knownConditionCount": len(known_conditions),
        "gatePassed": not blocking_issues,
        "blockingIssues": blocking_issues,
        "knownConditionSamples": known_conditions[:20],
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
