"""Django backendのurlsに関する入口またはデータ定義を提供する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def backend_status(_request):
    return JsonResponse(
        {
            "service": "knowledge-system-backend",
            "role": "api-only",
            "frontend": "http://127.0.0.1:5173/",
        }
    )


urlpatterns = [
    path("", backend_status, name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.drawing_metadata.api.urls")),
    path("internal/drawing-metadata/", include("apps.drawing_metadata.urls")),
]
