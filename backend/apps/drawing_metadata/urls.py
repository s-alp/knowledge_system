from django.urls import path

from apps.drawing_metadata import views


urlpatterns = [
    path("", views.RegistrationListPageView.as_view(), name="drawing-metadata-list-page"),
    path("<uuid:drawing_id>/", views.RegistrationDetailPageView.as_view(), name="drawing-metadata-detail-page"),
    path("jobs/<uuid:job_id>/", views.JobDetailPageView.as_view(), name="drawing-metadata-job-page"),
]
