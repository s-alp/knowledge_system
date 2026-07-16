from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django  # noqa: E402

django.setup()

from apps.drawing_metadata.models import DrawingMetadataSnapshot  # noqa: E402


PART_NUMBER_KEYS = {"partno", "partnumber", "品番", "部品番号", "図番", "drawingno"}


def normalize_key(value: object) -> str:
    return "".join(str(value).lower().replace("_", " ").replace("-", " ").split())


def part_number(part: dict) -> str:
    for key, value in (part.get("ex_info_fields") or {}).items():
        if normalize_key(key) in PART_NUMBER_KEYS and str(value).strip():
            return str(value).strip()
    return ""


def identity_key(part: dict) -> str:
    ref_path = str(part.get("ref_model_path") or "").strip().lower()
    ref_name = str(part.get("ref_model_name") or "").strip().lower()
    if ref_path or ref_name:
        return f"ref:{ref_path}/{ref_name}"
    number = part_number(part)
    if number:
        return f"number:{number.lower()}"
    name = str(part.get("name") or "").strip().lower()
    return f"name:{name}"


def build_report() -> dict:
    snapshots = DrawingMetadataSnapshot.objects.filter(extraction_mode="3d").select_related("drawing")
    kind_counts: Counter[str] = Counter()
    depth_counts: Counter[int] = Counter()
    candidate_counts: Counter[str] = Counter()
    leaf_identities: Counter[str] = Counter()
    unit_identities: Counter[str] = Counter()
    examples: dict[str, list[dict]] = {
        "topLevel": [],
        "referencedAssembly": [],
        "internalGrouping": [],
        "duplicateLeaf": [],
    }

    total_parts = 0
    for snapshot in snapshots.iterator():
        parts = [part for part in (snapshot.raw_extract_json or {}).get("parts", []) if isinstance(part, dict)]
        path_counts = Counter(
            tuple(str(item).strip() for item in (part.get("tree_path") or []) if str(item).strip())
            for part in parts
        )
        inferred_child_counts: Counter[tuple[str, ...]] = Counter()
        for path, count in path_counts.items():
            if len(path) > 1:
                inferred_child_counts[path[:-1]] += count
        for part in parts:
            total_parts += 1
            path = tuple(str(item).strip() for item in (part.get("tree_path") or []) if str(item).strip())
            explicit_depth = part.get("depth")
            depth = explicit_depth if isinstance(explicit_depth, int) and explicit_depth >= 0 else max(len(path) - 1, 0)
            explicit_child_count = part.get("child_count")
            child_count = (
                explicit_child_count
                if isinstance(explicit_child_count, int) and explicit_child_count >= 0
                else inferred_child_counts[path]
            )
            kind_counts[str(part.get("entity_kind") or "missing")] += 1
            depth_counts[depth] += 1
            identity = identity_key(part)
            row = {
                "drawing": snapshot.drawing.filename,
                "name": part.get("name"),
                "depth": depth,
                "childCount": child_count,
                "partNumber": part_number(part),
                "refModelName": part.get("ref_model_name"),
                "refModelPath": part.get("ref_model_path"),
                "isExternal": bool(part.get("is_external")),
                "identity": identity,
            }
            if child_count <= 0:
                leaf_identities[identity] += 1
                continue

            if depth == 0:
                candidate_counts["top_level_assembly"] += 1
                unit_identities[identity] += 1
                if len(examples["topLevel"]) < 20:
                    examples["topLevel"].append(row)
            elif part.get("ref_model_path") or part.get("ref_model_name") or part.get("is_external"):
                candidate_counts["referenced_assembly"] += 1
                unit_identities[identity] += 1
                if len(examples["referencedAssembly"]) < 20:
                    examples["referencedAssembly"].append(row)
            else:
                candidate_counts["internal_grouping_with_children"] += 1
                if len(examples["internalGrouping"]) < 40:
                    examples["internalGrouping"].append(row)

    duplicate_leaf_rows = [
        {"identity": identity, "occurrences": count}
        for identity, count in leaf_identities.most_common(50)
        if count > 1
    ]
    examples["duplicateLeaf"] = duplicate_leaf_rows
    return {
        "schemaVersion": "icad_entity_classification_analysis.v2",
        "registrationPolicy": {
            "unit": "icd_file",
            "candidateCount": snapshots.count(),
            "rule": "製品・装置・ユニットと部品の登録候補合計はICDファイル数と一致させる。",
        },
        "internalStructureDiagnostics": {
            "notice": "以下はICD内部ツリーの診断値であり、ナレッジシステムへの登録件数ではない。",
            "totalPartOccurrences": total_parts,
            "rawEntityKindCounts": dict(kind_counts),
            "depthCounts": {str(key): value for key, value in sorted(depth_counts.items())},
            "assemblyCandidateCounts": dict(candidate_counts),
            "uniqueUnitIdentityCount": len(unit_identities),
            "uniqueLeafIdentityCount": len(leaf_identities),
            "duplicateLeafIdentityCount": sum(1 for count in leaf_identities.values() if count > 1),
            "duplicateLeafOccurrenceCount": sum(count - 1 for count in leaf_identities.values() if count > 1),
            "examples": examples,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ICD単位の登録候補数と、内部構成ノードの診断値を分けて集計します。")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
