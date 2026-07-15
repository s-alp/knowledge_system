# 組み込み手順書

## 目的

この文書は、受け取り側が PDM の図面詳細画面へ本 viewer を組み込むときの最小手順をまとめたものです。

## まず確認する文書

- 概要把握: `docs/viewer-flow.md`
- API 契約: `docs/viewer-specification.md`
- 技術概要: `docs/technology-summary.md`

## 組み込みの基本方針

この viewer は `backend API` と `frontend UI` を分離しています。PDM 側は `/drawing/{drawingId}` の導線だけを持ち、viewer backend が PDM API を呼んで図面情報を解決する前提です。frontend は bootstrap の基本情報を詳細画面へ表示し、不足する補助セクションは mock detail で構成します。補助セクションは見た目合わせ用のモックであり、実データ連携の対象外です。

## Docker でそのまま使う場合

### 再現環境

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose up --build'
```

Linux bash:

```bash
docker compose up --build
```

- `nginx + gunicorn` の提出向け・ローカル再現用構成です
- `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` は build 時点の `.env` 値で固定されます

### 開発向け

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose -f docker-compose.dev.yml up --build'
```

Linux bash:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- bind mount を使う `Vite + Django runserver` の開発構成です
- `VITE_DEV_PROXY_TARGET` はこの構成と `npm run dev` のときだけ使います
- この開発構成では URL 直入力とローカルファイル読み込みを最初から有効にします
- 受入確認や納品前確認は、debug UI を含まない再現環境で実施することを推奨します

### 補足

- バックエンドは `8000`
- 提出向けフロントは `4173`
- 開発向けフロントは `5173`
- SQLite と成果物は backend volume へ保存する

## バックエンド取り込み

### 取り込む対象

- `backend/apps/viewer/`
- `backend/viewer_backend/settings.py` の viewer / PDM 関連設定値
- `backend/viewer_backend/urls.py` の API ルーティング
- `backend/requirements-base.txt`
- STEP を使う場合は `backend/requirements-step.txt`

### 組み込み手順

1. Django プロジェクトへ `apps.viewer` を追加する
2. `api/v1/` 配下に viewer の URL を include する
3. `.env` に viewer / PDM 設定を追加する
4. migration を取り込んで `migrate` を実行する
5. `VIEWER_STORAGE_ROOT` の保存先を既存運用に合わせる
6. Docker で DB を永続化する場合は `DJANGO_SQLITE_PATH` を volume 側へ向ける
7. フロントを別オリジンで配信する場合は `CORS_ALLOWED_ORIGINS` を設定する
8. `PDM_API_BASE_URL` と `PDM_DRAWING_RESOLVE_PATH_TEMPLATE` を相手先環境へ合わせる
9. 補助セクションはモック表示であることを受け取り側へ明示する
10. 社内 URL を直接開く場合は internal URL allowlist を設定する

### API 接続

公開 API は以下を前提にしてください。

- `GET /api/v1/drawings/{drawingId}/bootstrap`
- `POST /api/v1/drawings/{drawingId}/viewer2d/open`
- `POST /api/v1/drawings/{drawingId}/viewer3d/open`
- `POST /api/v1/viewer2d/open`
- `POST /api/v1/viewer2d/upload`
- `GET /api/v1/viewer2d/sessions/{id}/source`
- `GET /api/v1/viewer2d/sessions/{id}/pages/{page}/image`
- `POST /api/v1/viewer3d/open`
- `POST /api/v1/viewer3d/upload`
- `GET /api/v1/viewer3d/jobs/{id}`
- `GET /api/v1/viewer3d/jobs/{id}/model`

前者 3 本が本番用、後者 4 本は開発・検証用です。詳細なレスポンス項目は `docs/viewer-specification.md` を参照してください。

## フロントエンド取り込み

### 取り込む対象

