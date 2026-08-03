"""ICAD/STEPの3D部品・材質・重量候補を対象別に整理する。

アセンブリ本体と外部参照パーツを混ぜず、材質の採否理由を候補へ保持する。
入力dictだけを読み、ICAD、ファイル、DBを操作しない。
"""
from __future__ import annotations

from icad_tag_extraction.normalization_material import *  # noqa: F403
from icad_tag_extraction.normalization_text import *  # noqa: F403

def _material_id(material: dict) -> str | None:
    return material.get("mat_id") or material.get("matid")


def _material_name(material: dict) -> str | None:
    return material.get("name") or material.get("material_name")


def _part_path(part: dict, index: int) -> str:
    return ".".join(part.get("tree_path", []) or [part.get("name") or f"part_{index}"])


def _build_part_material_candidates(parts: list[dict], materials: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, str | None, str]] = set()

    for index, part in enumerate(parts):
        part_path = _part_path(part, index)
        for material in _normalize_material_items(part.get("materials", []) or []):
            material_id = _material_id(material)
            material_name = _material_name(material)
            material_key = material_id or material_name
            classification = _classify_material_value(material_key)
            if classification["status"] == "excluded":
                continue
            key = (part_path, material_key, "3d_part_material")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_id,
                    "material_name": material_name,
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": material.get("specific_gravity"),
                    "source": "3d_part_material",
                    "confidence": "high" if classification["status"] == "formal" else "low",
                    "reason": "ICAD部品ツリーのSxEntPartから材質一覧を取得できたため、当該部品の材質候補として採用しました。",
                }
            )

    if len(parts) == 1 and len(materials) == 1:
        part = parts[0]
        material = materials[0]
        part_path = _part_path(part, 0)
        material_id = _material_id(material)
        classification = _classify_material_value(material_id or material.get("name"))
        if classification["status"] != "excluded":
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_id,
                    "material_name": material.get("name"),
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": material.get("specific_gravity"),
                    "source": "3d_material_single_part",
                    "confidence": "high" if classification["status"] == "formal" else "low",
                    "reason": "単一パーツかつ3D材質一覧も単一のため、全体材質を当該パーツ候補として採用しました。",
                }
            )
            seen.add((part_path, material_id, "3d_material_single_part"))

    for index, part in enumerate(parts):
        part_path = _part_path(part, index)
        for field_key, field_value in (part.get("ex_info_fields", {}) or {}).items():
            material_text = _normalize_material_text(str(field_value))
            if not material_text:
                continue
            classification = _classify_material_value(material_text)
            if classification["status"] == "excluded":
                continue
            key = (part_path, material_text, f"part_ex_info_fields.{field_key}")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "part_path": part_path,
                    "part_name": part.get("name"),
                    "material_id": material_text,
                    "material_name": str(field_value).strip(),
                    "canonical_material": classification["canonical"],
                    "material_status": classification["status"],
                    "specific_gravity": None,
                    "source": f"part_ex_info_fields.{field_key}",
                    "confidence": "medium" if classification["status"] == "formal" else "low",
                    "reason": "パーツ付加情報の値が材質表記パターンに一致したため、部品材質候補として保持しました。",
                }
            )

    return candidates

__all__ = (
    "_material_id",
    "_material_name",
    "_part_path",
    "_normalize_material_text",
    "_looks_like_weight_text",
    "_normalize_weight_to_kg_text",
    "_classify_material_value",
    "_is_unresolved_material_keyword",
    "_split_material_keywords",
    "_build_part_material_candidates",
)
