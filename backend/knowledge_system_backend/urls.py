from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.drawing_metadata.api.urls")),
    path("drawing-metadata/", include("apps.drawing_metadata.urls")),
]
