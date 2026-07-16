# 組み込み手順書

この文書は、PDM の図面詳細画面へ本 viewer を組み込むときの最小手順をまとめた手順書です。

## まず見る資料

- 概念と流れ: `docs/viewer-flow.md`
- API 契約: `docs/viewer-specification.md`
- 技術概要: `docs/technology-summary.md`

## 組み込みの基本方針

- PDM 側は `/drawing/{drawingId}` の導線を持ち、viewer へは `drawingId` だけを渡す
- viewer backend が PDM API を呼び、図面メタ情報と 2D/3D source URL を解決する
- viewer backend は受信した Cookie / Authorization を PDM API 呼び出しへ引き継ぐ
- frontend は drawingId 起点の詳細表示に徹し、基本情報は bootstrap、補助セクションは `metadata.knowledgeDetail` で構成する
- 補助セクションは ICAD抽出snapshot、訂正候補、監査ログ、タグ・属性連携候補から生成した実データ連携対象とする
- debug 用 URL / upload UI は既定で隠す

## Docker で確認する場合

### 再現環境

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose up --build'
```

Linux bash:

```bash
docker compose up --build
```

- `nginx + gunicorn` の再現確認向け構成です
- `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` は build 時点の `.env` 値で固定されます

### 開発向け確認

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose -f docker-compose.dev.yml up --build'
```

Linux bash:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- bind mount を使う `Vite + Django runserver` の開発確認構成です
- `VITE_DEV_PROXY_TARGET` はこの構成と `npm run dev` のときだけ使います
- この開発構成では URL 直入力とローカルファイル読み込みを最初から有効にします
- 受入確認や納品前確認は debug UI を含まない再現環境で実施してください

## バックエンド取り込み

### 取り込む対象

- `backend/apps/viewer/`
- `backend/viewer_backend/settings.py` の viewer / PDM 関連設定
- `backend/viewer_backend/urls.py` の viewer API ルーティング
- `backend/requirements-base.txt`
- STEP を使う場合は `backend/requirements-step.txt`

### 手順

1. Django プロジェクトへ `apps.viewer` を追加する
2. `api/v1/` 配下に viewer の URL を include する
3. `.env` に viewer / PDM 関連設定を追加する
4. migration を取り込み、`migrate` を実行する
5. `VIEWER_STORAGE_ROOT` の保存先を運用に合わせて設定する
6. Docker で DB を永続化する場合は `DJANGO_SQLITE_PATH` を volume 側へ向ける
7. `PDM_API_BASE_URL` と `PDM_DRAWING_RESOLVE_PATH_TEMPLATE` を PDM 環境に合わせる
8. frontend を別オリジンで配信する場合は `CORS_ALLOWED_ORIGINS` を設定する
9. 社内 URL を直接開く場合は `VIEWER_INTERNAL_URLS_ENABLED` と allowlist を設定する

## フロントエンド取り込み

### 取り込む対象

- `frontend/src/App.tsx`
- `frontend/src/features/viewer2d/`
- `frontend/src/features/viewer3d/`
- `frontend/src/shared/api/client.ts`
- `frontend/src/shared/drawingRoute.ts`
- `frontend/src/shared/hooks/useDrawingBootstrap.ts`
- `frontend/src/shared/types/viewer.ts`
- `frontend/src/shared/knowledge/drawingKnowledge.ts`
- `frontend/src/shared/components/DrawingEntryPanel.tsx`
- `frontend/src/shared/components/DrawingOverviewPanel.tsx`
- `frontend/src/shared/components/DrawingSupplementPanels.tsx`
- `frontend/src/shared/components/IconToolbarButton.tsx`
- `frontend/src/shared/components/MetadataBar.tsx`
- `frontend/src/shared/components/LicensePanel.tsx`
- debug UI も必要なら `ViewerSourcePanel.tsx` と `LocalFilePicker.tsx`

### 手順

