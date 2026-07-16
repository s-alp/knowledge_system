from __future__ import annotations

from collections import Counter
from pathlib import PureWindowsPath
import re
from typing import Iterable
import uuid

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata


SCHEMA_VERSION = "icad_knowledge_entities.v2"
TARGET_PRODUCT = "product"
TARGET_PART = "part"

PART_FOLDER_HINTS = {"部品", "部品図", "parts", "part"}
ASSEMBLY_NAME_HINTS = {"組立", "組図", "assembly", "assy", "unit", "ユニット"}
STANDARD_GRAVITY = 9.80665


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


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if _has_value(value):
        return [value]
    return []


def _classify_icd(
    drawing: RegisteredDrawing,
    snapshot: DrawingMetadataSnapshot,
    parts: list[dict],
    canonical: dict | None = None,
) -> dict:
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

    if parts:
        external_count = sum(part.get("_depth", 0) > 0 and _has_external_reference(part) for part in parts)
    else:
        canonical = canonical or {}
        external_count = max(
            len(_as_list(canonical.get("ref_model_names"))),
            len(_as_list(canonical.get("ref_model_paths"))),
            1 if canonical.get("external_part_exists") else 0,
        )
    if external_count:
        return {
            "targetKey": TARGET_PRODUCT,
            "entityKind": "assembly",
            "evidence": "sxnet_external_parts",
            "confidence": "high",
            "reason": f"SXNETで外部参照パーツを{external_count}件確認できるため、ICD全体をアセンブリとして扱います。",
        }

    return {
        "targetKey": TARGET_PART,
        "entityKind": "part",
        "evidence": "no_external_parts",
        "confidence": "medium",
        "reason": "外部パーツ構成を確認できないため、ICD全体を部品候補として扱います。必要なら図面管理で登録先を確定します。",
    }


def _has_external_reference(part: dict) -> bool:
    return bool(part.get("is_external")) or _has_value(part.get("ref_model_name")) or _has_value(part.get("ref_model_path"))


def _attribute(
    *,
    key: str,
    label: str,
    value,
    source: str,
    confidence: str,
    evidence: str,
    reason: str = "",
) -> dict | None:
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
        "reason": reason or _attribute_reason(label, source),
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


def _canonical_list_values(canonical: dict, *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        for item in _as_list(canonical.get(key)):
            value = _string_value(item)
            if value and value not in values:
                values.append(value)
    return values


def _has_lightweight_part_summary(canonical: dict) -> bool:
    has_part_summary = any(
        _has_value(canonical.get(key))
        for key in (
            "top_part_name",
            "part_names",
            "part_tree_paths",
            "ref_model_names",
            "ref_model_paths",
            "external_part_exists",
            "material_keywords",
            "material_names",
            "material_ids",
        )
    )
    has_material_summary = any(
        _has_value(canonical.get(key)) for key in ("material_keywords", "material_names", "material_ids")
    )
    return has_part_summary and has_material_summary


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
            source = str(tag.get("source") or f"{snapshot.extraction_mode}_snapshot")
            tags.append(
                {
                    "value": value,
                    "source": source,
                    "confidence": str(tag.get("confidence") or "medium"),
                    "evidence": f"snapshotsByMode.{snapshot.extraction_mode}.derivedTags",
                    "reason": str(tag.get("reason") or _tag_reason(source)),
                    "manualFlag": bool(tag.get("manual_flag")),
                    "ruleVersion": str(tag.get("tag_rule_version") or ""),
                }
            )
    return tags


def _attribute_reason(label: str, source: str) -> str:
    if source == "3d_mass_properties":
        return f"{label}として3D質量情報からkg単位に正規化できたため採用しています。"
    if source == "2d_title_block":
        return f"{label}として2D図枠から抽出でき、図面管理の検索・確認に使えるため採用しています。"
    if source == "3d_part_material":
        return f"{label}として3D部品材質情報から抽出でき、部品検索に使えるため採用しています。"
    if source == "3d_part_tree":
        return f"{label}として3D部品構成から算出でき、製品・装置・ユニット／部品の判定に使えるため採用しています。"
    if source == "3d_part_extended_info":
        return f"{label}としてパーツ付加情報から確認でき、客先別の追加属性確認に使えるため採用しています。"
    if source == "file":
        return f"{label}として登録ファイル情報から取得でき、ICD単位の追跡に使えるため採用しています。"
    if source in {"manual_override", "manual_entity_target"}:
        return f"{label}として利用者が手動確定した値のため採用しています。"
    return f"{label}として抽出・正規化できたため採用しています。"


def _tag_reason(source: str) -> str:
    reasons = {
        "customer_name": "客先名として正規化でき、案件横断検索に使えるため採用しています。",
        "project_name": "案件名として正規化でき、案件単位の検索に使えるため採用しています。",
        "equipment_category": "装置カテゴリとして正規化でき、分類検索に使えるため採用しています。",
        "maker_keywords": "メーカー名として抽出でき、購入品や構成部品の検索に使えるため採用しています。",
        "material_keywords": "正式材質として分類でき、加工・調達検索に使えるため採用しています。",
        "unresolved_material_keywords": "材質らしい値ですが正式材質と確定できないため、要確認タグとして分離しています。",
        "spec_tokens": "規格識別子として抽出でき、規格・社内標準の検索に使えるため採用しています。",
        "title_block_fields.material": "2D図枠の材質欄から抽出でき、図面起点の材質検索に使えるため採用しています。",
        "title_block_fields.surface_treatment": "2D図枠の表面処理欄から抽出でき、加工・処理条件の検索に使えるため採用しています。",
        "title_block_fields.coating_instruction": "2D図枠の塗装指示欄から抽出でき、塗装条件の検索に使えるため採用しています。",
        "title_block_fields.prfx": "2D図枠のPRFX欄から抽出でき、客先・案件別の識別に使えるため採用しています。",
        "title_block_fields.unit_number": "2D図枠のユニット番号欄から抽出でき、ユニット単位の検索に使えるため採用しています。",
        "manual_override": "利用者が手動で追加したタグのため採用しています。",
        "composed_metadata": "2D/3D統合結果から検索・分類に使えるタグとして整理できたため採用しています。",
    }
    return reasons.get(source, "タグ化対象として正規化でき、検索・分類に使えるため採用しています。")


def _number(value) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group(0)) if match else None


