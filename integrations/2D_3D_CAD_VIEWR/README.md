# 2D/3D PDM Embedded Viewer

PDM の図面詳細画面へ埋め込むことを前提にした 2D/3D ビューアです。  
フロントエンドは `drawingId` を URL から受け取り、バックエンドは同一ログイン文脈で PDM API を呼んで図面メタ情報と 2D/3D の表示対象を解決します。2D は `PDF / JPEG / TIFF`、3D は `STL / STEP / STP` を対象にします。

## 概要

- 入口は `drawingId(UUID)` で、標準ルートは `/drawing/{drawingId}`
- backend は PDM API ブリッジ、形式判定、TIFF ページ画像化、3D 変換、成果物管理を担当する
- frontend は `bootstrap -> 2D/3D open -> 描画` の UI と状態表示を担当する
- TIFF はバックエンドでページごとに PNG 化して返す
- STEP は既定で `STEP -> STL` に変換して返す
- 2D の PDF 表示は、操作中の応答性を維持しつつ、操作後に高解像度描画へ差し替える
- URL 直貼り / ローカルファイル upload UI は開発・検証用で、開発環境でのみ表示する
- Docker Compose で再現環境と開発環境の両方を起動できる
- 図面viewerの補助セクションは `viewerBootstrap.metadata.knowledgeDetail` の実データを表示する
- 製品・装置・ユニット/部品の一覧・詳細はモックではなく、統合先のICAD 3D構成APIから実データを取得する
- ICADタグ・属性取得は専用レビュー画面で行い、システム設定には管理設定だけを置く

## リポジトリ構成

- `backend/`: Django/DRF API、PDM API 解決、TIFF ページ画像化、3D 変換、成果物管理
- `frontend/`: React/Vite ベースの PDM 埋込 viewer UI
- `docs/`: 仕様、データフロー、技術概要、運用メモ、納品/組み込み手順、ライセンス文書
- `scripts/`: テスト用補助スクリプトと handover パッケージ同期
- `handover_package/`: 外部共有向けの再生成パッケージ
- `tasklist.md`: 運用・保守フェーズのタスク管理

## 推奨起動方法

### 前提

1. `.env.example` を `.env` にコピーする
2. `docker compose up --build` では frontend の `VITE_*` は build 時に固定される
3. 再現確認用では `VITE_API_BASE_URL=/api/v1` を推奨する
4. `VITE_DEV_PROXY_TARGET` は `docker-compose.dev.yml` や `npm run dev` のときだけ backend URL に合わせる
5. PDM API の解決先は `PDM_API_BASE_URL` と `PDM_DRAWING_RESOLVE_PATH_TEMPLATE` で合わせる

### 再現確認環境

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose up --build'
```

Linux bash:

```bash
docker compose up --build
```

- 目的は導入前確認・ローカル再現用の確認環境
- フロントエンド: `http://localhost:4173`
- backend API: `http://localhost:8000/api/v1`
- frontend は `nginx`、backend は `gunicorn` で起動する
- SQLite と成果物は Docker volume `backend-runtime` に保存する
- `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` は build 時点の `.env` 値で固定される

### 開発向けホットリロード環境

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose -f docker-compose.dev.yml up --build'
```

Linux bash:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- 目的はソース変更を反映しながら動作確認する開発環境
- フロントエンド: `http://localhost:5173`
- backend API: `http://localhost:8000/api/v1`
- backend は Django `runserver`、frontend は Vite dev server で起動する
- Django と Vite はソース変更を即時反映する
- この開発環境では、URL 直入力とローカルファイル読み込みを最初から有効にする
- 納品前確認や受入確認は、debug UI を含まない再現確認環境で行うことを推奨する

## ローカル起動

### 必須環境

- Windows 11 または Linux
- Python 3.11
- Node.js 20 以上
- npm 10 以上

