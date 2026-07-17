from __future__ import annotations

import json

from django.db.models import Prefetch, Q, TextField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drawing_metadata.api.serializers import (
    DrawingMetadataExtractionJobSerializer,
    ExtractRequestSerializer,
    ManualOverrideSerializer,
    RegisteredDrawingCreateSerializer,
    RegisteredDrawingDetailSerializer,
    RegisteredDrawingListSerializer,
)
from apps.drawing_metadata.models import DrawingMetadataExtractionJob, DrawingMetadataSnapshot, RegisteredDrawing
from apps.drawing_metadata.services.persistence import apply_manual_overrides, enqueue_extraction_job


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _positive_int_param(request, name: str, default: int, maximum: int | None = None) -> int:
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "正の整数を指定してください。"})
    if value < 1:
        raise ValidationError({name: "正の整数を指定してください。"})
    if maximum is not None:
        value = min(value, maximum)
    return value


class RegistrationListApiView(APIView):
    def get(self, request):
        queryset = RegisteredDrawing.objects.prefetch_related(
            Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
            "jobs",
        ).all()

        # フィルタは統合結果(DrawingComposedMetadata)の確定値を参照する。
        customer = request.query_params.get("customer")
        if customer:
            queryset = queryset.filter(composed_metadata__canonical_attributes_json__customer_name=customer)
        equipment_category = request.query_params.get("equipmentCategory")
        if equipment_category:
            queryset = queryset.filter(
                composed_metadata__canonical_attributes_json__equipment_category=equipment_category
            )
        tag = request.query_params.get("tag")
        if tag:
            # PoC 段階の部分一致検索。本体統合時はタグ中間テーブルでの完全一致に置き換える。
            # SQLite の JSONField は非 ASCII を \uXXXX で保存するため、エスケープ形も併せて照合する。
            escaped_tag = json.dumps(tag, ensure_ascii=True)[1:-1]
            queryset = queryset.annotate(
                composed_tags_text=Cast("composed_metadata__derived_tags_json", TextField())
            ).filter(Q(composed_tags_text__icontains=tag) | Q(composed_tags_text__icontains=escaped_tag))
        mode = request.query_params.get("mode")
        if mode:
            queryset = queryset.filter(snapshots__extraction_mode=mode).distinct()
        job_status = request.query_params.get("jobStatus")
        if job_status:
            queryset = queryset.filter(jobs__status=job_status).distinct()

        page = _positive_int_param(request, "page", default=1)
        page_size = _positive_int_param(request, "pageSize", default=DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE)
        total = queryset.count()
        offset = (page - 1) * page_size
        items = queryset[offset : offset + page_size]

        return Response(
            {
                "items": RegisteredDrawingListSerializer(items, many=True).data,
                "page": page,
                "pageSize": page_size,
                "total": total,
            }
        )

    def post(self, request):
        serializer = RegisteredDrawingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        drawing = serializer.save()
        return Response(RegisteredDrawingDetailSerializer(drawing).data, status=status.HTTP_201_CREATED)


class RegistrationDetailApiView(APIView):
    def get(self, request, drawing_id):
        drawing = get_object_or_404(
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            ),
            pk=drawing_id,
        )
        return Response(RegisteredDrawingDetailSerializer(drawing).data)


class RegistrationExtractApiView(APIView):
    def post(self, request, drawing_id):
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        serializer = ExtractRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = enqueue_extraction_job(
            drawing=drawing,
            extraction_mode=serializer.validated_data["extractionMode"],
            reason="API requested re-extract",
            executed_by="api",
        )
        return Response(DrawingMetadataExtractionJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class RegistrationOverrideApiView(APIView):
    def patch(self, request, drawing_id):
        drawing = get_object_or_404(RegisteredDrawing, pk=drawing_id)
        serializer = ManualOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        snapshot = apply_manual_overrides(
            drawing=drawing,
            extraction_mode=serializer.validated_data["extractionMode"],
            payload=serializer.validated_data,
            reason=serializer.validated_data.get("reason", ""),
            executed_by="api",
        )
        return Response(
            {
                "drawingId": str(drawing.id),
                "extractionMode": snapshot.extraction_mode,
                "manualOverrides": snapshot.manual_overrides_json,
                "canonicalAttributes": snapshot.canonical_attributes_json,
                "derivedTags": snapshot.derived_tags_json,
            }
        )


class JobDetailApiView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(DrawingMetadataExtractionJob.objects.select_related("drawing"), pk=job_id)
        return Response(DrawingMetadataExtractionJobSerializer(job).data)