def _mass_in_kg(canonical: dict) -> tuple[str | None, str | None]:
    mass_value = _number(canonical.get("mass_value"))
    if mass_value is not None:
        return f"{mass_value:.2f} kg", "canonicalAttributes.mass_value"
    raw_weight = canonical.get("weight_value")
    weight_value = _number(raw_weight)
    if weight_value is not None:
        if isinstance(raw_weight, str) and re.search(r"(?:kg|ｋｇ)", raw_weight, re.IGNORECASE):
            return f"{weight_value:.2f} kg", "canonicalAttributes.weight_value (kg)"
        return f"{weight_value / STANDARD_GRAVITY:.2f} kg", "canonicalAttributes.weight_value / 9.80665"
    return None, None


def _business_fields(
    *,
    target_key: str,
    entity_kind: str,
    name: str,
    part_number: str,
    comment: str | None,
    canonical: dict,
    overrides: dict,
) -> tuple[dict, dict]:
    extracted = {
        "name": name,
        "partNumber": part_number if target_key == TARGET_PART else "",
        "category": _string_value(canonical.get("equipment_category")) or "",
        "entityKind": entity_kind,
        "phase": _string_value(canonical.get("phase")) or "",
        "status": _string_value(canonical.get("business_status")) or "",
        "owner": _string_value(canonical.get("person_in_charge"))
        or _string_value(canonical.get("designer"))
        or "",
        "supplier": _string_value(canonical.get("supplier")) or "",
        "unitPrice": _string_value(canonical.get("unit_price")) or "",
        "unit": _string_value(canonical.get("unit")) or "",
        "remarks": comment or "",
    }
    manual = overrides.get("businessFields") if isinstance(overrides.get("businessFields"), dict) else {}
    fields = {key: str(manual.get(key, value) or "") for key, value in extracted.items()}
    sources = {
        key: {
            "source": "manual_override" if key in manual else "icad_extraction",
            "evidence": f"manualOverrides.businessFields.{key}" if key in manual else f"canonicalAttributes.{key}",
        }
        for key in fields
    }
    sources["name"]["evidence"] = (
        "manualOverrides.businessFields.name" if "name" in manual else "titleBlock/topPart/filename"
    )
    if target_key == TARGET_PART:
        sources["partNumber"]["evidence"] = (
            "manualOverrides.businessFields.partNumber"
            if "partNumber" in manual
            else "canonicalAttributes.drawing_number/filename"
        )
    return fields, sources


