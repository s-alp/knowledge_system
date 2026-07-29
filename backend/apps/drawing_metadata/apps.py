"""Django backendのappsに関する入口またはデータ定義を提供する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
from django.apps import AppConfig


class DrawingMetadataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.drawing_metadata"
    verbose_name = "図面メタデータ"
