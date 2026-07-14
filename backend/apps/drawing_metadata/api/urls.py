from django.urls import path

from apps.drawing_metadata.api import views


urlpatterns = [
    path("drawing-metadata/registrations", views.RegistrationListApiView.as_view(), name="drawing-metadata-registration-list"),
    path("drawing-metadata/registrations/", views.RegistrationListApiView.as_view(), name="drawing-metadata-registration-list-slash"),
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
