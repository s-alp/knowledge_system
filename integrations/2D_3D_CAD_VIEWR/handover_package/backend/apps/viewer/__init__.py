"""2D/3Dビューワーバックエンドの__init__を担当し、API層と変換・保存処理を分離する。

初めて読むときは、公開されている入口から呼び出し先を順に追う。
外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。
"""
default_app_config = "apps.viewer.apps.ViewerConfig"
