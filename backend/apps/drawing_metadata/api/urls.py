from django.urls import path

from apps.drawing_metadata.api import views


urlpatterns = [
    path(
        "drawing-metadata/settings/tag-automation",
        views.TagAutomationSettingsApiView.as_view(),
        name="drawing-metadata-tag-automation-settings",
    ),
    path(
        "drawing-metadata/settings/tag-automation/",
        views.TagAutomationSettingsApiView.as_view(),
        name="drawing-metadata-tag-automation-settings-slash",
    ),
    path(
        "drawing-metadata/handoff-summary",
        views.HandoffSummaryApiView.as_view(),
        name="drawing-metadata-handoff-summary",
    ),
    path(
        "drawing-metadata/handoff-summary/",
        views.HandoffSummaryApiView.as_view(),
        name="drawing-metadata-handoff-summary-slash",
    ),
    path("drawing-metadata/tag-dictionaries", views.TagDictionaryListApiView.as_view(), name="drawing-metadata-tag-dictionary-list"),
    path("drawing-metadata/tag-dictionaries/", views.TagDictionaryListApiView.as_view(), name="drawing-metadata-tag-dictionary-list-slash"),
    path("drawing-metadata/tag-dictionaries/<int:entry_id>", views.TagDictionaryDetailApiView.as_view(), name="drawing-metadata-tag-dictionary-detail"),
    path("drawing-metadata/tag-dictionaries/<int:entry_id>/", views.TagDictionaryDetailApiView.as_view(), name="drawing-metadata-tag-dictionary-detail-slash"),
    path("knowledge-entities", views.IcadEntityListApiView.as_view(), name="icad-knowledge-entity-list"),
    path("knowledge-entities/", views.IcadEntityListApiView.as_view(), name="icad-knowledge-entity-list-slash"),
    path("drawing-options", views.DrawingOptionListApiView.as_view(), name="drawing-option-list"),
    path("drawing-options/", views.DrawingOptionListApiView.as_view(), name="drawing-option-list-slash"),
    path(
        "knowledge-entities/<uuid:entity_id>",
        views.IcadEntityDetailApiView.as_view(),
        name="icad-knowledge-entity-detail",
    ),
    path(
        "knowledge-entities/<uuid:entity_id>/",
        views.IcadEntityDetailApiView.as_view(),
        name="icad-knowledge-entity-detail-slash",
    ),
    path("drawing-metadata/registrations", views.RegistrationListApiView.as_view(), name="drawing-metadata-registration-list"),
    path("drawing-metadata/registrations/", views.RegistrationListApiView.as_view(), name="drawing-metadata-registration-list-slash"),
    path(
        "drawing-metadata/registrations/upload",
        views.RegistrationUploadApiView.as_view(),
        name="drawing-metadata-registration-upload",
    ),
    path(
        "drawing-metadata/registrations/upload/",
        views.RegistrationUploadApiView.as_view(),
        name="drawing-metadata-registration-upload-slash",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>",
        views.RegistrationDetailApiView.as_view(),
        name="drawing-metadata-registration-detail",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/",
        views.RegistrationDetailApiView.as_view(),
        name="drawing-metadata-registration-detail-slash",
    ),
    path(
        "drawings/<uuid:drawing_id>/bootstrap",
        views.DrawingViewerBootstrapApiView.as_view(),
        name="drawing-viewer-bootstrap",
    ),
    path(
        "drawings/<uuid:drawing_id>/bootstrap/",
        views.DrawingViewerBootstrapApiView.as_view(),
        name="drawing-viewer-bootstrap-slash",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer2d/open",
        views.DrawingViewer2DOpenApiView.as_view(),
        name="drawing-viewer2d-open",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer2d/open/",
        views.DrawingViewer2DOpenApiView.as_view(),
        name="drawing-viewer2d-open-slash",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer2d/preview.svg",
        views.DrawingViewer2DPreviewApiView.as_view(),
        name="drawing-viewer2d-preview-svg",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer3d/open",
        views.DrawingViewer3DOpenApiView.as_view(),
        name="drawing-viewer3d-open",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer3d/open/",
        views.DrawingViewer3DOpenApiView.as_view(),
        name="drawing-viewer3d-open-slash",
    ),
    path(
        "drawings/<uuid:drawing_id>/viewer3d/preview.stl",
        views.DrawingViewer3DPreviewApiView.as_view(),
        name="drawing-viewer3d-preview-stl",
    ),
    path(
        "drawing-metadata-preview-assets/<uuid:job_id>/<path:filename>",
        views.DrawingPreviewAssetApiView.as_view(),
        name="drawing-metadata-preview-asset",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/extract",
        views.RegistrationExtractApiView.as_view(),
        name="drawing-metadata-registration-extract",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/extract/",
        views.RegistrationExtractApiView.as_view(),
        name="drawing-metadata-registration-extract-slash",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/overrides",
        views.RegistrationOverrideApiView.as_view(),
        name="drawing-metadata-registration-overrides",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/overrides/",
        views.RegistrationOverrideApiView.as_view(),
        name="drawing-metadata-registration-overrides-slash",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/review",
        views.RegistrationReviewApiView.as_view(),
        name="drawing-metadata-registration-review",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/review/",
        views.RegistrationReviewApiView.as_view(),
        name="drawing-metadata-registration-review-slash",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/rag-payload",
        views.RegistrationRagPayloadApiView.as_view(),
        name="drawing-metadata-registration-rag-payload",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/rag-payload/",
        views.RegistrationRagPayloadApiView.as_view(),
        name="drawing-metadata-registration-rag-payload-slash",
    ),
    path("drawing-metadata/jobs/<uuid:job_id>", views.JobDetailApiView.as_view(), name="drawing-metadata-job-detail"),
    path("drawing-metadata/jobs/<uuid:job_id>/", views.JobDetailApiView.as_view(), name="drawing-metadata-job-detail-slash"),
]
