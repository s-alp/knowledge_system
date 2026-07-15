from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable
import uuid

from apps.drawing_metadata.models import DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.composition import compose_drawing_metadata


SCHEMA_VERSION = "icad_knowledge_entities.v1"
ENTITY_KIND_ASSEMBLY = "assembly"
ENTITY_KIND_SUBASSEMBLY = "subassembly"
ENTITY_KIND_PART = "part"

PART_NUMBER_KEYS = {
    "partno",
    "partnumber",
    "品番",
    "部品番号",
    "図番",
    "drawingno",
}

EX_INFO_TAG_FIELDS = {
    "材質": "材質",
    "材料": "材質",
    "material": "材質",
    "matl": "材質",
    "表面処理": "表面処理",
    "表処": "表面処理",
    "surface": "表面処理",
    "塗装": "塗装",
    "paint": "塗装",
    "メーカー": "メーカー",
    "maker": "メーカー",
    "prfx": "PRFX",
    "prefix": "PRFX",
    "ユニット": "ユニット",
    "unit": "ユニット",
}


@dataclass
class _Node:
    raw: dict
    raw_index: int
    node_id: str
    source_node_id: str | None
    source_parent_node_id: str | None
    path: tuple[str, ...]
    depth: int
    child_count: int
    entity_kind: str
    parent_id: str | None = None
    child_ids: list[str] | None = None


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _string_value(value) -> str | None:
    if not _has_value(value):
        return None
    return str(value).strip()


def _normalized_key(value: object) -> str:
    return "".join(str(value).lower().replace("_", " ").replace("-", " ").split())


def _stable_entity_id(drawing_id, source_key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"icad-entity:{drawing_id}:{source_key}"))


def _snapshot_3d(drawing: RegisteredDrawing) -> DrawingMetadataSnapshot | None:
    return next((snapshot for snapshot in drawing.snapshots.all() if snapshot.extraction_mode == "3d"), None)


def _path_from_part(part: dict, index: int) -> tuple[str, ...]:
    path = tuple(str(item).strip() for item in (part.get("tree_path") or []) if str(item).strip())
    if path:
        return path
    name = _string_value(part.get("name"))
    return (name or f"名称未取得-{index + 1}",)


def _entity_kind(raw_kind: str | None, *, depth: int, child_count: int) -> str:
    normalized = (raw_kind or "").strip().lower()
    if normalized in {ENTITY_KIND_ASSEMBLY, ENTITY_KIND_SUBASSEMBLY, ENTITY_KIND_PART}:
        return normalized
    if child_count <= 0:
        return ENTITY_KIND_PART
    return ENTITY_KIND_ASSEMBLY if depth == 0 else ENTITY_KIND_SUBASSEMBLY


def _prepare_nodes(drawing: RegisteredDrawing, raw_extract: dict) -> list[_Node]:
    parts = [part for part in (raw_extract.get("parts") or []) if isinstance(part, dict)]
    if not parts:
        top_part = raw_extract.get("top_part") or {}
        if isinstance(top_part, dict) and _has_value(top_part.get("name")):
            parts = [{**top_part, "tree_path": [top_part["name"]]}]

    path_occurrences: Counter[tuple[str, ...]] = Counter()
    prepared: list[tuple[dict, int, tuple[str, ...], int, str, str | None, str | None]] = []
    for index, part in enumerate(parts):
        path = _path_from_part(part, index)
        occurrence = path_occurrences[path]
        path_occurrences[path] += 1
        source_node_id = _string_value(part.get("node_id"))
        source_key = source_node_id or f"{'/'.join(path)}#{occurrence}"
        node_id = _stable_entity_id(drawing.id, source_key)
        depth_value = part.get("depth")
        depth = int(depth_value) if isinstance(depth_value, int) and depth_value >= 0 else max(len(path) - 1, 0)
        prepared.append(
            (
                part,
                index,
                path,
                depth,
                node_id,
                source_node_id,
                _string_value(part.get("parent_node_id")),
            )
        )

    source_id_to_entity_id = {source_node_id: node_id for _, _, _, _, node_id, source_node_id, _ in prepared if source_node_id}
    path_to_entity_ids: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for _, _, path, _, node_id, _, _ in prepared:
        path_to_entity_ids[path].append(node_id)

    nodes: list[_Node] = []
    for part, index, path, depth, node_id, source_node_id, source_parent_node_id in prepared:
        explicit_child_count = part.get("child_count")
        if isinstance(explicit_child_count, int) and explicit_child_count >= 0:
            child_count = explicit_child_count
        else:
            child_count = sum(
                len(entity_ids)
                for candidate_path, entity_ids in path_to_entity_ids.items()
                if len(candidate_path) == len(path) + 1 and candidate_path[:-1] == path
            )

        parent_id = source_id_to_entity_id.get(source_parent_node_id or "")
        if parent_id is None and len(path) > 1:
            parent_candidates = path_to_entity_ids.get(path[:-1], [])
            parent_id = parent_candidates[0] if parent_candidates else None

        nodes.append(
            _Node(
                raw=part,
                raw_index=index,
                node_id=node_id,
                source_node_id=source_node_id,
                source_parent_node_id=source_parent_node_id,
                path=path,
                depth=depth,
                child_count=child_count,
                entity_kind=_entity_kind(_string_value(part.get("entity_kind")), depth=depth, child_count=child_count),
                parent_id=parent_id,
                child_ids=[],
            )
        )

    node_by_id = {node.node_id: node for node in nodes}
    for node in nodes:
        if node.parent_id and node.parent_id in node_by_id:
            node_by_id[node.parent_id].child_ids.append(node.node_id)
    return nodes


