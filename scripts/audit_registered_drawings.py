from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")

import django  # noqa: E402

django.setup()

from apps.drawing_metadata.models import RegisteredDrawing  # noqa: E402
from apps.drawing_metadata.services.drawing_scope import get_active_drawing_scope  # noqa: E402


def _source_bucket(source_path: str) -> str:
    normalized = source_path.replace("/", "\\")
    if normalized.startswith(str(ROOT / "backend" / "var" / "drawing_metadata" / "uploads")):
        return "backend_uploads"
    if normalized.startswith(str(ROOT / "cad_data")):
        return "cad_data"
    if normalized.startswith("\\\\HONSYA-FILE01"):
        return "honsya_file"
    if normalized.startswith("J:") or normalized.startswith("T:"):
        return normalized[:2]
    return "other"


def main() -> int:
    drawings = list(RegisteredDrawing.objects.prefetch_related("snapshots", "jobs").order_by("filename", "created_at"))
    scope = get_active_drawing_scope()
    filename_counts = Counter(drawing.filename for drawing in drawings)
    state_counts: Counter[tuple[bool, bool]] = Counter()
    scoped_state_counts: Counter[tuple[bool, bool]] = Counter()
    bucket_counts: Counter[str] = Counter()
    scoped_count = 0
    excluded_count = 0
    problem_rows: list[tuple[str, str, str, str, str, str]] = []

    for drawing in drawings:
        modes = {snapshot.extraction_mode for snapshot in drawing.snapshots.all()}
        has_2d = "2d" in modes
        has_3d = "3d" in modes
        state_counts[(has_2d, has_3d)] += 1
        in_scope = scope.source_paths is None or drawing.source_path in scope.source_paths
        if in_scope:
            scoped_count += 1
            scoped_state_counts[(has_2d, has_3d)] += 1
        else:
            excluded_count += 1
        bucket = _source_bucket(drawing.source_path)
        bucket_counts[bucket] += 1
        if not modes or drawing.filename == "browser_icad_probe.icd" or filename_counts[drawing.filename] > 1:
            problem_rows.append(
                (
                    "scope" if in_scope else "excluded",
                    drawing.filename,
                    str(drawing.id),
                    bucket,
                    ",".join(sorted(modes)) or "-",
                    drawing.source_path,
                )
            )

    print(f"total={len(drawings)}")
    print(f"scope_mode={scope.mode}")
    print(f"scope_manifest={scope.manifest_path or '-'}")
    print(f"scoped={scoped_count}")
    print(f"excluded={excluded_count}")
    print(f"state_counts={dict(state_counts)}")
    print(f"scoped_state_counts={dict(scoped_state_counts)}")
    print(f"bucket_counts={dict(bucket_counts)}")
    print(f"duplicate_filenames={dict(sorted((k, v) for k, v in filename_counts.items() if v > 1))}")
    print("problem_rows:")
    for row_scope, filename, drawing_id, bucket, modes, source_path in problem_rows:
        print(f"{row_scope}\t{filename}\t{drawing_id}\t{bucket}\t{modes}\t{source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
