from __future__ import annotations

"""Persistence helpers for short-lived viewer sessions and jobs."""

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.viewer.models import Viewer2DSession, Viewer3DJob


@dataclass(slots=True)
class JobStore:
    """Wrap ORM operations so services can express state changes in one place."""

    ttl_seconds: int

    def create_2d_session(self, **kwargs) -> Viewer2DSession:
        return Viewer2DSession.objects.create(
            expires_at=timezone.now() + timedelta(seconds=self.ttl_seconds),
            **kwargs,
        )

    def get_2d_session(self, session_id: str) -> Viewer2DSession:
        return Viewer2DSession.objects.get(pk=session_id)

    def create_3d_job(self, **kwargs) -> Viewer3DJob:
        return Viewer3DJob.objects.create(
            expires_at=timezone.now() + timedelta(seconds=self.ttl_seconds),
            **kwargs,
        )

    def get_3d_job(self, job_id: str) -> Viewer3DJob:
        return Viewer3DJob.objects.get(pk=job_id)

    def get_cached_ready_job(self, source_url_hash: str) -> Viewer3DJob | None:
        return (
            Viewer3DJob.objects.filter(
                source_url_hash=source_url_hash,
                status=Viewer3DJob.STATUS_READY,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )

    def mark_processing(self, job: Viewer3DJob) -> Viewer3DJob:
        job.status = Viewer3DJob.STATUS_PROCESSING
        job.error_message = ""
        job.save(update_fields=["status", "error_message", "updated_at"])
        return job

    def mark_ready(self, job: Viewer3DJob, *, model_artifact_path: str, model_format: str) -> Viewer3DJob:
        job.status = Viewer3DJob.STATUS_READY
        job.model_artifact_path = model_artifact_path
        job.model_format = model_format
        job.error_message = ""
        job.save(update_fields=["status", "model_artifact_path", "model_format", "error_message", "updated_at"])
        return job

    def mark_failed(self, job: Viewer3DJob, error_message: str) -> Viewer3DJob:
        job.status = Viewer3DJob.STATUS_FAILED
        job.error_message = error_message
        job.save(update_fields=["status", "error_message", "updated_at"])
        return job

    def cleanup_expired(self) -> tuple[list[str], list[str]]:
        session_paths = list(
            Viewer2DSession.objects.filter(expires_at__lte=timezone.now()).values_list("artifact_path", flat=True)
        )
        job_source_paths = list(
            Viewer3DJob.objects.filter(expires_at__lte=timezone.now()).values_list("source_artifact_path", flat=True)
        )
        job_model_paths = list(
            Viewer3DJob.objects.filter(expires_at__lte=timezone.now()).values_list("model_artifact_path", flat=True)
        )
        Viewer2DSession.objects.filter(expires_at__lte=timezone.now()).delete()
        Viewer3DJob.objects.filter(expires_at__lte=timezone.now()).delete()
        return session_paths + job_source_paths, job_model_paths
