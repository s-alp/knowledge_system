from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_HANDOFF = ROOT / "docs" / "icad_entity_operations_and_quality_handoff_2026-07-16.md"
SHARED_39_STATUS = (
    ROOT
    / "docs"
    / "souya_icad_tag_attribute_handoff_2026-07-14_parts"
    / "souya_icad_tag_attribute_handoff_2026-07-14_10_shared_39_status.md"
)
TASKLIST = ROOT / "tasklist.md"
REVIEW_SUMMARY = ROOT / "output" / "souya_handoff" / "drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json"


def _run_json(script_name: str) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{script_name} failed: {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout)


def _review_summary_target_attribute_counts() -> dict[str, int]:
    data = json.loads(REVIEW_SUMMARY.read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    for item in data.get("items") or []:
        for target in item.get("knowledgeTargets") or []:
            target_key = str(target.get("targetKey") or "unknown")
            counts[target_key] += int(target.get("payloadAttributeCount") or target.get("attributeCount") or 0)
    return dict(counts)


def _expect_token(issues: list[dict[str, str]], path: Path, token: str, source: str) -> None:
    text = path.read_text(encoding="utf-8")
    if token not in text:
        issues.append({"file": str(path), "missingToken": token, "source": source})


def main() -> int:
    parser = argparse.ArgumentParser(description="引継ぎ資料の固定数値が現行監査結果と一致するか確認します。")
    parser.add_argument("--output", help="JSON出力先。省略時は標準出力します。")
    args = parser.parse_args()

    tag_quality = _run_json("audit_tag_quality.py")
    payload_quality = _run_json("audit_knowledge_payload_attribute_quality.py")
    target_attribute_counts = _review_summary_target_attribute_counts()
    scope = payload_quality["scope"]

    expected_attribute_line = (
        "属性候補数: "
        f"図面{target_attribute_counts.get('drawing', 0)}、"
        f"部品{target_attribute_counts.get('part', 0)}、"
        f"製品・装置・ユニット{target_attribute_counts.get('product', 0)}、"
        f"プロジェクト{target_attribute_counts.get('project', 0)}"
        f"（合計{payload_quality['attributeCount']}）"
    )
    expected_tokens = [
        (
            OPERATIONS_HANDOFF,
            f"全登録{scope['totalRegistrationCount']}件、固定manifest対象{scope['scopedRegistrationCount']}件、対象外{scope['excludedRegistrationCount']}件",
            "payload_quality.scope",
        ),
        (
            OPERATIONS_HANDOFF,
            f"snapshot {tag_quality['snapshotCount']}件、タグ{tag_quality['tagCount']}件、禁止タグ{tag_quality['forbiddenTagCount']}件",
            "tag_quality",
        ),
        (
            TASKLIST,
            f"既存{tag_quality['snapshotCount']} snapshotを再正規化",
            "tag_quality.snapshotCount",
        ),
        (
            TASKLIST,
            f"共有39件で属性{payload_quality['attributeCount']}件、対象別タグ{payload_quality['tagCount']}件",
            "payload_quality.counts",
        ),
        (
            SHARED_39_STATUS,
            expected_attribute_line,
            "review_summary.knowledgeTargets.payloadAttributeCount",
        ),
        (
            SHARED_39_STATUS,
            f"対象別タグ{payload_quality['tagCount']}件",
            "payload_quality.tagCount",
        ),
    ]

    issues: list[dict[str, str]] = []
    for path, token, source in expected_tokens:
        _expect_token(issues, path, token, source)

    result = {
        "schemaVersion": "icad_handoff_numeric_consistency_audit.v1",
        "gatePassed": not issues,
        "issueCount": len(issues),
        "issues": issues,
        "observed": {
            "tagQuality": {
                "snapshotCount": tag_quality["snapshotCount"],
                "tagCount": tag_quality["tagCount"],
                "forbiddenTagCount": tag_quality["forbiddenTagCount"],
            },
            "payloadQuality": {
                "totalRegistrationCount": scope["totalRegistrationCount"],
                "scopedRegistrationCount": scope["scopedRegistrationCount"],
                "excludedRegistrationCount": scope["excludedRegistrationCount"],
                "attributeCount": payload_quality["attributeCount"],
                "tagCount": payload_quality["tagCount"],
            },
            "targetAttributeCounts": target_attribute_counts,
        },
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result["gatePassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
