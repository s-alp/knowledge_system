from __future__ import annotations

import os
import platform
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.drawing_metadata.tasks.extraction_tasks import claim_next_job, claim_next_jobs, process_job, process_jobs
from apps.drawing_metadata.services.worker_status import write_worker_heartbeat


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
        parser.add_argument("--batch-size", type=int, default=settings.DRAWING_METADATA_WORKER_BATCH_SIZE)

    def handle(self, *args, **options) -> None:
        if not options["once"] and not options["loop"]:
            raise SystemExit("--once か --loop のいずれかを指定してください。")

        worker_name = options["worker_name"]
        mode = options["mode"]
        runner_mode = "once" if options["once"] else "loop"
        batch_size = max(int(options["batch_size"]), 1)
        write_worker_heartbeat(
            worker_name=worker_name,
            mode=mode,
            state="starting",
            runner_mode=runner_mode,
            batch_size=batch_size if runner_mode == "loop" else None,
        )

        if options["once"]:
            write_worker_heartbeat(worker_name=worker_name, mode=mode, state="claiming", runner_mode="once")
            job = claim_next_job(worker_name=worker_name, mode=mode)
            if not job:
                write_worker_heartbeat(worker_name=worker_name, mode=mode, state="completed", runner_mode="once")
                self.stdout.write("queued job is not found")
                return
            write_worker_heartbeat(worker_name=worker_name, mode=mode, state="processing", job_id=str(job.id), runner_mode="once")
            process_job(job.id)
            write_worker_heartbeat(worker_name=worker_name, mode=mode, state="completed", runner_mode="once")
            self.stdout.write(f"processed {job.id}")
            return

        while True:
            write_worker_heartbeat(
                worker_name=worker_name,
                mode=mode,
                state="claiming",
                runner_mode="loop",
                batch_size=batch_size,
            )
            jobs = claim_next_jobs(worker_name=worker_name, mode=mode, limit=batch_size)
            if jobs:
                job_ids = ",".join(str(job.id) for job in jobs)
                write_worker_heartbeat(
                    worker_name=worker_name,
                    mode=mode,
                    state="processing",
                    job_id=job_ids,
                    runner_mode="loop",
                    batch_size=len(jobs),
                )
                processed_jobs = process_jobs(jobs)
                succeeded_count = sum(1 for job in processed_jobs if job.status == job.STATUS_SUCCEEDED)
                failed_count = sum(1 for job in processed_jobs if job.status == job.STATUS_FAILED)
                write_worker_heartbeat(
                    worker_name=worker_name,
                    mode=mode,
                    state="idle",
                    runner_mode="loop",
                    batch_size=batch_size,
                )
                self.stdout.write(f"processed batch total={len(processed_jobs)} succeeded={succeeded_count} failed={failed_count}")
                continue
            write_worker_heartbeat(worker_name=worker_name, mode=mode, state="idle", runner_mode="loop", batch_size=batch_size)
            time.sleep(options["sleep_seconds"])