def _attribute(*, key: str, label: str, value, source: str, confidence: str, evidence: str) -> dict | None:
    if not _has_value(value):
        return None
    if isinstance(value, (list, tuple, set)):
        display_value = ", ".join(str(item) for item in value if _has_value(item))
    elif isinstance(value, dict):
        display_value = ", ".join(f"{item_key}={item_value}" for item_key, item_value in value.items() if _has_value(item_value))
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
    if item and not any(existing["key"] == item["key"] and existing["value"] == item["value"] for existing in attributes):
        attributes.append(item)


def _tag(*, value: str, source: str, confidence: str, evidence: str) -> dict:
    return {"value": value, "source": source, "confidence": confidence, "evidence": evidence}


def _append_tag(tags: list[dict], **kwargs) -> None:
    item = _tag(**kwargs)
    if item["value"] and not any(existing["value"] == item["value"] for existing in tags):
        tags.append(item)


def _part_number(node: _Node) -> str:
    ex_info_fields = node.raw.get("ex_info_fields") or {}
    for key, value in ex_info_fields.items():
        if _normalized_key(key) in PART_NUMBER_KEYS and _has_value(value):
            return str(value).strip()
    return _string_value(node.raw.get("name")) or node.path[-1]


def _material_values(node: _Node) -> list[str]:
    values: list[str] = []
    for material in node.raw.get("materials") or []:
        if not isinstance(material, dict):
            continue
        value = _string_value(material.get("mat_id")) or _string_value(material.get("name"))
        if value and value not in values:
            values.append(value)
    return values


def _global_tags_for_node(node: _Node, composed_metadata: dict, *, node_count: int) -> list[dict]:
    allowed_prefixes = ("客先:", "装置:", "PRFX:", "ユニット:") if node.entity_kind != ENTITY_KIND_PART else (
        "メーカー:",
        "規格:",
    )
    if node.depth != 0 and not (node.entity_kind == ENTITY_KIND_PART and node_count == 1):
        return []
    return [
        tag
        for tag in (composed_metadata.get("derivedTags") or [])
        if isinstance(tag, dict) and str(tag.get("tag") or "").startswith(allowed_prefixes)
    ]