- `frontend/src/features/viewer2d/`
- `frontend/src/features/viewer3d/`
- `frontend/src/shared/api/client.ts`
- `frontend/src/shared/drawingRoute.ts`
- `frontend/src/shared/hooks/useDrawingBootstrap.ts`
- `frontend/src/shared/types/viewer.ts`
- `frontend/src/shared/mock/drawingKnowledge.ts`
- `frontend/src/shared/components/DrawingEntryPanel.tsx`
- `frontend/src/shared/components/DrawingOverviewPanel.tsx`
- `frontend/src/shared/components/DrawingSupplementPanels.tsx`
- `frontend/src/shared/components/IconToolbarButton.tsx`
- `frontend/src/shared/components/MetadataBar.tsx`
- `frontend/src/shared/components/LicensePanel.tsx`

### 組み込み手順

1. 既存 React アプリへ features と shared を移植する
2. `VITE_API_BASE_URL` を受け取り側 API に合わせる
3. `/drawing/:drawingId` 相当の詳細画面へ viewer を接続する
4. CSS を既存デザインシステムに合わせて必要なら置き換える
5. 基本情報カードと補助セクションを使う場合は `drawingKnowledge.ts` の mock detail を流用する
6. 開発画面の `DrawingEntryPanel` では `drawingId / URL` とローカルファイル起動の両方を提供する
7. 静的配布するときは `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` を build 時に確定させる
8. 開発モードでは debug UI は既定で表示される

## リバースプロキシ配下の想定

- API のベース URL は `VITE_API_BASE_URL` で吸収する
- Django 側の `ALLOWED_HOSTS` と reverse proxy 設定は受け取り側の運用に合わせる
- 3D/2D ソース配信 URL はバックエンド absolute URL を返すため、外部公開 URL と整合するよう reverse proxy を構成する

## Docker確認項目

- 再現環境は `http://localhost:4173`、開発環境は `http://localhost:5173` で開ける
- 再現環境の backend は `gunicorn`、開発環境の backend は `runserver` で起動する
- `.env` の `VITE_LOCAL_FILE_ENABLED` を変更した場合、再現環境では再 build 後の UI と一致する
- 開発環境では URL 直入力とローカルファイル読み込みが最初から表示される
- 開発環境では `drawingId / URL` 入力とローカルファイル起動が同じ入口に並ぶ
- 再現環境では debug UI が表示されない

## 社内 URL を直接開く場合

- `VIEWER_INTERNAL_URLS_ENABLED=true`
- `VIEWER_INTERNAL_HOST_ALLOWLIST` に許可ホスト名を設定する
- `VIEWER_INTERNAL_CIDR_ALLOWLIST` に許可 CIDR を設定する
- `.env.example` の allowlist はサンプル値なので、必ず組み込み先環境向けに差し替える
- allowlist に一致しない private / loopback 宛ては拒否される

## 形式ごとの扱い

- TIFF はブラウザで直接デコードせず、バックエンドでページごとに PNG 化して返す
- STL はそのまま表示する
- STEP は既定でバックエンドで STL メッシュへ変換して表示する
- 断面キャップは閉じた STL メッシュのみ対象

## 受け取り後の確認項目

- `bootstrap` で図面メタ情報と availability が返る
- 基本情報カードに bootstrap の内容が表示される
- 改訂履歴、関連情報、変更履歴、属性情報、備考が補助セクションとして表示される
- 2D で PDF/JPEG/TIFF が開ける
- 3D で STL/STEP/STP が開ける
- 2D の操作 UI で戻る/進む、拡大/縮小、リセット、左右回転が使える
- 3D の操作 UI で拡大/縮小、リセット、断面オン/オフ、輪郭強調 ON/OFF が使える
- STEP が STL 変換後に表示される
- TIFF 複数ページで page image が切り替わる
- 社内 URL を使う場合は allowlist 設定後に internal URL が開ける
- 許可外の internal URL は `security_error` で拒否される
- 断面、ズーム、パン、リセットが動作する
- ヘッダーからライセンス文書への導線がある
