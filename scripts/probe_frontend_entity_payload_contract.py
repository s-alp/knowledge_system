from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_JS_ASSET_URL = "http://210.165.3.139/web/assets/index-B8bCj6lB.js"


PATTERNS_BY_ENTITY = {
    "drawing": [
        r"/drawings/",
        r"/drawings/internals/",
        r"drawing_no",
        r"drawing_name",
        r"tags:e\.tags",
        r"attributes:e\.attributes\.map",
    ],
    "product": [
        r"/products/",
        r"/products/internals/",
        r"product_name",
        r"attributes:e\.attributes\.map",
    ],
    "part": [
        r"/parts/",
        r"/parts/internals/",
        r"part_name",
        r"attributes:e\.attributes\.map",
    ],
    "project": [
        r"/projects/",
        r"/projects/internals/",
        r"project_name",
        r"attributes:e\.attributes\.map",
        r"tags:e\.tags",
    ],
}

PAYLOAD_FIELD_PATTERNS = {
    "attributeValueShape": r"attribute:n\.attributeId,attribute_option:n\.optionValueId,attribute_value:n\.attributeValue",
    "tagsDirect": r"tags:e\.tags",
    "drawingNo": r"drawing_no:e\.drawingNo",
    "drawingName": r"drawing_name:e\.drawingName",
    "paperSize": r"paper_size:e\.paperSize",
    "owner": r"owner:e\.owner",
    "productName": r"product_name:e\.productName",
    "partName": r"part_name:e\.partName",
}


def _read_js(asset_url: str | None, input_path: Path | None) -> tuple[str, str]:
    if input_path:
        return input_path.read_text(encoding="utf-8"), str(input_path)
    if not asset_url:
        raise ValueError("asset_url or input_path is required")
    with urllib.request.urlopen(asset_url, timeout=30) as response:
        body = response.read()
    return body.decode("utf-8", errors="replace"), asset_url


def _snippets(text: str, pattern: str, *, limit: int = 5, radius: int = 900) -> list[dict]:
    snippets: list[dict] = []
    for match in re.finditer(pattern, text):
        start = max(match.start() - radius, 0)
        end = min(match.end() + radius, len(text))
        snippets.append(
            {
                "offset": match.start(),
                "pattern": pattern,
                "snippet": text[start:end],
            }
        )
        if len(snippets) >= limit:
            break
    return snippets


def _entity_snippets(text: str) -> dict:
    result = {}
    for entity, patterns in PATTERNS_BY_ENTITY.items():
        evidence = []
        for pattern in patterns:
            evidence.extend(_snippets(text, pattern, limit=2, radius=700))
        result[entity] = {
            "patternHitCount": len(evidence),
            "evidence": evidence,
        }
    return result


def _field_shape_hits(text: str) -> dict:
    return {
        name: {
            "found": bool(re.search(pattern, text)),
            "evidence": _snippets(text, pattern, limit=3, radius=700),
        }
        for name, pattern in PAYLOAD_FIELD_PATTERNS.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="本番フロントbundleから個別エンティティpayload候補を静的解析します。")
    parser.add_argument("--asset-url", default=DEFAULT_JS_ASSET_URL)
    parser.add_argument("--input", type=Path, help="既に保存済みのbundle JS。指定時はasset-urlを読みに行きません。")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    js_text, source = _read_js(args.asset_url, args.input)
    payload = {
        "inspectedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "jsLength": len(js_text),
        "fieldShapeHits": _field_shape_hits(js_text),
        "entitySnippets": _entity_snippets(js_text),
        "inferredContract": {
            "attributeValueShape": {
                "payloadKeys": ["attribute", "attribute_option", "attribute_value"],
                "frontendSourceShape": ["attributeId", "optionValueId", "attributeValue"],
                "appliesTo": ["drawing", "product", "part"],
                "certainty": "medium",
                "reason": "bundle内で個別レコード送信時の attributes.map が共通形状に見える。実API仕様は創屋確認が必要。",
            },
            "drawingTags": {
                "payloadKey": "tags",
                "frontendSourceShape": "tags",
                "appliesTo": ["drawing"],
                "certainty": "medium",
                "reason": "図面詳細表示で tags が表示され、bundle内に tags:e.tags の送信候補がある。タグ保存APIの正確な責務は創屋確認が必要。",
            },
            "projectTagsOrAttributes": {
                "payloadKey": None,
                "appliesTo": ["project"],
                "certainty": "low",
                "reason": "project_attributes と project tags はbundle内で確認できない。プロジェクト向けタグは既存API追加か補助情報扱いが必要。",
            },
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