def _build_record(
    drawing: RegisteredDrawing,
    snapshot: DrawingMetadataSnapshot,
    *,
    include_details: bool,
) -> dict:
    composed = compose_drawing_metadata(drawing) if include_details else None
    canonical = (composed or {}).get("canonicalAttributes") or _snapshot_canonical(drawing, snapshot)
    parts = _part_rows(snapshot) if include_details or not _has_lightweight_part_summary(canonical) else []
    classification = _classify_icd(drawing, snapshot, parts, canonical=canonical)
    top_part = ((snapshot.raw_extract_json or {}).get("top_part") or {}) if include_details or parts else {}
    canonical_part_names = _canonical_list_values(canonical, "part_names")
    name = (
        _string_value(canonical.get("drawing_name"))
        or _string_value(canonical.get("top_part_name"))
        or (canonical_part_names[0] if canonical_part_names else None)
        or _string_value(top_part.get("name"))
        or PureWindowsPath(drawing.filename).stem
    )
    part_number = _string_value(canonical.get("drawing_number")) or PureWindowsPath(drawing.filename).stem
    if parts:
        external_count = sum(_has_external_reference(part) for part in parts)
        unloaded_count = sum(bool(part.get("is_unloaded")) for part in parts)
        extended_info_count = sum(bool(part.get("ex_info_fields")) for part in parts)
        unique_part_names = sorted(
            {_string_value(part.get("name")) for part in parts if _string_value(part.get("name"))}
        )
        materials = _material_values(parts)
        component_count = len(parts)
        child_assembly_count = sum(part.get("_child_count", 0) > 0 and _has_external_reference(part) for part in parts)
        child_part_count = sum(part.get("_child_count", 0) == 0 for part in parts)
    else:
        unique_part_names = _canonical_list_values(canonical, "part_names", "part_keywords")
        materials = _canonical_list_values(canonical, "material_keywords", "material_names", "material_ids")
        external_count = max(
            len(_as_list(canonical.get("ref_model_names"))),
            len(_as_list(canonical.get("ref_model_paths"))),
            1 if canonical.get("external_part_exists") else 0,
        )
        unloaded_count = 1 if canonical.get("unresolved_part_exists") else 0
        extended_info_count = 1 if _has_value(canonical.get("part_ex_info_fields")) else 0
        component_count = len(_as_list(canonical.get("part_tree_paths"))) or len(unique_part_names)
        child_assembly_count = external_count
        child_part_count = component_count
    overrides = snapshot.manual_overrides_json or {}
    business_fields, business_field_sources = _business_fields(
        target_key=classification["targetKey"],
        entity_kind=classification["entityKind"],
        name=name,
        part_number=part_number,
        comment=_string_value(top_part.get("comment")) or _string_value(canonical.get("top_part_comment")),
        canonical=canonical,
        overrides=overrides,
    )
    name = business_fields["name"] or name
    part_number = business_fields["partNumber"] or part_number

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
    _append_attribute(attributes, key="component_occurrence_count", label="内部パーツ使用数", value=component_count, source="3d_part_tree", confidence="high", evidence="rawExtract.parts / canonicalAttributes.part_tree_paths")
    _append_attribute(attributes, key="unique_component_name_count", label="内部パーツ名称数", value=len(unique_part_names), source="3d_part_tree", confidence="medium", evidence="rawExtract.parts[].name / canonicalAttributes.part_names")
    _append_attribute(attributes, key="external_part_count", label="外部パーツ数", value=external_count, source="3d_part_tree", confidence="high", evidence="rawExtract.parts[].is_external / canonicalAttributes.ref_model_names")
    _append_attribute(attributes, key="unloaded_part_count", label="未ロード外部パーツ数", value=unloaded_count or None, source="3d_part_tree", confidence="high", evidence="rawExtract.parts[].is_unloaded / canonicalAttributes.unresolved_part_exists")
    _append_attribute(attributes, key="part_extended_info_count", label="パーツ付加情報あり", value=extended_info_count or None, source="3d_part_extended_info", confidence="high", evidence="rawExtract.parts[].ex_info_fields / canonicalAttributes.part_ex_info_fields")
    _append_attribute(attributes, key="materials", label="材質", value=materials, source="3d_part_material", confidence="high", evidence="rawExtract.parts[].materials / canonicalAttributes.material_keywords")
    _append_attribute(attributes, key="material_2d", label="材質 (2D図枠)", value=canonical.get("material"), source="2d_title_block", confidence="medium", evidence="canonicalAttributes.title_block_fields.material")
    mass_kg, mass_evidence = _mass_in_kg(canonical)
    for key, label in (
        ("customer_name", "客先"),
        ("project_name", "案件"),
        ("equipment_category", "装置カテゴリ"),
        ("drawing_number", "図番"),
        ("drawing_name", "図面名"),
        ("model_name", "ICADモデル名"),
        ("model_path", "ICADモデル格納パス"),
        ("model_comment", "ICADモデルコメント"),
        ("surface_treatment", "表面処理"),
        ("paint", "塗装"),
        ("scale", "尺度"),
        ("drawing_size", "図面サイズ"),
        ("prfx", "PRFX"),
        ("unit_number", "ユニット番号"),
    ):
        _append_attribute(attributes, key=key, label=label, value=canonical.get(key), source="composed_2d_3d", confidence="medium", evidence=f"canonicalAttributes.{key}")
    _append_attribute(
        attributes,
        key="mass_value",
        label="質量",
        value=mass_kg,
        source="3d_mass_properties",
        confidence="high",
        evidence=mass_evidence or "canonicalAttributes.mass_value",
    )
    _append_attribute(
        attributes,
        key="weight_value",
        label="重量",
        value=mass_kg,
        source="3d_mass_properties",
        confidence="high",
        evidence=f"{mass_evidence or 'canonicalAttributes.mass_value'} (kg表示へ統一)",
    )

    tags = [
        {
            "value": str(tag.get("tag")),
            "source": str(tag.get("source") or "composed_metadata"),
            "confidence": str(tag.get("confidence") or "medium"),
            "evidence": "composedMetadata.derivedTags",
            "reason": str(tag.get("reason") or _tag_reason(str(tag.get("source") or "composed_metadata"))),
            "manualFlag": bool(tag.get("manual_flag")),
            "ruleVersion": str(tag.get("tag_rule_version") or ""),
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
    diagnostic_conflicts = (composed or {}).get("diagnosticConflicts") or []
    reconciled_attributes = (composed or {}).get("reconciledAttributes") or []
    return {
        "entityId": _stable_entity_id(drawing.id),
        "targetKey": classification["targetKey"],
        "entityKind": classification["entityKind"],
        "classificationEvidence": classification["evidence"],
        "classificationConfidence": classification["confidence"],
        "classificationReason": classification["reason"],
        "name": name,
        "partNumber": part_number if classification["targetKey"] == TARGET_PART else None,
        "comment": business_fields["remarks"] or None,
        "treePath": [name],
        "depth": 0,
        "parentEntityId": None,
        "childEntityIds": [],
        "childAssemblyCount": child_assembly_count,
        "childPartCount": child_part_count,
        "descendantPartCount": component_count,
        "drawingId": str(drawing.id),
        "drawingFilename": drawing.filename,
        "sourcePath": drawing.source_path,
        "attributes": attributes,
        "tags": tags,
        "businessFields": business_fields,
        "businessFieldSources": business_field_sources,
        "conflicts": conflicts,
        "diagnosticConflicts": diagnostic_conflicts,
        "reconciledAttributes": reconciled_attributes,
        "reviewStatus": snapshot.review_status,
        "reviewRequired": snapshot.review_status != DrawingMetadataSnapshot.REVIEW_CONFIRMED or bool(conflicts) or classification["confidence"] != "high",
        "extractionReview": {
            "status": snapshot.review_status,
            "required": snapshot.review_status != DrawingMetadataSnapshot.REVIEW_CONFIRMED
            or bool(conflicts)
            or classification["confidence"] != "high",
            "label": {
                DrawingMetadataSnapshot.REVIEW_CONFIRMED: "確認済み",
                DrawingMetadataSnapshot.REVIEW_NEEDS_CORRECTION: "要手直し",
            }.get(snapshot.review_status, "未確認"),
            "description": "ICAD自動抽出結果の確認状態です。製品・部品の業務ステータスとは別に管理します。",
        },
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
    linked_ids = {
        str(item)
        for item in ((snapshot.manual_overrides_json or {}).get("relatedDrawingIds") or [])
    }
    related_drawings = [
        {
            "drawingId": record["drawingId"],
            "filename": record["drawingFilename"],
            "sourcePath": record["sourcePath"],
            "relationship": "source",
        }
    ]
    linked_drawings = RegisteredDrawing.objects.filter(id__in=linked_ids).order_by("filename", "id")
    related_drawings.extend(
        {
            "drawingId": str(candidate.id),
            "filename": candidate.filename,
            "sourcePath": candidate.source_path,
            "relationship": "linked",
        }
        for candidate in linked_drawings
        if str(candidate.id) in linked_ids and str(candidate.id) != record["drawingId"]
    )
    provenance = [
        {"kind": "attribute", "name": item["label"], **item}
        for item in record["attributes"]
    ] + [
        {"kind": "tag", "name": item["value"], **item}
        for item in record["tags"]
    ]
    return {
        **record,
        "relatedEntities": related,
        "relatedDrawing": {"drawingId": record["drawingId"], "filename": record["drawingFilename"]},
        "relatedDrawings": related_drawings,
        "provenance": provenance,
    }
