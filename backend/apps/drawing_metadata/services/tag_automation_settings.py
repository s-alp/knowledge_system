from __future__ import annotations

from django.conf import settings


def build_tag_automation_settings_payload() -> dict:
    api_key_configured = bool(getattr(settings, "GEMINI_API_KEY", ""))
    fallback_models = list(getattr(settings, "GEMINI_FALLBACK_MODELS", []) or [])
    return {
        "title": "タグ自動取得設定",
        "summary": "ICAD 2D/3D 抽出結果からタグ・属性候補を作るための運用設定です。",
        "runtimeRows": [
            {"label": "設定配置", "value": "システム設定 > タグ自動取得設定"},
            {"label": "LLM provider", "value": getattr(settings, "DRAWING_METADATA_LLM_PROVIDER", "") or "-"},
            {"label": "Gemini APIキー", "value": "設定済み" if api_key_configured else "未設定"},
            {"label": "主モデル", "value": getattr(settings, "GEMINI_MODEL", "") or "-"},
            {"label": "フォールバックモデル", "value": ", ".join(fallback_models) if fallback_models else "-"},
            {"label": "温度", "value": str(getattr(settings, "GEMINI_TEMPERATURE", "0.0"))},
            {"label": "タグルール版", "value": getattr(settings, "DRAWING_METADATA_TAG_RULE_VERSION", "") or "-"},
            {"label": "本番書き込み", "value": "行わない。創屋連携payloadの確認まで"},
        ],
        "operationRows": [
            {
                "area": "設定",
                "screen": "システム設定 > タグ自動取得設定",
                "role": "LLM、温度、タグルール、採用方針を管理する。",
                "writePolicy": "本番保存は創屋実装側。こちらは設定値とpayload仕様を渡す。",
            },
            {
                "area": "確認・再抽出・手直し",
                "screen": "図面管理 > タグ候補レビュー",
                "role": "2D/3D/パーツ付加情報の抽出結果、競合、対象別payloadを確認する。",
                "writePolicy": "ローカルDBの手動補正と再抽出ジョブだけを扱う。",
            },
            {
                "area": "表示",
                "screen": "図面詳細 / 製品・装置・ユニット詳細 / 部品詳細",
                "role": "確定候補をタグ・属性情報として表示し、紐づき候補も確認する。",
                "writePolicy": "本番ナレッジシステムの登録・変更・削除は行わない。",
            },
            {
                "area": "連携",
                "screen": "創屋連携payload",
                "role": "創屋が本番側に埋め込める形で対象、属性、タグ、根拠を出力する。",
                "writePolicy": "読み取り確認とfixture/API出力まで。",
            },
        ],
        "targetRows": [
            {
                "target": "図面",
                "displayPage": "図面詳細 / 図面管理",
                "storedAs": "tags / 属性情報",
                "reviewRoute": "図面管理 > タグ候補レビュー",
            },
            {
                "target": "製品・装置・ユニット",
                "displayPage": "製品・装置・ユニット詳細",
                "storedAs": "属性情報 / 関連情報",
                "reviewRoute": "図面管理 > 対象別payload確認",
            },
            {
                "target": "部品",
                "displayPage": "部品詳細",
                "storedAs": "属性情報 / 関連情報",
                "reviewRoute": "図面管理 > 対象別payload確認",
            },
            {
                "target": "プロジェクト",
                "displayPage": "プロジェクト詳細",
                "storedAs": "現時点は保留",
                "reviewRoute": "創屋の保存口確認後に再判定",
            },
        ],
        "ruleRows": [
            {
                "label": "2D",
                "value": "図枠、中央図面、寸法、注記、訂正内容、材質、表面処理、尺度、PRFX、ユニット番号",
            },
            {
                "label": "3D",
                "value": "図面名、図面サイズ候補、重量、材質、パーツツリー、パーツ付加情報、PRFX、ユニット番号",
            },
            {"label": "照合", "value": "2D/3D の同名属性は統合し、競合と診断差分を分けてレビューへ出す"},
            {"label": "AI採用", "value": "CAD内に存在する候補値の分類補助だけに使い、存在しない値は生成しない"},
            {"label": "図枠外", "value": "印刷枠内を自動採用優先。枠外・枠不明は証跡として残してレビュー対象"},
        ],
    }
