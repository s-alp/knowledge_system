from __future__ import annotations

import uuid

from django.db import models


EXTRACTION_MODE_2D = "2d"
EXTRACTION_MODE_3D = "3d"
EXTRACTION_MODE_CHOICES = [
    (EXTRACTION_MODE_2D, "2D"),
    (EXTRACTION_MODE_3D, "3D"),
]


class RegisteredDrawing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host_drawing_id = models.CharField(max_length=255, blank=True)
    filename = models.CharField(max_length=255)
    source_path = models.CharField(max_length=1024)
    source_format = models.CharField(max_length=64, default="icad")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.filename


class DrawingMetadataExtractionJob(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drawing = models.ForeignKey(RegisteredDrawing, on_delete=models.CASCADE, related_name="jobs")
    extraction_mode = models.CharField(max_length=8, choices=EXTRACTION_MODE_CHOICES, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    worker_name = models.CharField(max_length=255, blank=True, db_index=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    retry_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed_ms = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    warnings_json = models.JSONField(default=list, blank=True)
    extractor_name = models.CharField(max_length=128, blank=True)
    extractor_version = models.CharField(max_length=64, blank=True)
    schema_version = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.drawing.filename}:{self.extraction_mode}:{self.status}"


class DrawingMetadataSnapshot(models.Model):
    drawing = models.ForeignKey(RegisteredDrawing, on_delete=models.CASCADE, related_name="snapshots")
    extraction_mode = models.CharField(max_length=8, choices=EXTRACTION_MODE_CHOICES, db_index=True)
    latest_job = models.ForeignKey(
        DrawingMetadataExtractionJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="latest_snapshots",
    )
    raw_extract_json = models.JSONField(default=dict, blank=True)
    canonical_attributes_json = models.JSONField(default=dict, blank=True)
    derived_tags_json = models.JSONField(default=list, blank=True)
    manual_overrides_json = models.JSONField(default=dict, blank=True)
    normalizer_version = models.CharField(max_length=32, blank=True)
    tag_rule_version = models.CharField(max_length=32, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["drawing_id", "extraction_mode"]
        constraints = [
            models.UniqueConstraint(
                fields=["drawing", "extraction_mode"],
                name="drawing_metadata_unique_snapshot_per_mode",
            )
        ]

    def __str__(self) -> str:
        return f"snapshot:{self.drawing.filename}:{self.extraction_mode}"


class DrawingComposedMetadata(models.Model):
    """2D/3D スナップショットと手動補正を合成した確定値。一覧絞り込みと RAG 投入の読み出し先。"""

    drawing = models.OneToOneField(RegisteredDrawing, on_delete=models.CASCADE, related_name="composed_metadata")
    canonical_attributes_json = models.JSONField(default=dict, blank=True)
    derived_tags_json = models.JSONField(default=list, blank=True)
    conflicts_json = models.JSONField(default=list, blank=True)
    normalizer_version = models.CharField(max_length=32, blank=True)
    tag_rule_version = models.CharField(max_length=32, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"composed:{self.drawing.filename}"


class TagDictionaryEntry(models.Model):
    """タグ・属性正規化に使う辞書。コード内 seed 定数の運用置き換え先で、admin から編集できる。"""

    KIND_CUSTOMER = "customer"
    KIND_EQUIPMENT_CATEGORY = "equipment_category"
    KIND_MAKER = "maker"
    KIND_SPEC = "spec"
    KIND_CHOICES = [
        (KIND_CUSTOMER, "客先"),
        (KIND_EQUIPMENT_CATEGORY, "装置カテゴリ"),
        (KIND_MAKER, "メーカー"),
        (KIND_SPEC, "規格"),
    ]

    id = models.BigAutoField(primary_key=True)
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, db_index=True)
    canonical_value = models.CharField(max_length=255)
    aliases_json = models.JSONField(default=list, blank=True)
    priority = models.IntegerField(default=100, help_text="小さいほど優先。複数候補時の主候補選択順。")
    enabled = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "priority", "canonical_value"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "canonical_value"],
                name="tag_dictionary_unique_kind_value",
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.canonical_value}"


class DrawingMetadataAuditLog(models.Model):
    ACTION_EXTRACTION = "extraction"
    ACTION_OVERRIDE = "override"
    ACTION_REQUEUE = "requeue"
    ACTION_RENORMALIZE = "re_normalize"
    ACTION_CHOICES = [
        (ACTION_EXTRACTION, "Extraction"),
        (ACTION_OVERRIDE, "Override"),
        (ACTION_REQUEUE, "Requeue"),
        (ACTION_RENORMALIZE, "ReNormalize"),
    ]

    id = models.BigAutoField(primary_key=True)
    drawing = models.ForeignKey(RegisteredDrawing, on_delete=models.CASCADE, related_name="audit_logs")
    extraction_mode = models.CharField(max_length=8, choices=EXTRACTION_MODE_CHOICES, db_index=True)
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    before_json = models.JSONField(default=dict, blank=True)
    after_json = models.JSONField(default=dict, blank=True)
    executed_by = models.CharField(max_length=255, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-executed_at"]

    def __str__(self) -> str:
        return f"{self.drawing.filename}:{self.extraction_mode}:{self.action_type}"