1. 既存 React アプリへ features と shared を移植する
2. 既存ルーティングを `/drawing/:drawingId` 相当の詳細画面へ接続する
3. `VITE_API_BASE_URL` を受け取り側 API に合わせる
4. 必要なら CSS を既存デザインシステムに合わせて調整する
5. 基本情報カードと補助セクションを使う場合は `viewerBootstrap.metadata.knowledgeDetail` を `drawingKnowledge.ts` で正規化して渡す
6. 静的配布するときは `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` を build 時に確定させる
7. 開発画面の `DrawingEntryPanel` では `drawingId / URL` とローカルファイル起動の両方を提供する

## リバースプロキシ配下の想定

- API のベース URL は `VITE_API_BASE_URL` で吸収する
- Django 側の `ALLOWED_HOSTS` と reverse proxy 設定は受け取り側の運用に合わせる
- 2D/3D ソース配信 URL は backend absolute URL を返すため、外部公開 URL と整合するよう reverse proxy を構成する

## 公開 API

- `GET /api/v1/drawings/{drawingId}/bootstrap`
- `POST /api/v1/drawings/{drawingId}/viewer2d/open`
- `POST /api/v1/drawings/{drawingId}/viewer3d/open`
- `GET /api/v1/viewer2d/sessions/{id}/source`
- `GET /api/v1/viewer2d/sessions/{id}/pages/{page}/image`
- `GET /api/v1/viewer3d/jobs/{id}`
- `GET /api/v1/viewer3d/jobs/{id}/model`

開発・検証用 API として以下も残しています。

- `POST /api/v1/viewer2d/open`
- `POST /api/v1/viewer2d/upload`
- `POST /api/v1/viewer3d/open`
- `POST /api/v1/viewer3d/upload`

## PDM API 契約の前提

- viewer backend が呼ぶ PDM API は `drawingId` から次を解決できる必要があります
  - 図面メタ情報
  - 2D source URL
  - 3D source URL
- 受け入れ可能な返却形は次のどちらかです
  - `source_2d_url` / `source_3d_url` をトップレベルで返す
  - `drawing_file_versions` 相当の配列で `file_name` / `file_path` を返す
- `drawing_file_versions` 方式では、viewer backend が拡張子から 2D と 3D の候補を選びます
- そのため、`file_name` には実拡張子付きファイル名、`file_path` には viewer backend から取得可能な URL を入れてください
- デフォルトの解決先は `PDM_DRAWING_RESOLVE_PATH_TEMPLATE=/drawings/internals/{drawing_id}/`
- 実際の PDM API パスが異なる場合は env で差し替えます

## 社内 URL を直接開く場合

- `VIEWER_INTERNAL_URLS_ENABLED=true`
- `VIEWER_INTERNAL_HOST_ALLOWLIST` に許可ホスト名を設定する
- `VIEWER_INTERNAL_CIDR_ALLOWLIST` に許可 CIDR を設定する
- `.env.example` の allowlist はサンプル値なので、組み込み先環境向けに差し替える
- allowlist に一致しない private / loopback 宛ては拒否される

## 形式ごとの扱い

- TIFF はブラウザで直接デコードせず、backend でページごとに PNG 化して返す
- STL はそのまま表示する
- STEP は既定で backend で STL メッシュへ変換して表示する
- 断面キャップは閉じた STL メッシュのみ対象

## 受入確認項目

- `bootstrap` で図面情報と availability が返る
- 基本情報カードに bootstrap の内容が表示される
- 改訂履歴、関連情報、変更履歴、属性情報、備考が補助セクションとして表示される
- 2D がある図面で PDF / JPEG / TIFF が開ける
- 3D がある図面で STL / STEP / STP が開ける
- 2D の操作 UI で戻る/進む、拡大/縮小、リセット、左右回転が使える
- 3D の操作 UI で拡大/縮小、リセット、断面オン/オフ、輪郭強調 ON/OFF が使える
- TIFF でページ切り替えが動く
- STEP が STL 変換後に表示される
- 社内 URL を使う場合は allowlist 設定後に internal URL が開ける
- 許可外の internal URL は `security_error` で拒否される
- 開発モードでは debug UI が既定で表示される
- 本番相当の再現環境では debug UI は表示されない
- ヘッダーからライセンス文書への導線がある
