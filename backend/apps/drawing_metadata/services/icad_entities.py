from __future__ import annotations

from collections import Counter
from pathlib import PureWindowsPath
from typing import Iterable
import uuid

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata


SCHEMA_VERSION = "icad_knowledge_entities.v2"
TARGET_PRODUCT = "product"
TARGET_PART = "part"

PART_FOLDER_HINTS = {"部品", "部品図", "parts", "part"}
ASSEMBLY_NAME_HINTS = {"組立", "組図", "assembly", "assy", "unit", "ユニット"}


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _string_value(value) -> str | None:
    return str(value).strip() if _has_value(value) else None


def _stable_entity_id(drawing_id) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"icad-file-entity:{drawing_id}"))


def _snapshot_3d(drawing: RegisteredDrawing) -> DrawingMetadataSnapshot | None:
    prefetched = getattr(drawing, "knowledge_3d_snapshots", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return next((snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == "3d"), None)


def _part_rows(snapshot: DrawingMetadataSnapshot) -> list[dict]:
    parts = [part for part in (snapshot.raw_extract_json or {}).get("parts", []) if isinstance(part, dict)]
    path_counts = Counter(
        tuple(str(item).strip() for item in (part.get("tree_path") or []) if str(item).strip())
        for part in parts
    )
    inferred_child_counts: Counter[tuple[str, ...]] = Counter()
    for path, count in path_counts.items():
        if len(path) > 1:
            inferred_child_counts[path[:-1]] += count
    rows: list[dict] = []
    for part in parts:
        row = dict(part)
        path = tuple(str(item).strip() for item in (part.get("tree_path") or []) if str(item).strip())
        explicit_depth = part.get("depth")
        explicit_child_count = part.get("child_count")
        row["_path"] = path
        row["_depth"] = (
            explicit_depth
            if isinstance(explicit_depth, int) and explicit_depth >= 0
            else max(len(path) - 1, 0)
        )
        row["_child_count"] = (
            explicit_child_count
            if isinstance(explicit_child_count, int) and explicit_child_count >= 0
            else inferred_child_counts[path]
        )
        rows.append(row)
    return rows


def _manual_classification(snapshot: DrawingMetadataSnapshot) -> tuple[str, str] | None:
    overrides = snapshot.manual_overrides_json or {}
    target = _string_value(overrides.get("knowledgeEntityTarget"))
    kind = _string_value(overrides.get("knowledgeEntityKind"))
    if target not in {TARGET_PRODUCT, TARGET_PART}:
        return None
    if target == TARGET_PART:
        return target, "part"
    return target, kind if kind in {"assembly", "subassembly"} else "assembly"


def _classify_icd(drawing: RegisteredDrawing, snapshot: DrawingMetadataSnapshot, parts: list[dict]) -> dict:
    manual = _manual_classification(snapshot)
    if manual:
        return {
            "targetKey": manual[0],
            "entityKind": manual[1],
            "evidence": "manual_override",
            "confidence": "high",
            "reason": "図面管理でICD単位の登録先が手動確定されています。",
        }

    path_parts = [part.lower() for part in PureWindowsPath(drawing.source_path).parts]
    filename = drawing.filename.lower()
    if any(any(hint in path_part for hint in PART_FOLDER_HINTS) for path_part in path_parts[1:]):
        return {
            "targetKey": TARGET_PART,
            "entityKind": "part",
            "evidence": "source_folder",
            "confidence": "high",
            "reason": "保存パスに部品／部品図フォルダがあるため、ICD全体を部品として扱います。",
        }

    if any(hint in filename for hint in ASSEMBLY_NAME_HINTS):
        return {
            "targetKey": TARGET_PRODUCT,
            "entityKind": "assembly",
            "evidence": "filename",
            "confidence": "high",
            "reason": "ファイル名に組立・ユニットを示す語があるため、ICD全体を製品・装置・ユニットとして扱います。",
        }

    external_parts = [part for part in parts if part.get("_depth", 0) > 0 and bool(part.get("is_external"))]
    if external_parts:
        return {
            "targetKey": TARGET_PRODUCT,
            "entityKind": "assembly",
            "evidence": "sxnet_external_parts",
            "confidence": "high",
            "reason": f"SXNETで外部パーツを{len(external_parts)}件含むため、ICD全体をアセンブリとして扱います。",
        }

    return {
        "targetKey": TARGET_PART,
        "entityKind": "part",
        "evidence": "no_external_parts",
        "confidence": "medium",
        "reason": "外部パーツ構成を確認できないため、ICD全体を部品候補として扱います。必要なら図面管理で登録先を確定します。",
    }


def _attribute(*, key: str, label: str, value, source: str, confidence: str, evidence: str) -> dict | None:
    if not _has_value(value):
        return None
    if isinstance(value, (list, tuple, set)):
        display_value = ", ".join(str(item) for item in value if _has_value(item))
    elif isinstance(value, dict):
        display_value = ", ".join(
            f"{item_key}={item_value}" for item_key, item_value in value.items() if _has_value(item_value)
        )
    else:
        display_value = str(value)
    if not display_value:
        return None
    return {
        "key": key,
        "label": label,
        "value": display_value,
        "source": source,
        "confidence": confidence,
        "evidence": evidence,
    }


def _append_attribute(attributes: list[dict], **kwargs) -> None:
    item = _attribute(**kwargs)
    if item and not any(existing["key"] == item["key"] for existing in attributes):
        attributes.append(item)


def _material_values(parts: list[dict]) -> list[str]:
    values: list[str] = []
    for part in parts:
        for material in part.get("materials") or []:
            if not isinstance(material, dict):
                continue
            value = _string_value(material.get("mat_id")) or _string_value(material.get("name"))
            if value and value not in values:
                values.append(value)
    return values


def _snapshot_canonical(drawing: RegisteredDrawing, snapshot_3d: DrawingMetadataSnapshot) -> dict:
    canonical: dict = {}
    prefetched = getattr(drawing, "knowledge_2d_snapshots", None)
    snapshot_2d = (
        prefetched[0]
        if prefetched
        else next(
            (snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == "2d"),
            None,
        )
    )
    if snapshot_2d:
        canonical.update(snapshot_2d.canonical_attributes_json or {})
    canonical.update(snapshot_3d.canonical_attributes_json or {})
    return canonical


def _snapshot_tags(drawing: RegisteredDrawing) -> list[dict]:
    tags: list[dict] = []
    seen: set[str] = set()
    prefetched_2d = getattr(drawing, "knowledge_2d_snapshots", None)
    prefetched_3d = getattr(drawing, "knowledge_3d_snapshots", None)
    snapshots = (
        [*(prefetched_2d or []), *(prefetched_3d or [])]
        if prefetched_2d is not None and prefetched_3d is not None
        else drawing.snapshots.all()
    )
    for snapshot in snapshots:
        for tag in snapshot.derived_tags_json or []:
            value = _string_value(tag.get("tag")) if isinstance(tag, dict) else None
            if not value or value in seen:
                continue
            seen.add(value)
            tags.append(
                {
                    "value": value,
                    "source": str(tag.get("source") or f"{snapshot.extraction_mode}_snapshot"),
                    "confidence": str(tag.get("confidence") or "medium"),
                    "evidence": f"snapshotsByMode.{snapshot.extraction_mode}.derivedTags",
                }
            )
    return tags


def _build_record(
    drawing: RegisteredDrawing,
    snapshot: DrawingMetadataSnapshot,
    *,
    include_details: bool,
) -> dict:
    parts = _part_rows(snapshot)
    composed = compose_drawing_metadata(drawing) if include_details else None
    canonical = (composed or {}).get("canonicalAttributes") or _snapshot_canonical(drawing, snapshot)
    classification = _classify_icd(drawing, snapshot, parts)
    top_part = (snapshot.raw_extract_json or {}).get("top_part") or {}
    name = (
        _string_value(canonical.get("drawing_name"))
        or _string_value(top_part.get("name"))
        or PureWindowsPath(drawing.filename).stem
    )
    part_number = _string_value(canonical.get("drawing_number")) or PureWindowsPath(drawing.filename).stem
    external_count = sum(bool(part.get("is_external")) for part in parts)
    unloaded_count = sum(bool(part.get("is_unloaded")) for part in parts)
    extended_info_count = sum(bool(part.get("ex_info_fields")) for part in parts)
    unique_part_names = sorted(
        {_string_value(part.get("name")) for part in parts if _string_value(part.get("name"))}
    )
    materials = _material_values(parts)

    attributes: list[dict] = []
    _append_attribute(
        attributes,
        key="classification_reason",
        label="登録先判定根拠",
        value=classification["reason"],
        source=classification["evidence"],
        confidence=classification["confidence"],
        evidence="ICDファイル全体",
    )
    _append_attribute(attributes, key="source_path", label="保存先", value=drawing.source_path, source="file", confidence="high", evidence="registeredDrawing.sourcePath")
    _append_attribute(attributes, key="component_occurrence_count", label="内部パーツ使用数", value=len(parts), source="3d_part_tree", confidence="high", evidence="rawExtract.parts")
    _append_attribute(attributes, key="unique_component_name_count", label="内部パーツ名称数", value=len(unique_part_names), source="3d_part_tree", confidence="medium", evidence="rawExtract.parts[].name")
    _append_attribute(attributes, key="external_part_count", label="外部パーツ数", value=external_count, source="3d_part_tree", confidence="high", evidence="rawExtract.parts[].is_external")
    _append_attribute(attributes, key="unloaded_part_count", label="未ロード外部パーツ数", value=unloaded_count or None, source="3d_part_tree", confidence="high", evidence="rawExtract.parts[].is_unloaded")
    _append_attribute(attributes, key="part_extended_info_count", label="パーツ付加情報あり", value=extended_info_count or None, source="3d_part_extended_info", confidence="high", evidence="rawExtract.parts[].ex_info_fields")
    _append_attribute(attributes, key="materials", label="材質", value=materials, source="3d_part_material", confidence="high", evidence="rawExtract.parts[].materials")
    for key, label in (
        ("customer_name", "客先"),
        ("project_name", "案件"),
        ("equipment_category", "装置カテゴリ"),
        ("drawing_number", "図番"),
        ("drawing_name", "図面名"),
        ("mass_value", "質量"),
        ("weight_value", "重量"),
        ("surface_treatment", "表面処理"),
        ("paint", "塗装"),
        ("scale", "尺度"),
        ("drawing_size", "図面サイズ"),
        ("prfx", "PRFX"),
        ("unit_number", "ユニット番号"),
    ):
        _append_attribute(attributes, key=key, label=label, value=canonical.get(key), source="composed_2d_3d", confidence="medium", evidence=f"canonicalAttributes.{key}")

    tags = [
        {
            "value": str(tag.get("tag")),
            "source": str(tag.get("source") or "composed_metadata"),
            "confidence": str(tag.get("confidence") or "medium"),
            "evidence": "composedMetadata.derivedTags",
        }
        for tag in ((composed or {}).get("derivedTags") or [])
        if isinstance(tag, dict) and _has_value(tag.get("tag"))
    ] if composed else _snapshot_tags(drawing)
    history = [
        {
            "action": audit.action_type,
            "mode": audit.extraction_mode,
            "reason": audit.reason,
            "executedBy": audit.executed_by,
            "executedAt": audit.executed_at.isoformat(),
        }
        for audit in drawing.audit_logs.all()
    ] if include_details else []
    conflicts = (composed or {}).get("conflicts") or []
    return {
        "entityId": _stable_entity_id(drawing.id),
        "targetKey": classification["targetKey"],
        "entityKind": classification["entityKind"],
        "classificationEvidence": classification["evidence"],
        "classificationConfidence": classification["confidence"],
        "classificationReason": classification["reason"],
        "name": name,
        "partNumber": part_number if classification["targetKey"] == TARGET_PART else None,
        "comment": _string_value(top_part.get("comment")),
        "treePath": [name],
        "depth": 0,
        "parentEntityId": None,
        "childEntityIds": [],
        "childAssemblyCount": sum(part.get("_child_count", 0) > 0 and bool(part.get("is_external")) for part in parts),
        "childPartCount": sum(part.get("_child_count", 0) == 0 for part in parts),
        "descendantPartCount": len(parts),
        "drawingId": str(drawing.id),
        "drawingFilename": drawing.filename,
        "sourcePath": drawing.source_path,
        "attributes": attributes,
        "tags": tags,
        "conflicts": conflicts,
        "reviewStatus": snapshot.review_status,
        "reviewRequired": snapshot.review_status != DrawingMetadataSnapshot.REVIEW_CONFIRMED or bool(conflicts) or classification["confidence"] != "high",
        "evidence": [
            {
                "source": "icd_file",
                "path": drawing.source_path,
                "snapshotUpdatedAt": snapshot.updated_at.isoformat(),
            }
        ],
        "history": history,
        "updatedAt": snapshot.updated_at.isoformat(),
    }


def _records(
    drawings: Iterable[RegisteredDrawing],
    *,
    include_details: bool = False,
) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    skipped: list[dict] = []
    for drawing in drawings:
        snapshot = _snapshot_3d(drawing)
        if snapshot is None:
            skipped.append({"drawingId": str(drawing.id), "filename": drawing.filename, "reason": "3d_snapshot_missing"})
            continue
        records.append(_build_record(drawing, snapshot, include_details=include_details))
    records.sort(key=lambda record: (record["name"].lower(), record["drawingFilename"].lower()))
    return records, skipped


def build_icad_entity_catalog(
    drawings: Iterable[RegisteredDrawing],
    *,
    target_key: str | None = None,
    query: str = "",
    offset: int = 0,
    limit: int | None = None,
) -> dict:
    if target_key not in {None, TARGET_PRODUCT, TARGET_PART}:
        raise ValueError(f"unsupported target_key: {target_key}")
    records, skipped = _records(drawings, include_details=False)
    if target_key:
        records = [record for record in records if record["targetKey"] == target_key]
    normalized_query = query.strip().lower()
    if normalized_query:
        records = [
            record
            for record in records
            if normalized_query
            in " ".join(
                [
                    record["name"],
                    record.get("partNumber") or "",
                    record["drawingFilename"],
                    record["sourcePath"],
                    *(tag["value"] for tag in record["tags"]),
                    *(attribute["value"] for attribute in record["attributes"]),
                ]
            ).lower()
        ]
    total_count = len(records)
    returned = records[offset : offset + limit] if limit is not None else records[offset:]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "definitions": {
            TARGET_PRODUCT: "1つのICD全体をアセンブリ／サブアセンブリとして登録",
            TARGET_PART: "1つのICD全体を1部品として登録",
        },
        "targetKey": target_key,
        "count": total_count,
        "totalCount": total_count,
        "returnedCount": len(returned),
        "offset": offset,
        "limit": limit,
        "items": returned,
        "skippedDrawings": skipped,
    }


