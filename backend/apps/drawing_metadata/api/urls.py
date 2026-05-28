from django.urls import path

from apps.drawing_metadata.api import views


urlpatterns = [
    path("drawing-metadata/registrations", views.RegistrationListApiView.as_view(), name="drawing-metadata-registration-list"),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>",
        views.RegistrationDetailApiView.as_view(),
        name="drawing-metadata-registration-detail",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/extract",
        views.RegistrationExtractApiView.as_view(),
        name="drawing-metadata-registration-extract",
    ),
    path(
        "drawing-metadata/registrations/<uuid:drawing_id>/overrides",
        views.RegistrationOverrideApiView.as_view(),
        name="drawing-metadata-registration-overrides",
    ),
    path("drawing-metadata/jobs/<uuid:job_id>", views.JobDetailApiView.as_view(), name="drawing-metadata-job-detail"),
]
