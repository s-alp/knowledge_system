from __future__ import annotations

from django.conf import settings

NAMESPACE_CUSTOMER = "客先"
NAMESPACE_EQUIPMENT = "装置"
NAMESPACE_MAKER = "メーカー"
NAMESPACE_SPEC = "規格"

TAG_DISPLAY_SEPARATOR = ":"


def format_tag_display(namespace: str, value: str) -> str:
    return f"{namespace}{TAG_DISPLAY_SEPARATOR}{value}"


def split_tag_display(display: str) -> tuple[str, str]:
    """表示文字列から namespace/value を分解する。手動タグの後方互換入力用。"""
    namespace, separator, value = display.partition(TAG_DISPLAY_SEPARATOR)
    if not separator:
        return "", display
    return namespace, value


def build_derived_tags(canonical_attributes: dict, low_confidence_sources: set[str] | None = None) -> list[dict]:
    """canonical_attributes から自動タグを再生成する。

    - タグは表示文字列だけでなく namespace/value/evidence を持つ。
    - low_confidence_sources に入っている属性由来のタグは、除外せず confidence=low で残す
      (2D/3D 競合時にタグごと消えると一覧・RAG から見えなくなるため)。
    """
    low_confidence_sources = low_confidence_sources or set()
    evidence_map = canonical_attributes.get("match_evidence") or {}
    tags: list[dict] = []

    def evidence_for(source: str, value: str) -> list[dict]:
        return [item for item in evidence_map.get(source, []) if item.get("value") == value]

    def add_tag(namespace: str, value: str, source: str, confidence: str = "high") -> None:
        display = format_tag_display(namespace, value)
        if any(item["tag"] == display for item in tags):
            return
        if source in low_confidence_sources:
            confidence = "low"
        tags.append(
            {
                "tag": display,
                "namespace": namespace,
                "value": value,
                "source": source,
                "confidence": confidence,
                "manual_flag": False,
                "tag_rule_version": settings.DRAWING_METADATA_TAG_RULE_VERSION,
                "evidence": evidence_for(source, value),
            }
        )

    customer_name = canonical_attributes.get("customer_name")
    if customer_name:
        candidates = canonical_attributes.get("customer_name_candidates") or [customer_name]
        add_tag(
            NAMESPACE_CUSTOMER,
            customer_name,
            "customer_name",
            confidence="high" if len(candidates) <= 1 else "medium",
        )

    equipment_category = canonical_attributes.get("equipment_category")
    if equipment_category:
        candidates = canonical_attributes.get("equipment_category_candidates") or [equipment_category]
        add_tag(
            NAMESPACE_EQUIPMENT,
            equipment_category,
            "equipment_category",
            confidence="high" if len(candidates) <= 1 else "medium",
        )

    for maker in canonical_attributes.get("maker_keywords") or []:
        add_tag(NAMESPACE_MAKER, maker, "maker_keywords", confidence="medium")

    for spec in canonical_attributes.get("spec_names") or []:
        add_tag(NAMESPACE_SPEC, spec, "spec_names", confidence="medium")

    return tags
