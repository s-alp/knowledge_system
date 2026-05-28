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

    return tags
