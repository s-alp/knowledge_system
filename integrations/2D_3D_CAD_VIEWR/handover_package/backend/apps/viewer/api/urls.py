"""Public API routes consumed by the React viewer."""

from django.urls import path

from apps.viewer.api.views import (
    DrawingBootstrapView,
    DrawingViewer2DOpenView,
    DrawingViewer3DOpenView,
    Viewer2DOpenView,
    Viewer2DPageImageView,
    Viewer2DSourceView,
    Viewer2DUploadView,
    Viewer3DJobView,
    Viewer3DModelView,
    Viewer3DOpenView,
    Viewer3DUploadView,
)

urlpatterns = [
    path("drawings/<uuid:drawing_id>/bootstrap", DrawingBootstrapView.as_view(), name="drawing-bootstrap"),
    path("drawings/<uuid:drawing_id>/viewer2d/open", DrawingViewer2DOpenView.as_view(), name="drawing-viewer2d-open"),
    path("drawings/<uuid:drawing_id>/viewer3d/open", DrawingViewer3DOpenView.as_view(), name="drawing-viewer3d-open"),
    # 2D は元ファイル URL と、TIFF 専用のページ画像 URL を分けて公開する。
    path("viewer2d/open", Viewer2DOpenView.as_view(), name="viewer2d-open"),
    path("viewer2d/upload", Viewer2DUploadView.as_view(), name="viewer2d-upload"),
    path("viewer2d/sessions/<uuid:session_id>/source", Viewer2DSourceView.as_view(), name="viewer2d-source"),
    path(
        "viewer2d/sessions/<uuid:session_id>/pages/<int:page_number>/image",
        Viewer2DPageImageView.as_view(),
        name="viewer2d-page-image",
    ),
    # 3D は job 状態取得と、ready 後のモデル配信を別エンドポイントに分ける。
    path("viewer3d/open", Viewer3DOpenView.as_view(), name="viewer3d-open"),
    path("viewer3d/upload", Viewer3DUploadView.as_view(), name="viewer3d-upload"),
    path("viewer3d/jobs/<uuid:job_id>", Viewer3DJobView.as_view(), name="viewer3d-job"),
    path("viewer3d/jobs/<uuid:job_id>/model", Viewer3DModelView.as_view(), name="viewer3d-model"),
]
