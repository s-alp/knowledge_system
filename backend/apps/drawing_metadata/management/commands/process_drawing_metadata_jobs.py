from __future__ import annotations

import os
import platform
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.drawing_metadata.tasks.extraction_tasks import claim_next_job, process_job


class Command(BaseCommand):
    help = "DB に積まれた図面メタデータ抽出ジョブを処理します。"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--loop", action="store_true")
        parser.add_argument("--mode", choices=["2d", "3d", "all"], default="all")
        parser.add_argument(
            "--worker-name",
            default=os.environ.get("COMPUTERNAME") or platform.node() or "windows-icad-worker",
        )
        parser.add_argument("--sleep-seconds", type=int, default=settings.DRAWING_METADATA_WORKER_POLL_SECONDS)

    def handle(self, *args, **options) -> None:
        if not options["once"] and not options["loop"]:
            raise SystemExit("--once か --loop のいずれかを指定してください。")

        worker_name = options["worker_name"]
        mode = options["mode"]

        if options["once"]:
            job = claim_next_job(worker_name=worker_name, mode=mode)
            if not job:
                self.stdout.write("queued job is not found")
                return
            process_job(job.id)
            self.stdout.write(f"processed {job.id}")
            return

        while True:
            job = claim_next_job(worker_name=worker_name, mode=mode)
            if job:
                process_job(job.id)
                self.stdout.write(f"processed {job.id}")
                continue
            time.sleep(options["sleep_seconds"])
