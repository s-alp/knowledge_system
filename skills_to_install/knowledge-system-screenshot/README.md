# knowledge-system-screenshot スキル

社内ナレッジシステム（PDM＋ナレッジ検索）の主要画面を、Cowork の bash 上で Playwright を使って自動キャプチャするスキルです。

## インストール

このフォルダ全体を、Cowork のスキルディレクトリにコピーしてください。

**コピー先（このユーザー環境）:**
```
C:\Users\s-iwata\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\e2639113-2d24-4c09-9ba7-065761fc450a\07067200-c91d-4b75-826b-4a00d91079e4\skills\knowledge-system-screenshot\
```

コピー後、新しい Cowork 会話を開始すると、利用可能スキル一覧に `knowledge-system-screenshot` が現れます。

## 初回セットアップ（インストール後1回だけ）

スキルインストール直後の Cowork 会話で、以下をご依頼ください：

> 「knowledge-system-screenshot スキルの初回セットアップをお願い」

Claude が以下を実行します：
1. `.env.example` をコピーして `.env` を作成
2. （`.env` の編集が必要な場合は提示）
3. `bash setup.sh` で Playwright + Chromium Headless Shell をインストール

セットアップで生成されるもの：
- `node_modules/` — Playwright 一式
- `browsers/` — Chromium Headless Shell バイナリ（約100MB）
- `screenshots/` — キャプチャ出力先（空）

## 通常の使い方

セットアップ後、いつでも以下をご依頼ください：

> 「ナレッジシステムの最新画面をキャプチャ」
> 「ナレッジの画面を取って」

Claude が `bash run.sh` を実行し、約30秒で7画面をキャプチャします。

## 取得対象画面

| # | URL（base からの相対） | ファイル名 | 内容 |
|---|----------------------|----------|------|
| 1 | `/` | `01_home.png` | ホーム（通知・お知らせ） |
| 2 | `/chat` | `02_ai_search.png` | AI検索（自然言語チャット） |
| 3 | `/drawing/similar_search` | `03_similar_search.png` | 類似検索（2D/3D・重みづけ） |
| 4 | `/drawing` | `04_drawings.png` | 図面一覧（実データ取込済） |
| 5 | `/product` | `05_products.png` | 製品・装置・ユニット一覧 |
| 6 | `/system_setting` | `06_workflow.png` | ワークフロー設定 |
| 7 | `/system_setting`（タブ切替） | `07_crawl.png` | クロール設定 |

追加対象は `grab_screenshots.js` の `pages` 配列に追加してください。

## ファイル構成

```
knowledge-system-screenshot/
├── SKILL.md              ← スキル定義（Cowork が読む）
├── README.md             ← このファイル
├── grab_screenshots.js   ← Playwright メインスクリプト
├── setup.sh              ← 初回インストール
├── run.sh                ← 通常実行
├── .env.example          ← 認証情報テンプレート
├── .env                  ← 実際の認証情報（自分で作成、Git 除外）
├── node_modules/         ← setup 後に作られる
├── browsers/             ← setup 後に作られる Chromium バイナリ
└── screenshots/          ← 出力 PNG
```

## セキュリティ

- `.env` は社内認証情報を含むため、Git 管理外（`.gitignore` 推奨）
- スクリプト本体には認証情報をハードコードしない設計
- ナレッジシステム URL は社内 LAN 限定の前提
