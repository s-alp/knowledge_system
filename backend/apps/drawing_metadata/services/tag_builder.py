from __future__ import annotations

from django.conf import settings


def build_derived_tags(canonical_attributes: dict, excluded_sources: set[str] | None = None) -> list[dict]:
    excluded_sources = excluded_sources or set()
    tags: list[dict] = []

    def add_tag(tag: str, source: str, confidence: str = "high", reason: str = "") -> None:
        if any(item["tag"] == tag for item in tags):
            return
        tags.append(
            {
                "tag": tag,
                "source": source,
                "confidence": confidence,
                "reason": reason or _tag_reason(source),
                "manual_flag": False,
                "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
            }
        )

    if canonical_attributes.get("customer_name") and "customer_name" not in excluded_sources:
        add_tag(f"客先:{canonical_attributes['customer_name']}", "customer_name")
    if canonical_attributes.get("project_name") and "project_name" not in excluded_sources:
        add_tag(f"案件:{canonical_attributes['project_name']}", "project_name")
    if canonical_attributes.get("equipment_category") and "equipment_category" not in excluded_sources:
        add_tag(f"装置:{canonical_attributes['equipment_category']}", "equipment_category")
    if "maker_keywords" not in excluded_sources:
        for maker in canonical_attributes.get("maker_keywords", []):
            add_tag(f"メーカー:{maker}", "maker_keywords", confidence="medium")
    if "material_keywords" not in excluded_sources:
        for material in canonical_attributes.get("material_keywords", []):
            add_tag(f"材質:{material}", "material_keywords", confidence="medium")
    if "unresolved_material_keywords" not in excluded_sources:
        for material in canonical_attributes.get("unresolved_material_keywords", []):
            add_tag(f"材質要確認:{material}", "unresolved_material_keywords", confidence="low")
    if "spec_tokens" not in excluded_sources:
        for spec in canonical_attributes.get("spec_tokens", []):
            if spec in {"SES"}:
                add_tag(f"規格:{spec}", "spec_tokens", confidence="medium")
    if "title_block_fields" not in excluded_sources:
        title_block_fields = canonical_attributes.get("title_block_fields", {}) or {}
        if title_block_fields.get("material"):
            add_tag(f"材質:{title_block_fields['material']}", "title_block_fields.material", confidence="medium")
        if title_block_fields.get("surface_treatment"):
            add_tag(f"表面処理:{title_block_fields['surface_treatment']}", "title_block_fields.surface_treatment", confidence="medium")
        if title_block_fields.get("coating_instruction"):
            add_tag(f"塗装:{title_block_fields['coating_instruction']}", "title_block_fields.coating_instruction", confidence="medium")
        if title_block_fields.get("prfx"):
            add_tag(f"PRFX:{title_block_fields['prfx']}", "title_block_fields.prfx", confidence="medium")
        if title_block_fields.get("unit_number"):
            add_tag(f"ユニット:{title_block_fields['unit_number']}", "title_block_fields.unit_number", confidence="medium")
    return tags


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
    }
    return reasons.get(source, "タグ化対象として正規化でき、検索・分類に使えるため採用しています。")
