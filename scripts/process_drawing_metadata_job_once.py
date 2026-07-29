"""`process_drawing_metadata_job_once`として抽出ジョブを限定回数だけ処理して状態を確認する補助スクリプトである。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledge_system_backend.settings")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: process_drawing_metadata_job_once.py <job-id>")

    import django

    django.setup()

    from apps.drawing_metadata.models import DrawingMetadataExtractionJob
    from apps.drawing_metadata.tasks.extraction_tasks import process_job

    job = DrawingMetadataExtractionJob.objects.get(pk=sys.argv[1])
    job.worker_name = "codex-direct-2d-check"
    job.save(update_fields=["worker_name", "updated_at"])
    processed = process_job(job.id)
    print(f"{processed.id}\t{processed.extraction_mode}\t{processed.status}\t{processed.drawing.filename}")
    if processed.error_message:
        print(processed.error_message)


if __name__ == "__main__":
    main()
