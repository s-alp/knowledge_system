from __future__ import annotations

"""Database models for short-lived viewer artifacts and conversion jobs."""

import uuid

from django.db import models


class Viewer2DSession(models.Model):
    """A stored 2D source plus the metadata the frontend needs to render it."""

    # URL で再取得する前提なので、アップロード品も含め viewer 側で一意 ID を採番する。
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_url = models.URLField()
    source_url_hash = models.CharField(max_length=64, db_index=True)
    filename = models.CharField(max_length=255)
    extension = models.CharField(max_length=32)
    mime_type = models.CharField(max_length=255)
    artifact_path = models.CharField(max_length=512)
    page_count = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Viewer3DJob(models.Model):
    """A 3D source and the derived model artifact exposed to the frontend."""

    # frontend の polling 状態と 1 対 1 で対応する、最小限の状態だけを保持する。
    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_READY = "ready"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_READY, "Ready"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_url = models.URLField()
    source_url_hash = models.CharField(max_length=64, db_index=True)
    filename = models.CharField(max_length=255)
    source_extension = models.CharField(max_length=32)
    source_mime_type = models.CharField(max_length=255)
    # source と model を分けておくと、元データと表示用メッシュの両方を管理できる。
    source_artifact_path = models.CharField(max_length=512)
    model_artifact_path = models.CharField(max_length=512, blank=True)
    model_format = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    error_message = models.TextField(blank=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
