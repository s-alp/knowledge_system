from __future__ import annotations

from django.conf import settings


def build_derived_tags(canonical_attributes: dict, excluded_sources: set[str] | None = None) -> list[dict]:
    excluded_sources = excluded_sources or set()
    tags: list[dict] = []

    def add_tag(tag: str, source: str, confidence: str = "high", reason: str = "", evidence: str = "") -> None:
        if any(item["tag"] == tag for item in tags):
            return
        tags.append(
            {
                "tag": tag,
                "source": source,
                "evidence": evidence or _tag_evidence(source),
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
    if "surface_treatment_tokens" not in excluded_sources:
        for treatment in canonical_attributes.get("surface_treatment_tokens", []):
            add_tag(f"表面処理:{treatment}", "surface_treatment_tokens", confidence="medium")
    if "paint_instruction_tokens" not in excluded_sources:
        for paint in canonical_attributes.get("paint_instruction_tokens", []):
            add_tag(f"塗装:{paint}", "paint_instruction_tokens", confidence="medium")
    if "heat_treatment_keywords" not in excluded_sources:
        for treatment in canonical_attributes.get("heat_treatment_keywords", []):
            add_tag(f"熱処理:{treatment}", "heat_treatment_keywords", confidence="medium")
    if "prfx_candidates" not in excluded_sources:
        for prfx in canonical_attributes.get("prfx_candidates", []):
            add_tag(f"PRFX:{prfx}", "prfx_candidates", confidence="medium")
    if "unit_number_candidates" not in excluded_sources:
        for unit_number in canonical_attributes.get("unit_number_candidates", []):
            add_tag(f"ユニット:{unit_number}", "unit_number_candidates", confidence="medium")
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


def _tag_evidence(source: str) -> str:
    evidence = {
        "customer_name": "composedMetadata.canonicalAttributes.customer_name",
        "project_name": "composedMetadata.canonicalAttributes.project_name",
        "equipment_category": "composedMetadata.canonicalAttributes.equipment_category",
        "maker_keywords": "composedMetadata.canonicalAttributes.maker_keywords",
        "material_keywords": "composedMetadata.canonicalAttributes.material_keywords",
        "surface_treatment_tokens": "composedMetadata.canonicalAttributes.surface_treatment_tokens",
        "paint_instruction_tokens": "composedMetadata.canonicalAttributes.paint_instruction_tokens",
        "heat_treatment_keywords": "composedMetadata.canonicalAttributes.heat_treatment_keywords",
        "prfx_candidates": "composedMetadata.canonicalAttributes.prfx_candidates",
        "unit_number_candidates": "composedMetadata.canonicalAttributes.unit_number_candidates",
        "spec_tokens": "composedMetadata.canonicalAttributes.spec_tokens",
        "title_block_fields.material": "composedMetadata.canonicalAttributes.title_block_fields.material",
        "title_block_fields.surface_treatment": "composedMetadata.canonicalAttributes.title_block_fields.surface_treatment",
        "title_block_fields.coating_instruction": "composedMetadata.canonicalAttributes.title_block_fields.coating_instruction",
        "title_block_fields.prfx": "composedMetadata.canonicalAttributes.title_block_fields.prfx",
        "title_block_fields.unit_number": "composedMetadata.canonicalAttributes.title_block_fields.unit_number",
    }
    return evidence.get(source, f"composedMetadata.canonicalAttributes.{source}")


def _tag_reason(source: str) -> str:
    reasons = {
        "customer_name": "客先名として正規化でき、案件横断検索に使えるため採用しています。",
        "project_name": "案件名として正規化でき、案件単位の検索に使えるため採用しています。",
        "equipment_category": "装置カテゴリとして正規化でき、分類検索に使えるため採用しています。",
        "maker_keywords": "メーカー名として抽出でき、購入品や構成部品の検索に使えるため採用しています。",
        "material_keywords": "正式材質として分類でき、加工・調達検索に使えるため採用しています。",
        "surface_treatment_tokens": "表面処理として抽出でき、加工・処理条件の検索に使えるため採用しています。",
        "paint_instruction_tokens": "塗装指示として抽出でき、塗装条件の検索に使えるため採用しています。",
        "heat_treatment_keywords": "熱処理指定として抽出でき、加工条件の検索に使えるため採用しています。",
        "prfx_candidates": "PRFXとして抽出でき、客先・案件別の識別に使えるため採用しています。",
        "unit_number_candidates": "ユニット番号として抽出でき、ユニット単位の検索に使えるため採用しています。",
        "spec_tokens": "規格識別子として抽出でき、規格・社内標準の検索に使えるため採用しています。",
        "title_block_fields.material": "2D図枠の材質欄から抽出でき、図面起点の材質検索に使えるため採用しています。",
        "title_block_fields.surface_treatment": "2D図枠の表面処理欄から抽出でき、加工・処理条件の検索に使えるため採用しています。",
        "title_block_fields.coating_instruction": "2D図枠の塗装指示欄から抽出でき、塗装条件の検索に使えるため採用しています。",
        "title_block_fields.prfx": "2D図枠のPRFX欄から抽出でき、客先・案件別の識別に使えるため採用しています。",
        "title_block_fields.unit_number": "2D図枠のユニット番号欄から抽出でき、ユニット単位の検索に使えるため採用しています。",
    }
    return reasons.get(source, "タグ化対象として正規化でき、検索・分類に使えるため採用しています。")
