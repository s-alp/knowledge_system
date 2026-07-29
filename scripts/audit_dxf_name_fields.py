# 変換済みDXFの文字・ブロック属性を読み、名称ラベルと値候補の取得状況を監査する。
# 既存のDXF全件監査成果物を入力とし、原本DXFは変更せず集計JSONだけを生成する。
# 失敗時はsummary.jsonと個別DXFの存在、DXF文字コード、エンティティ構造を確認する。
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DXF_AUDIT_ROOT = ROOT / "output" / "dxf_full_audit_2026-07-28"
SUMMARY_PATH = DXF_AUDIT_ROOT / "summary.json"
OUTPUT_PATH = ROOT / "output" / "drawing_entity_name_audit_2026-07-29" / "dxf_name_field_audit.json"
TEXT_TYPES = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}
NAME_LABELS = (
    "品名",
    "部品名",
    "図名",
    "図面名",
    "名称",
    "PARTNAME",
    "UNITNAME",
    "MACHINENAME",
)


def _decode_dxf(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"DXFをUTF-8またはCP932としてデコードできません: {path}")


def _pairs(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    pairs: list[tuple[str, str]] = []
    for index in range(0, len(lines) - 1, 2):
        code = lines[index].strip()
        if re.fullmatch(r"-?\d+", code):
            pairs.append((code, lines[index + 1].rstrip("\r\n")))
    return pairs


def _first(record_pairs: list[tuple[str, str]], code: str) -> str | None:
    for pair_code, value in record_pairs:
        if pair_code == code:
            stripped = value.strip()
            return stripped or None
    return None


def _float_value(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _clean_text(value: str) -> str:
    cleaned = value.replace("\\P", " ")
    cleaned = re.sub(r"\\[A-Za-z][^;{}]*;", "", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    return unicodedata.normalize("NFKC", cleaned).strip()


def _compact(value: str) -> str:
    return "".join(_clean_text(value).upper().split())


def _text_records(path: Path) -> list[dict]:
    pairs = _pairs(_decode_dxf(path))
    records: list[dict] = []
    index = 0
    while index < len(pairs):
        code, entity_type = pairs[index]
        if code != "0":
            index += 1
            continue
        next_index = index + 1
        while next_index < len(pairs) and pairs[next_index][0] != "0":
            next_index += 1
        record_pairs = pairs[index + 1 : next_index]
        normalized_type = entity_type.strip().upper()
        if normalized_type in TEXT_TYPES:
            raw_text = (
                "".join(value for pair_code, value in record_pairs if pair_code in {"3", "1"})
                if normalized_type == "MTEXT"
                else (_first(record_pairs, "1") or "")
            )
            cleaned = _clean_text(raw_text)
            if cleaned:
                records.append(
                    {
                        "entityType": normalized_type,
                        "layer": _first(record_pairs, "8"),
                        "text": cleaned,
                        "positionX": _float_value(_first(record_pairs, "10")),
                        "positionY": _float_value(_first(record_pairs, "20")),
                    }
                )
        index = next_index
    return records


def _is_name_label(text: str) -> bool:
    compact = _compact(text)
    return any(label in compact for label in NAME_LABELS)


def _nearest_texts(label: dict, text_records: list[dict]) -> list[dict]:
    label_x = label.get("positionX")
    label_y = label.get("positionY")
    if not isinstance(label_x, float) or not isinstance(label_y, float):
        return []
    candidates: list[tuple[tuple[int, float], dict]] = []
    for item in text_records:
        if item is label or _is_name_label(item["text"]):
            continue
        item_x = item.get("positionX")
        item_y = item.get("positionY")
        if not isinstance(item_x, float) or not isinstance(item_y, float):
            continue
        distance = math.hypot(item_x - label_x, item_y - label_y)
        candidates.append(
            (
                (0 if item.get("layer") == label.get("layer") else 1, distance),
                {
                    "text": item["text"],
                    "distance": round(distance, 3),
                    "sameLayer": item.get("layer") == label.get("layer"),
                    "layer": item.get("layer"),
                    "positionX": item_x,
                    "positionY": item_y,
                },
            )
        )
    return [item for _sort_key, item in sorted(candidates, key=lambda row: row[0])[:12]]


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []
    counts = Counter()
    for result in summary.get("results") or []:
        dxf_path_value = result.get("dxfPath")
        if not dxf_path_value:
            continue
        dxf_path = Path(dxf_path_value)
        if not dxf_path.is_file():
            continue
        records = _text_records(dxf_path)
        labels = [item for item in records if _is_name_label(item["text"])]
        evidence = [
            {
                **label,
                "nearestTexts": _nearest_texts(label, records),
            }
            for label in labels
        ]
        counts["audited"] += 1
        if records:
            counts["withText"] += 1
        if labels:
            counts["withNameLabel"] += 1
        rows.append(
            {
                "filename": result.get("filename"),
                "sourcePath": result.get("sourcePath"),
                "dxfPath": str(dxf_path),
                "textCount": len(records),
                "nameLabelCount": len(labels),
                "nameLabelEvidence": evidence,
            }
        )

    payload = {
        "schemaVersion": "dxf_name_field_audit.v1",
        "sourceSummary": str(SUMMARY_PATH),
        "counts": dict(counts),
        "rows": rows,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    print(f"output={OUTPUT_PATH}")
    for row in [item for item in rows if item["nameLabelCount"]][:20]:
        print(
            json.dumps(
                {
                    "filename": row["filename"],
                    "labels": [
                        {
                            "text": evidence["text"],
                            "nearestTexts": evidence["nearestTexts"][:5],
                        }
                        for evidence in row["nameLabelEvidence"]
                    ],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
