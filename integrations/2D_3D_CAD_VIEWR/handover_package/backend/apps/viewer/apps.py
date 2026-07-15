from django.apps import AppConfig


class ViewerConfig(AppConfig):
    # Django へ viewer app の登録名を知らせる最小設定。
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.viewer"
