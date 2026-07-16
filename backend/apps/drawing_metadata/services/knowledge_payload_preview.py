from __future__ import annotations

from apps.drawing_metadata.models import RegisteredDrawing


SCHEMA_VERSION = "knowledge_system_payload_preview.v1"

ATTRIBUTE_VALUE_KEYS = ("attribute", "attribute_option", "attribute_value")

DRAWING_ATTRIBUTE_SPECS = (
    ("drawing_number", "図番"),
    ("drawing_name", "図面名"),
    ("paper_size", "図面サイズ"),
    ("title_block_fields.material", "材質"),
    ("material_keywords", "材質候補"),
    ("unresolved_material_keywords", "要確認材質"),
    ("title_block_fields.surface_treatment", "表面処理"),
    ("surface_treatment_tokens", "表面処理候補"),
    ("title_block_fields.coating_instruction", "塗装指示"),
    ("title_block_fields.scale", "尺度"),
    ("title_block_fields.prfx", "PRFX"),
    ("title_block_fields.unit_number", "ユニット番号"),
    ("title_block_fields.designer", "設計者"),
    ("title_block_fields.checker", "検図者"),
    ("title_block_fields.approver", "承認者"),
    ("title_block_fields.date", "日付"),
    ("title_block_fields.created_date", "作成日"),
    ("title_block_fields.checked_date", "検図日"),
    ("title_block_fields.approved_date", "承認日"),
    ("title_block_fields.revision_date", "改訂日"),
    ("revision_note_count", "訂正内容候補数"),
    ("mass_value", "質量"),
    ("weight_value", "重量"),
)

PRODUCT_ATTRIBUTE_SPECS = (
    ("customer_name", "客先"),
    ("project_name", "案件"),
    ("equipment_category", "装置カテゴリ"),
    ("equipment_name", "装置名"),
    ("title_block_fields.prfx", "PRFX"),
    ("title_block_fields.unit_number", "ユニット番号"),
    ("source_directory_path", "保存フォルダ"),
)

PART_ATTRIBUTE_SPECS = (
    ("top_part_name", "代表部品名"),
    ("part_names", "部品名候補"),
    ("material_keywords", "材質候補"),
    ("unresolved_material_keywords", "要確認材質"),
    ("maker_keywords", "メーカー候補"),
    ("part_ex_info_tokens", "パーツ付加情報トークン"),
    ("referenced_2d_part_names", "2D実像部品名"),
    ("referenced_2d_part3d_names", "2D参照3D部品名"),
    ("referenced_2d_ref_model_names", "2D参照モデル名"),
)

PROJECT_ATTRIBUTE_SPECS = (
    ("customer_name", "客先"),
    ("project_name", "案件"),
    ("equipment_category", "装置カテゴリ"),
    ("source_directory_path", "保存フォルダ"),
)


def _has_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _value_at_path(data: dict, path: str):
    value = data
    for key in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _attribute_value(value) -> str:
    if isinstance(value, dict):
        items = [f"{key}={item}" for key, item in value.items() if _has_value(item)]
        return ", ".join(items)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if _has_value(item))
    return str(value)


def _attribute_confidence(canonical_attributes: dict, source_path: str) -> str:
    if source_path.startswith("title_block_fields."):
        field = source_path.split(".", 1)[1]
        for candidate in canonical_attributes.get("title_block_candidates") or []:
            if candidate.get("field") == field and _has_value(candidate.get("value")):
                confidence = candidate.get("llm_confidence") or candidate.get("confidence")
                if confidence in {"high", "medium", "low"}:
                    return confidence
        return "medium"
    confidence = canonical_attributes.get("confidence_summary")
    return confidence if confidence in {"high", "medium", "low"} else "medium"


def _attribute_evidence(source_path: str, value: str) -> str:
    return f"canonicalAttributes.{source_path}={value}"


def _attribute_reason(attribute_name: str, source_path: str) -> str:
    if source_path.startswith("title_block_fields."):
        return f"2D図枠候補から{attribute_name}として正規化できるため、属性候補として提示します。"
    if source_path in {"mass_value", "weight_value"}:
        return f"抽出結果をkg・小数点以下2桁へ正規化できるため、{attribute_name}属性候補として提示します。"
    if "material" in source_path:
        return f"材質分類に使える値として正規化できるため、{attribute_name}属性候補として提示します。"
    return f"canonicalAttributes.{source_path} から業務項目 {attribute_name} として提示できるため、属性候補に含めます。"