def _build_entity_record(
    *,
    drawing: RegisteredDrawing,
    snapshot: DrawingMetadataSnapshot,
    node: _Node,
    node_by_id: dict[str, _Node],
    composed_metadata: dict,
    node_count: int,
) -> dict:
    raw = node.raw
    name = _string_value(raw.get("name")) or node.path[-1]
    ex_info_fields = raw.get("ex_info_fields") or {}
    materials = _material_values(node)
    attributes: list[dict] = []
    evidence_base = f"snapshotsByMode.3d.rawExtract.parts[{node.raw_index}]"

    _append_attribute(
        attributes,
        key="entity_kind",
        label="構成種別",
        value={ENTITY_KIND_ASSEMBLY: "アセンブリ", ENTITY_KIND_SUBASSEMBLY: "サブアセンブリ", ENTITY_KIND_PART: "部品"}[node.entity_kind],
        source="3d_part_tree",
        confidence="high" if node.source_node_id else "medium",
        evidence=f"{evidence_base}.tree_path",
    )
    _append_attribute(attributes, key="tree_path", label="構成パス", value=" > ".join(node.path), source="3d_part_tree", confidence="high", evidence=f"{evidence_base}.tree_path")
    _append_attribute(attributes, key="comment", label="コメント", value=raw.get("comment"), source="3d_part_tree", confidence="high", evidence=f"{evidence_base}.comment")
    _append_attribute(attributes, key="materials", label="材質", value=materials, source="3d_part_material", confidence="high", evidence=f"{evidence_base}.materials")
    _append_attribute(attributes, key="ref_model_name", label="参照モデル名", value=raw.get("ref_model_name"), source="3d_part_tree", confidence="high", evidence=f"{evidence_base}.ref_model_name")
    _append_attribute(attributes, key="ref_model_path", label="参照モデルパス", value=raw.get("ref_model_path"), source="3d_part_tree", confidence="high", evidence=f"{evidence_base}.ref_model_path")
    _append_attribute(attributes, key="external_reference", label="外部参照", value="あり" if raw.get("is_external") else None, source="3d_part_tree", confidence="high", evidence=f"{evidence_base}.is_external")

    for key, value in ex_info_fields.items():
        _append_attribute(
            attributes,
            key=f"part_ex_info.{key}",
            label=f"パーツ付加情報：{key}",
            value=value,
            source="3d_part_extended_info",
            confidence="high",
            evidence=f"{evidence_base}.ex_info_fields.{key}",
        )

    canonical = composed_metadata.get("canonicalAttributes") or {}
    if node.depth == 0:
        for key, label in (
            ("customer_name", "客先"),
            ("project_name", "案件"),
            ("equipment_category", "装置カテゴリ"),
            ("drawing_number", "図番"),
            ("drawing_name", "図面名"),
            ("mass_value", "質量"),
            ("weight_value", "重量"),
        ):
            _append_attribute(
                attributes,
                key=key,
                label=label,
                value=canonical.get(key),
                source="composed_2d_3d",
                confidence="medium",
                evidence=f"composedMetadata.canonicalAttributes.{key}",
            )

    tags: list[dict] = []
    for material in materials:
        _append_tag(tags, value=f"材質:{material}", source="3d_part_material", confidence="high", evidence=f"{evidence_base}.materials")
    for field_key, field_value in ex_info_fields.items():
        normalized = _normalized_key(field_key)
        prefix = next((tag_prefix for key_hint, tag_prefix in EX_INFO_TAG_FIELDS.items() if _normalized_key(key_hint) in normalized), None)
        value = _string_value(field_value)
        if prefix and value:
            _append_tag(tags, value=f"{prefix}:{value}", source="3d_part_extended_info", confidence="high", evidence=f"{evidence_base}.ex_info_fields.{field_key}")
    for global_tag in _global_tags_for_node(node, composed_metadata, node_count=node_count):
        tag_value = _string_value(global_tag.get("tag"))
        if tag_value:
            _append_tag(
                tags,
                value=tag_value,
                source=_string_value(global_tag.get("source")) or "composed_metadata",
                confidence=_string_value(global_tag.get("confidence")) or "medium",
                evidence=f"composedMetadata.derivedTags[{tag_value}]",
            )

    child_nodes = [node_by_id[child_id] for child_id in (node.child_ids or []) if child_id in node_by_id]
    child_assembly_count = sum(child.entity_kind != ENTITY_KIND_PART for child in child_nodes)
    child_part_count = sum(child.entity_kind == ENTITY_KIND_PART for child in child_nodes)
    descendant_part_count = sum(
        candidate.entity_kind == ENTITY_KIND_PART
        and len(candidate.path) > len(node.path)
        and candidate.path[: len(node.path)] == node.path
        for candidate in node_by_id.values()
    )

    history = [
        {
            "action": audit.action_type,
            "mode": audit.extraction_mode,
            "reason": audit.reason,
            "executedBy": audit.executed_by,
            "executedAt": audit.executed_at.isoformat(),
        }
        for audit in drawing.audit_logs.all()
    ]
    conflicts = composed_metadata.get("conflicts") or [] if node.depth == 0 else []

    return {
        "entityId": node.node_id,
        "targetKey": "part" if node.entity_kind == ENTITY_KIND_PART else "product",
        "entityKind": node.entity_kind,
        "classificationEvidence": "sxnet_node_fields" if node.source_node_id else "legacy_tree_path_inference",
        "classificationConfidence": "high" if node.source_node_id else "medium",
        "name": name,
        "partNumber": _part_number(node) if node.entity_kind == ENTITY_KIND_PART else None,
        "comment": _string_value(raw.get("comment")),
        "treePath": list(node.path),
        "depth": node.depth,
        "parentEntityId": node.parent_id,
        "childEntityIds": node.child_ids or [],
        "childAssemblyCount": child_assembly_count,
        "childPartCount": child_part_count,
        "descendantPartCount": descendant_part_count,
        "drawingId": str(drawing.id),
        "drawingFilename": drawing.filename,
        "sourcePath": drawing.source_path,
        "attributes": attributes,
        "tags": tags,
        "conflicts": conflicts,
        "reviewStatus": snapshot.review_status,
        "reviewRequired": (
            snapshot.review_status != DrawingMetadataSnapshot.REVIEW_CONFIRMED
            or bool(conflicts)
            or any(tag["confidence"] == "low" for tag in tags)
        ),
        "evidence": [
            {
                "source": "3d_part_tree",
                "path": evidence_base,
                "snapshotUpdatedAt": snapshot.updated_at.isoformat(),
            }
        ],
        "history": history,
        "updatedAt": snapshot.updated_at.isoformat(),
    }