### バックエンド

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; python -m venv .venv'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\.venv\Scripts\python -m pip install -r backend\requirements-base.txt'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\.venv\Scripts\python -m pip install -r backend\requirements-step.txt'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\.venv\Scripts\python backend\manage.py migrate'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\.venv\Scripts\python backend\manage.py runserver'
```

Linux bash:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements-base.txt
./.venv/bin/python -m pip install -r backend/requirements-step.txt
./.venv/bin/python backend/manage.py migrate
./.venv/bin/python backend/manage.py runserver
```

### フロントエンド

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Set-Location -LiteralPath "frontend"; npm install'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Set-Location -LiteralPath "frontend"; npm run dev'
```

Linux bash:

```bash
cd frontend && npm install
cd frontend && npm run dev
```

## 検証コマンド

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\.venv\Scripts\python -m pytest backend\tests'
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Set-Location -LiteralPath "frontend"; npm run test'
```

Linux bash:

```bash
./.venv/bin/python -m pytest backend/tests
cd frontend && npm run test
```

## 主要な環境変数

### backend

- `VIEWER_TIMEOUT_SECONDS`
- `VIEWER_MAX_DOWNLOAD_BYTES`
- `VIEWER_ARTIFACT_TTL_SECONDS`
- `VIEWER_ALLOWED_SCHEMES`
- `VIEWER_INTERNAL_URLS_ENABLED`
- `VIEWER_INTERNAL_HOST_ALLOWLIST`
- `VIEWER_INTERNAL_CIDR_ALLOWLIST`
- `VIEWER_STEP_ENABLED`
- `VIEWER_LOCAL_FILE_ENABLED`
- `VIEWER_STORAGE_ROOT`
- `VIEWER_STEP_STL_TOLERANCE`
- `VIEWER_STEP_STL_ANGULAR_TOLERANCE`
- `PDM_API_BASE_URL`
- `PDM_DRAWING_RESOLVE_PATH_TEMPLATE`
- `PDM_REQUEST_TIMEOUT_SECONDS`

### frontend

- `VITE_API_BASE_URL`
- `VITE_DEV_PROXY_TARGET`
- `VITE_LOCAL_FILE_ENABLED`

## 公開 API

### PDM 埋込向け

- `GET /api/v1/drawings/{drawingId}/bootstrap`
- `POST /api/v1/drawings/{drawingId}/viewer2d/open`
- `POST /api/v1/drawings/{drawingId}/viewer3d/open`
- `GET /api/v1/viewer2d/sessions/{id}/source`
- `GET /api/v1/viewer2d/sessions/{id}/pages/{page}/image`
- `GET /api/v1/viewer3d/jobs/{id}`
- `GET /api/v1/viewer3d/jobs/{id}/model`

### 開発・検証用

- `POST /api/v1/viewer2d/open`
- `POST /api/v1/viewer2d/upload`
- `POST /api/v1/viewer3d/open`
- `POST /api/v1/viewer3d/upload`

## 表示方針

### TIFF

TIFF はブラウザで直接デコードせず、バックエンドでページ数を取得し、必要なページを PNG 化して返します。

### STEP

STEP は `CadQuery / OCP / OCCT` を利用し、既定では `STL` に変換して表示します。依存差し替え手順は `docs/step-backend-replacement.md` を参照してください。

### 断面キャップ

断面キャップは `閉じた STL メッシュ` のみ対応です。開いたメッシュではキャップを描画せず、断面内部が見える場合があります。

## 文書索引

- 仕様書: `docs/viewer-specification.md`
- データフロー: `docs/viewer-flow.md`
- 技術概要: `docs/technology-summary.md`
- コードマップ: `docs/code-map.md`
- 組み込み手順: `docs/integration-manual.md`
- 納品パッケージ手順: `docs/handover-package-manual.md`
- タスク一覧: `tasklist.md`

## ライセンス

- サードパーティ通知: `docs/THIRD_PARTY_NOTICES.md`
- LGPL 本文と OCCT 関連文書: `docs/licenses/`
- UI 上でもヘッダーのライセンス導線から確認できます
