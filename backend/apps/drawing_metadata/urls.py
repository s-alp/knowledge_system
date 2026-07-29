"""Django backendのurlsに関する入口またはデータ定義を提供する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from django.urls import path

from apps.drawing_metadata import views


urlpatterns = [
    path("handoff/", views.HandoffDashboardPageView.as_view(), name="drawing-metadata-handoff-page"),
    path(
        "system/tag-automation/",
        views.TagAutomationSettingsPageView.as_view(),
        name="drawing-metadata-tag-automation-settings-page",
    ),
    path("", views.RegistrationListPageView.as_view(), name="drawing-metadata-list-page"),
    path("<uuid:drawing_id>/tags/", views.TagReviewPageView.as_view(), name="drawing-metadata-tag-review-page"),
    path("<uuid:drawing_id>/product-unit/", views.ProductUnitTagPageView.as_view(), name="drawing-metadata-product-unit-page"),
    path("<uuid:drawing_id>/parts/", views.PartTagPageView.as_view(), name="drawing-metadata-part-page"),
    path("<uuid:drawing_id>/", views.RegistrationDetailPageView.as_view(), name="drawing-metadata-detail-page"),
    path("jobs/<uuid:job_id>/", views.JobDetailPageView.as_view(), name="drawing-metadata-job-page"),
]