def build_icad_entity_catalog(
    drawings: Iterable[RegisteredDrawing],
    *,
    target_key: str | None = None,
    query: str = "",
    offset: int = 0,
    limit: int | None = None,
) -> dict:
    if target_key not in {None, "product", "part"}:
        raise ValueError(f"unsupported target_key: {target_key}")

    prepared_entries: list[tuple[RegisteredDrawing, DrawingMetadataSnapshot, _Node, dict[str, _Node], int]] = []
    skipped_drawings: list[dict] = []
    for drawing in drawings:
        snapshot = _snapshot_3d(drawing)
        if snapshot is None:
            skipped_drawings.append({"drawingId": str(drawing.id), "filename": drawing.filename, "reason": "3d_snapshot_missing"})
            continue
        nodes = _prepare_nodes(drawing, snapshot.raw_extract_json or {})
        if not nodes:
            skipped_drawings.append({"drawingId": str(drawing.id), "filename": drawing.filename, "reason": "3d_part_tree_empty"})
            continue
        node_by_id = {node.node_id: node for node in nodes}
        prepared_entries.extend(
            (drawing, snapshot, node, node_by_id, len(nodes))
            for node in nodes
            if target_key is None
            or (target_key == "part" and node.entity_kind == ENTITY_KIND_PART)
            or (target_key == "product" and node.entity_kind != ENTITY_KIND_PART)
        )

    prepared_entries.sort(
        key=lambda entry: (entry[0].filename.lower(), entry[2].path, entry[2].node_id)
    )

    composed_by_drawing_id: dict[str, dict] = {}

    def build_record(entry) -> dict:
        drawing, snapshot, node, node_by_id, node_count = entry
        drawing_key = str(drawing.id)
        if drawing_key not in composed_by_drawing_id:
            composed_by_drawing_id[drawing_key] = compose_drawing_metadata(drawing)
        return _build_entity_record(
            drawing=drawing,
            snapshot=snapshot,
            node=node,
            node_by_id=node_by_id,
            composed_metadata=composed_by_drawing_id[drawing_key],
            node_count=node_count,
        )

    normalized_query = query.strip().lower()
    if normalized_query:
        records = [build_record(entry) for entry in prepared_entries]
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
        returned_records = records[offset : offset + limit] if limit is not None else records[offset:]
    else:
        total_count = len(prepared_entries)
        selected_entries = prepared_entries[offset : offset + limit] if limit is not None else prepared_entries[offset:]
        returned_records = [build_record(entry) for entry in selected_entries]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "definitions": {
            "product": "ICAD 3D構成で子ノードを持つアセンブリ／サブアセンブリ",
            "part": "ICAD 3D構成で子ノードを持たない末端パーツ",
        },
        "targetKey": target_key,
        "count": total_count,
        "totalCount": total_count,
        "returnedCount": len(returned_records),
        "offset": offset,
        "limit": limit,
        "items": returned_records,
        "skippedDrawings": skipped_drawings,
    }


def find_icad_entity(drawings: Iterable[RegisteredDrawing], entity_id: str) -> dict | None:
    catalog = build_icad_entity_catalog(drawings)
    record = next((item for item in catalog["items"] if item["entityId"] == str(entity_id)), None)
    if record is None:
        return None

    record_by_id = {item["entityId"]: item for item in catalog["items"]}
    related_entities: list[dict] = []
    if record.get("parentEntityId") in record_by_id:
        parent = record_by_id[record["parentEntityId"]]
        related_entities.append(
            {
                "relationship": "parent",
                "entityId": parent["entityId"],
                "targetKey": parent["targetKey"],
                "entityKind": parent["entityKind"],
                "name": parent["name"],
                "partNumber": parent.get("partNumber"),
            }
        )
    for child_id in record.get("childEntityIds") or []:
        child = record_by_id.get(child_id)
        if child is None:
            continue
        related_entities.append(
            {
                "relationship": "child",
                "entityId": child["entityId"],
                "targetKey": child["targetKey"],
                "entityKind": child["entityKind"],
                "name": child["name"],
                "partNumber": child.get("partNumber"),
            }
        )
    return {
        **record,
        "relatedEntities": related_entities,
        "relatedDrawing": {
            "drawingId": record["drawingId"],
            "filename": record["drawingFilename"],
        },
    }
