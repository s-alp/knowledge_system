from __future__ import annotations

from django.conf import settings


def build_derived_tags(canonical_attributes: dict, excluded_sources: set[str] | None = None) -> list[dict]:
    excluded_sources = excluded_sources or set()
    tags: list[dict] = []

    def add_tag(tag: str, source: str, confidence: str = "high") -> None:
        if any(item["tag"] == tag for item in tags):
            return
        tags.append(
            {
                "tag": tag,
                "source": source,
                "confidence": confidence,
                "manual_flag": False,
                "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
            }
        )

    if canonical_attributes.get("customer_name") and "customer_name" not in excluded_sources:
        add_tag(f"客先:{canonical_attributes['customer_name']}", "customer_name")
    if canonical_attributes.get("equipment_category") and "equipment_category" not in excluded_sources:
        add_tag(f"装置:{canonical_attributes['equipment_category']}", "equipment_category")
    if "maker_keywords" not in excluded_sources:
        for maker in canonical_attributes.get("maker_keywords", []):
            add_tag(f"メーカー:{maker}", "maker_keywords", confidence="medium")
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
    if "geometry_feature_candidates" not in excluded_sources:
        for candidate in canonical_attributes.get("geometry_feature_candidates", []) or []:
            tag = candidate.get("tag")
            if tag:
                add_tag(tag, "geometry_feature_candidates", confidence=candidate.get("confidence", "low"))

    return tags
