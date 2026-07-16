from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django

django.setup()

from apps.drawing_metadata.models import DrawingMetadataSnapshot


FORBIDDEN_EXACT = {"改訂情報あり"}
FORBIDDEN_PREFIXES = ("加工指示:", "幾何公差:", "図面特徴:", "形状候補:")


def main() -> int:
    snapshots = list(DrawingMetadataSnapshot.objects.only("id", "derived_tags_json"))
    tags = [
        tag
        for snapshot in snapshots
        for tag in (snapshot.derived_tags_json or [])
        if isinstance(tag, dict)
    ]
    forbidden = [
        str(tag.get("tag") or "")
        for tag in tags
        if str(tag.get("tag") or "") in FORBIDDEN_EXACT
        or str(tag.get("tag") or "").startswith(FORBIDDEN_PREFIXES)
    ]
    missing_source = [tag for tag in tags if not str(tag.get("source") or "").strip()]
    missing_evidence = [tag for tag in tags if not str(tag.get("evidence") or "").strip()]
    missing_confidence = [tag for tag in tags if str(tag.get("confidence") or "").strip() not in {"high", "medium", "low"}]
    missing_reason = [tag for tag in tags if not str(tag.get("reason") or "").strip()]
    result = {
        "snapshotCount": len(snapshots),
        "tagCount": len(tags),
        "forbiddenTagCount": len(forbidden),
        "forbiddenTags": sorted(set(forbidden)),
        "missingSourceCount": len(missing_source),
        "missingEvidenceCount": len(missing_evidence),
        "missingConfidenceCount": len(missing_confidence),
        "missingReasonCount": len(missing_reason),
        "sourceCounts": dict(sorted(Counter(str(tag.get("source")) for tag in tags).items())),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if forbidden or missing_source or missing_evidence or missing_confidence or missing_reason else 0


if __name__ == "__main__":
    raise SystemExit(main())