def find_icad_entity(drawings: Iterable[RegisteredDrawing], entity_id: str) -> dict | None:
    drawing_list = list(drawings)
    selected_drawing = next(
        (drawing for drawing in drawing_list if _stable_entity_id(drawing.id) == str(entity_id)),
        None,
    )
    if selected_drawing is None:
        return None
    snapshot = _snapshot_3d(selected_drawing)
    if snapshot is None:
        return None
    record = _build_record(selected_drawing, snapshot, include_details=True)
    referenced_names = {
        str(part.get("ref_model_name") or "").strip().lower()
        for part in (snapshot.raw_extract_json or {}).get("parts", [])
        if isinstance(part, dict) and str(part.get("ref_model_name") or "").strip()
    }
    records, _ = _records(drawing_list, include_details=False)
    related = [
        {
            "relationship": "child",
            "entityId": candidate["entityId"],
            "targetKey": candidate["targetKey"],
            "entityKind": candidate["entityKind"],
            "name": candidate["name"],
            "partNumber": candidate.get("partNumber"),
        }
        for candidate in records
        if candidate["entityId"] != record["entityId"]
        and PureWindowsPath(candidate["drawingFilename"]).stem.lower() in referenced_names
    ]
    return {
        **record,
        "relatedEntities": related,
        "relatedDrawing": {"drawingId": record["drawingId"], "filename": record["drawingFilename"]},
    }
