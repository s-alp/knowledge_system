from __future__ import annotations

from rest_framework import serializers

from apps.drawing_metadata.models import (
    DrawingMetadataExtractionJob,
    DrawingMetadataSnapshot,
    RegisteredDrawing,
    EXTRACTION_MODE_CHOICES,
)
from apps.drawing_metadata.services.composition import compose_drawing_metadata


class RegisteredDrawingCreateSerializer(serializers.ModelSerializer):
    hostDrawingId = serializers.CharField(source="host_drawing_id", allow_blank=True, required=False)
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")

    class Meta:
        model = RegisteredDrawing
        fields = ("id", "hostDrawingId", "filename", "sourcePath", "sourceFormat")
        read_only_fields = ("id",)

    def validate(self, attrs):
        source_path = attrs.get("source_path")
        if source_path and RegisteredDrawing.objects.filter(source_path=source_path).exists():
            raise serializers.ValidationError(
                {"sourcePath": "同じ sourcePath の図面が既に登録されています。再抽出は既存図面の extract を使ってください。"}
            )
        return attrs


class ExtractRequestSerializer(serializers.Serializer):
    extractionMode = serializers.ChoiceField(choices=EXTRACTION_MODE_CHOICES)


class DrawingMetadataExtractionJobSerializer(serializers.ModelSerializer):
    jobId = serializers.UUIDField(source="id")
    drawingId = serializers.UUIDField(source="drawing_id")
    extractionMode = serializers.CharField(source="extraction_mode")
    workerName = serializers.CharField(source="worker_name", allow_blank=True)
    leaseExpiresAt = serializers.DateTimeField(source="lease_expires_at", allow_null=True)
    retryCount = serializers.IntegerField(source="retry_count")
    startedAt = serializers.DateTimeField(source="started_at", allow_null=True)
    finishedAt = serializers.DateTimeField(source="finished_at", allow_null=True)
    elapsedMs = serializers.IntegerField(source="elapsed_ms", allow_null=True)
    errorMessage = serializers.CharField(source="error_message", allow_blank=True)
    warnings = serializers.JSONField(source="warnings_json")
    extractorName = serializers.CharField(source="extractor_name", allow_blank=True)
    extractorVersion = serializers.CharField(source="extractor_version", allow_blank=True)
    schemaVersion = serializers.CharField(source="schema_version", allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = DrawingMetadataExtractionJob
        fields = (
            "jobId",
            "drawingId",
            "extractionMode",
            "status",
            "workerName",
            "leaseExpiresAt",
            "retryCount",
            "startedAt",
            "finishedAt",
            "elapsedMs",
            "errorMessage",
            "warnings",
            "extractorName",
            "extractorVersion",
            "schemaVersion",
            "createdAt",
            "updatedAt",
        )


class SnapshotSerializer(serializers.ModelSerializer):
    extractionMode = serializers.CharField(source="extraction_mode")
    latestJob = serializers.SerializerMethodField()
    rawExtract = serializers.JSONField(source="raw_extract_json")
    canonicalAttributes = serializers.JSONField(source="canonical_attributes_json")
    derivedTags = serializers.JSONField(source="derived_tags_json")
    manualOverrides = serializers.JSONField(source="manual_overrides_json")
    updatedAt = serializers.DateTimeField(source="updated_at")
    updatedBy = serializers.CharField(source="updated_by", allow_blank=True)

    class Meta:
        model = DrawingMetadataSnapshot
        fields = (
            "extractionMode",
            "latestJob",
            "rawExtract",
            "canonicalAttributes",
            "derivedTags",
            "manualOverrides",
            "updatedAt",
            "updatedBy",
        )

    def get_latestJob(self, obj: DrawingMetadataSnapshot) -> dict | None:
        if not obj.latest_job:
            return None
        return DrawingMetadataExtractionJobSerializer(obj.latest_job).data


class RegisteredDrawingListSerializer(serializers.ModelSerializer):
    drawingId = serializers.UUIDField(source="id")
    hostDrawingId = serializers.CharField(source="host_drawing_id")
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")
    snapshotModes = serializers.SerializerMethodField()
    latestJobStatusByMode = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = RegisteredDrawing
        fields = (
            "drawingId",
            "hostDrawingId",
            "filename",
            "sourcePath",
            "sourceFormat",
            "snapshotModes",
            "latestJobStatusByMode",
            "createdAt",
            "updatedAt",
        )

    def get_snapshotModes(self, obj: RegisteredDrawing) -> list[str]:
        return sorted(snapshot.extraction_mode for snapshot in obj.snapshots.all())

    def get_latestJobStatusByMode(self, obj: RegisteredDrawing) -> dict[str, str | None]:
        # prefetch 済みの jobs(-created_at 順)を使い、図面ごとの追加クエリを発行しない。
        statuses: dict[str, str | None] = {"2d": None, "3d": None}
        for job in obj.jobs.all():
            if statuses.get(job.extraction_mode) is None:
                statuses[job.extraction_mode] = job.status
        return statuses


class RegisteredDrawingDetailSerializer(serializers.ModelSerializer):
    drawingId = serializers.UUIDField(source="id")
    hostDrawingId = serializers.CharField(source="host_drawing_id")
    sourcePath = serializers.CharField(source="source_path")
    sourceFormat = serializers.CharField(source="source_format")
    snapshotsByMode = serializers.SerializerMethodField()
    composedMetadata = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = RegisteredDrawing
        fields = (
            "drawingId",
            "hostDrawingId",
            "filename",
            "sourcePath",
            "sourceFormat",
            "snapshotsByMode",
            "composedMetadata",
            "createdAt",
            "updatedAt",
        )

    def get_snapshotsByMode(self, obj: RegisteredDrawing) -> dict[str, dict]:
        snapshots_by_mode: dict[str, dict] = {}
        for snapshot in obj.snapshots.all():
            snapshots_by_mode[snapshot.extraction_mode] = SnapshotSerializer(snapshot).data
        return snapshots_by_mode

    def get_composedMetadata(self, obj: RegisteredDrawing) -> dict:
        return compose_drawing_metadata(obj)


class ManualOverrideSerializer(serializers.Serializer):
    extractionMode = serializers.ChoiceField(choices=EXTRACTION_MODE_CHOICES)
    canonicalAttributes = serializers.JSONField(required=False)
    derivedTags = serializers.JSONField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
