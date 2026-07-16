from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

    import django

    django.setup()

    from apps.drawing_metadata.api.serializers import RegisteredDrawingDetailSerializer
    from apps.drawing_metadata.models import RegisteredDrawing

    drawing = (
        RegisteredDrawing.objects.prefetch_related("snapshots", "jobs", "audit_logs")
        .filter(snapshots__isnull=False)
        .distinct()
        .order_by("-updated_at")
        .first()
    )
    if drawing is None:
        raise SystemExit("snapshot付きの登録図面が見つかりません。")

    payload = RegisteredDrawingDetailSerializer(drawing).data
    knowledge_detail = payload["viewerBootstrap"]["metadata"]["knowledgeDetail"]
    result = {
        "drawingId": str(drawing.id),
        "filename": drawing.filename,
        "schemaVersion": knowledge_detail.get("schemaVersion"),
        "attributes": len(knowledge_detail.get("attributes") or []),
        "revisionHistory": len(knowledge_detail.get("revisionHistory") or []),
        "relatedTabs": len(knowledge_detail.get("relatedTabs") or []),
        "changeHistory": len(knowledge_detail.get("changeHistory") or []),
        "tagAttributeTargets": len(knowledge_detail.get("tagAttributeTargets") or []),
        "firstRelatedTab": (knowledge_detail.get("relatedTabs") or [None])[0],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