def _attribute_items(canonical_attributes: dict, specs: tuple[tuple[str, str], ...]) -> list[dict]:
    items: list[dict] = []
    for source_path, attribute_name in specs:
        value = _value_at_path(canonical_attributes, source_path)
        if not _has_value(value):
            continue
        attribute_value = _attribute_value(value)
        evidence = _attribute_evidence(source_path, attribute_value)
        items.append(
            {
                "sourcePath": f"canonicalAttributes.{source_path}",
                "attributeName": attribute_name,
                "attribute": None,
                "attributeOption": None,
                "attributeValue": attribute_value,
                "evidence": evidence,
                "confidence": _attribute_confidence(canonical_attributes, source_path),
                "reason": _attribute_reason(attribute_name, source_path),
                "payloadShape": {
                    "attribute": None,
                    "attribute_option": None,
                    "attribute_value": attribute_value,
                },
                "bindingStatus": "needs_attribute_master_binding",
            }
        )
    return items


def _tag_items(tags: list[dict]) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for tag in tags or []:
        if not isinstance(tag, dict):
            continue
        value = str(tag.get("tag") or "").strip()
        if value and value not in seen:
            seen.add(value)
            confidence = tag.get("confidence")
            items.append(
                {
                    "tag": value,
                    "source": tag.get("source") or "composedMetadata.derivedTags",
                    "evidence": tag.get("evidence") or f"composedMetadata.derivedTags contains {value}",
                    "confidence": confidence if confidence in {"high", "medium", "low"} else "medium",
                    "reason": tag.get("reason") or "検索・分類に使える自動タグ候補として提示します。",
                    "manualFlag": bool(tag.get("manual_flag")),
                    "tagRuleVersion": tag.get("tag_rule_version"),
                }
            )
    return items


def _tags_for_target(tags: list[dict], target_key: str) -> list[dict]:
    selected: list[dict] = []
    for item in tags:
        tag = item["tag"]
        if target_key == "drawing":
            selected.append(item)
        elif target_key == "project" and (tag.startswith("客先:") or tag.startswith("装置:")):
            selected.append(item)
        elif target_key == "product" and (tag.startswith("客先:") or tag.startswith("装置:") or tag.startswith("PRFX:") or tag.startswith("ユニット:")):
            selected.append(item)
        elif target_key == "part" and (
            tag.startswith("材質:")
            or tag.startswith("メーカー:")
            or tag.startswith("規格:")
        ):
            selected.append(item)
    return selected


def _tag_values(tags: list[dict]) -> list[str]:
    return [item["tag"] for item in tags]


def _tag_fallback_attributes(tags: list[dict]) -> list[dict]:
    return [
        {
            "sourcePath": "composedMetadata.derivedTags",
            "attributeName": "自動タグ候補",
            "attribute": None,
            "attributeOption": None,
            "attributeValue": item["tag"],
            "evidence": item["evidence"],
            "confidence": item["confidence"],
            "reason": f"対象ページにタグ専用の保存口が未確認のため、{item['reason']}",
            "payloadShape": {
                "attribute": None,
                "attribute_option": None,
                "attribute_value": item["tag"],
            },
            "bindingStatus": "needs_attribute_master_binding",
        }
        for item in tags
    ]


def _part_material_attributes(canonical_attributes: dict) -> list[dict]:
    items: list[dict] = []
    for candidate in (canonical_attributes.get("part_material_candidates") or [])[:12]:
        value = candidate.get("canonical_material") or candidate.get("material_id") or candidate.get("material_name")
        if not _has_value(value):
            continue
        part_hint = candidate.get("part_path") or candidate.get("part_name")
        items.append(
            {
                "sourcePath": "canonicalAttributes.part_material_candidates",
                "entityHint": part_hint,
                "attributeName": "材質",
                "attribute": None,
                "attributeOption": None,
                "attributeValue": str(value),
                "evidence": candidate.get("evidence")
                or candidate.get("material_name")
                or "canonicalAttributes.part_material_candidates",
                "confidence": candidate.get("confidence") if candidate.get("confidence") in {"high", "medium", "low"} else "medium",
                "reason": candidate.get("reason")
                or "3Dパーツ材質候補またはパーツ付加情報から材質として正規化できるため、部品属性候補として提示します。",
                "payloadShape": {
                    "attribute": None,
                    "attribute_option": None,
                    "attribute_value": str(value),
                },
                "bindingStatus": "needs_part_record_and_attribute_master_binding",
            }
        )
    return items


def _target_payload(
    *,
    target_key: str,
    label: str,
    existing_reception: str,
    candidate_endpoint: str | None,
    attributes: list[dict],
    tags: list[dict],
    tag_api_status: str,
    notes: list[str],
) -> dict:
    attribute_payloads = [item["payloadShape"] for item in attributes]
    tag_values = _tag_values(tags)
    payload_preview: dict = {"attributes": attribute_payloads}
    if tag_values and tag_api_status == "candidate_existing":
        payload_preview["tags"] = tag_values

    return {
        "targetKey": target_key,
        "label": label,
        "existingReception": existing_reception,
        "candidateEndpoint": candidate_endpoint,
        "writePolicy": "preview_only_no_production_write",
        "tagApiStatus": tag_api_status,
        "tags": tag_values,
        "tagEvidence": tags,
        "attributes": attributes,
        "payloadPreview": payload_preview,
        "attributePayloadKeys": list(ATTRIBUTE_VALUE_KEYS),
        "reviewRequired": True,
        "notes": notes,
    }


