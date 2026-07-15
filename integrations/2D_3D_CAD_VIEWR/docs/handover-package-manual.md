# 納品パッケージ手順書

## 目的

この文書は、PDM 埋込向け 2D/3D viewer を相手先へ引き渡すときに、何をどの状態で渡すかを定義するための納品用マニュアルです。

## 標準の納品単位

標準は、リポジトリ直下の `handover_package/` を納品用の正本として渡します。内容は `ソース一式 + Docker 起動定義 + 設定例 + ライセンス文書 + 同梱文書` とし、`dist/` や仮想環境、内部運用文書は含めません。

### 渡す対象

- `backend/`
- `frontend/`
- `docs/viewer-specification.md`
- `docs/viewer-flow.md`
- `docs/code-map.md`
- `docs/handover-technology-summary.md` を原本にした `docs/technology-summary.md`
- `docs/handover-integration-manual.md` を原本にした `docs/integration-manual.md`
- `docs/handover-readme.md` を原本にした `README.md`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/licenses/`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `.dockerignore`
- `.env.example`
- `.gitignore`

### 渡さない対象

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/coverage/`
- `frontend/test/`
- `backend/db.sqlite3`
- `backend/media/`
- `backend/**/__pycache__/`
- `backend/**/*.pyc`
- `backend/tests/`
- `backend/pytest.ini`
- `frontend/*.tsbuildinfo`
- `frontend/src/test/`
- `frontend/src/**/*.test.ts`
- `frontend/src/**/*.test.tsx`
- `frontend/vite.config.js`
- `frontend/vite.config.d.ts`
- `frontend/vitest.config.js`
- `frontend/vitest.config.d.ts`
- `frontend/vitest.config.ts`
- `AGENTS.md`
- `tasklist.md`
- `docs/handover-package-manual.md`
- `docs/step-backend-replacement.md`
- `docs/tiff-handling-notes.md`
- `docs/3d-performance-notes.md`
- `docs/3d-section-cap-notes.md`
- `scripts/`
- `tests/`
- 一時生成物、ログ、キャッシュ

## handover パッケージの同期手順

handover パッケージは手作業で編集せず、リポジトリ直下の `scripts/sync_handover_package.ps1` で再生成します。同梱する `README.md` は社内用のリポジトリ直下 `README.md` ではなく `docs/handover-readme.md` を原本として出力し、`docs/technology-summary.md` と `docs/integration-manual.md` もそれぞれ handover 原本から生成します。

### 更新

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\scripts\sync_handover_package.ps1 -Mode update'
```

### 最新性確認

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; .\scripts\sync_handover_package.ps1 -Mode check'
```

## 納品前チェック

- `scripts/sync_handover_package.ps1 -Mode update` 実行後に `handover_package/` が再生成できる
- `scripts/sync_handover_package.ps1 -Mode check` が成功する
- `docker compose up --build` 相当の再現手順が README に記載されている
- 再現環境が `nginx + gunicorn`、開発環境が `Vite + Django runserver` として説明されている
- `docs/viewer-flow.md` が同梱されている
- `docs/code-map.md` が同梱されている
- バックエンド依存が `backend/requirements-base.txt` と `backend/requirements-step.txt` に揃っている
- フロント依存が `frontend/package.json` と `frontend/package-lock.json` に揃っている
- `.env.example` が最新の設定値を反映している
- `docs/technology-summary.md` が現行構成を反映している
- `docs/handover-readme.md` がそのまま同梱できる内容になっている
- `docs/handover-integration-manual.md` が組み込み手順として成立している
- `docs/handover-technology-summary.md` が構成説明として成立している
- `docs/THIRD_PARTY_NOTICES.md` と `docs/licenses/` が同梱されている
- `docs/viewer-specification.md` が現行実装と一致している
- 提出物に `backend/tests/` とフロントエンドのテストコードが含まれていない

## 納品時に伝える内容

### 推奨確認手順

- `.env.example` を `.env` にコピーする
- `docker compose up --build` で起動する
- `http://localhost:4173/drawing/{drawingId}` にアクセスする
- bootstrap が返ることを確認する
- 2D で PDF / JPEG / TIFF を確認する
- 3D で STL / STEP を確認する

### 設定ファイル

相手先には `.env.example` をベースに `.env` を作成してもらいます。特に以下を説明してください。

- `VIEWER_TIMEOUT_SECONDS`
- `VIEWER_MAX_DOWNLOAD_BYTES`
- `VIEWER_ARTIFACT_TTL_SECONDS`
- `VIEWER_ALLOWED_SCHEMES`
- `VIEWER_INTERNAL_URLS_ENABLED`
- `VIEWER_INTERNAL_HOST_ALLOWLIST`
- `VIEWER_INTERNAL_CIDR_ALLOWLIST`
- `VIEWER_STEP_ENABLED`
- `VIEWER_STEP_STL_TOLERANCE`
- `VIEWER_STEP_STL_ANGULAR_TOLERANCE`
- `VIEWER_LOCAL_FILE_ENABLED`
- `VIEWER_STORAGE_ROOT`
- `PDM_API_BASE_URL`
- `PDM_DRAWING_RESOLVE_PATH_TEMPLATE`
- `PDM_REQUEST_TIMEOUT_SECONDS`
- `DJANGO_SQLITE_PATH`
- `VITE_API_BASE_URL`
- `VITE_DEV_PROXY_TARGET`
- `VITE_LOCAL_FILE_ENABLED`

### 同梱文書

- `README.md`
- `docs/viewer-specification.md`
- `docs/viewer-flow.md`
- `docs/code-map.md`
- `docs/technology-summary.md`
- `docs/integration-manual.md`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/licenses/README.md`
