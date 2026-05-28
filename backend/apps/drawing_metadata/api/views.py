from __future__ import annotations

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
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


class RegistrationListApiView(APIView):
    def get(self, request):
        drawings = (
            RegisteredDrawing.objects.prefetch_related(
                Prefetch("snapshots", queryset=DrawingMetadataSnapshot.objects.select_related("latest_job")),
                "jobs",
            )
            .all()
        )
        return Response(RegisteredDrawingListSerializer(drawings, many=True).data)

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