def build_knowledge_system_payload_preview(*, drawing: RegisteredDrawing, composed_metadata: dict) -> dict:
    canonical_attributes = composed_metadata.get("canonicalAttributes", {}) or {}
    tags = _tag_items(composed_metadata.get("derivedTags", []) or [])

    drawing_tags = _tags_for_target(tags, "drawing")
    product_tags = _tags_for_target(tags, "product")
    part_tags = _tags_for_target(tags, "part")
    project_tags = _tags_for_target(tags, "project")

    drawing_attributes = _attribute_items(canonical_attributes, DRAWING_ATTRIBUTE_SPECS)
    product_attributes = _attribute_items(canonical_attributes, PRODUCT_ATTRIBUTE_SPECS)
    part_attributes = (
        _attribute_items(canonical_attributes, PART_ATTRIBUTE_SPECS)
        + _part_material_attributes(canonical_attributes)
        + _tag_fallback_attributes(part_tags)
    )
    project_attributes = _attribute_items(canonical_attributes, PROJECT_ATTRIBUTE_SPECS) + _tag_fallback_attributes(project_tags)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "source": {
            "drawingId": str(drawing.id),
            "hostDrawingId": drawing.host_drawing_id,
            "filename": drawing.filename,
            "sourcePath": drawing.source_path,
            "sourceFormat": drawing.source_format,
        },
        "contractEvidence": {
            "frontendProbePath": "output/knowledge_ui_screenshots_2026-07-15/frontend_entity_payload_contract_probe.json",
            "attributeValueShape": {
                "attribute": "attribute master id; Souya binding required",
                "attribute_option": "option id when input type is select; Souya binding required",
                "attribute_value": "free text value",
            },
            "productionWritePolicy": "本番ナレッジシステムへ登録・変更・削除は行わず、fixture/API上のプレビューだけを生成する。",
        },
        "targets": [
            _target_payload(
                target_key="drawing",
                label="図面",
                existing_reception="図面詳細にタグと属性情報が表示され、drawing_attributes マスタAPI候補も本番フロント資産で確認済み。",
                candidate_endpoint="/drawings/{drawingInternalId}/ または同等の図面更新API（創屋確認前）",
                attributes=drawing_attributes,
                tags=drawing_tags,
                tag_api_status="candidate_existing",
                notes=[
                    "図面の tags は既存表示口があるため第一優先の連携候補。",
                    "attribute / attribute_option は本番マスタIDが必要なため、ここでは名前と値のプレビューに留める。",
                ],
            ),
            _target_payload(
                target_key="product",
                label="製品・装置・ユニット",
                existing_reception="詳細画面に属性情報が表示され、product_attributes マスタAPI候補を確認済み。タグ欄は未確認。",
                candidate_endpoint="/products/{productInternalId}/ または同等の製品・装置・ユニット更新API（創屋確認前）",
                attributes=product_attributes + _tag_fallback_attributes(product_tags),
                tags=product_tags,
                tag_api_status="not_found_use_attribute_fallback",
                notes=[
                    "装置カテゴリ、PRFX、ユニット番号は製品・装置・ユニット側の検索/絞り込みに効く候補。",
                    "タグ専用口が未確認のため、自動タグ候補は属性値として代替できる形も併記する。",
                ],
            ),
            _target_payload(
                target_key="part",
                label="部品",
                existing_reception="詳細画面に属性情報が表示され、part_attributes マスタAPI候補を確認済み。タグ欄は未確認。",
                candidate_endpoint="/parts/{partInternalId}/ または同等の部品更新API（創屋確認前）",
                attributes=part_attributes,
                tags=part_tags,
                tag_api_status="not_found_use_attribute_fallback",
                notes=[
                    "3Dパーツ付加情報と材質候補は部品側の属性候補として扱う。",
                    "部品レコードとの突合キーは未確定のため、entityHint にパーツパス/パーツ名を保持する。",
                ],
            ),
            _target_payload(
                target_key="project",
                label="プロジェクト",
                existing_reception="本番フロント資産では project_attributes / project tags を未確認。",
                candidate_endpoint=None,
                attributes=project_attributes,
                tags=project_tags,
                tag_api_status="not_found_requires_souya_extension",
                notes=[
                    "客先・案件・装置カテゴリはプロジェクト側でも有効だが、既存保存口は創屋確認が必要。",
                    "既存APIが無い場合は補助タブ、関連図面由来の集約、または新規属性APIのいずれかを検討する。",
                ],
            ),
        ],
    }
