# 2D/3D PDM Embedded Viewer 利用ガイド

このパッケージは、PDM の図面詳細画面へ組み込む 2D/3D viewer を確認・導入するための一式です。backend は同一ログイン文脈で PDM API を呼び、frontend は `drawingId` から起動して 2D/3D 表示へ接続します。

## 概要

- 入口は `drawingId` で、標準ルートは `/drawing/{drawingId}`
- 2D は `PDF / JPEG / TIFF` に対応
- 3D は `STL / STEP / STP` に対応
- backend は `Django / Django REST framework`
- frontend は `React / TypeScript / Vite`
- STEP は既定で backend 側で `STL` に変換して表示
- PDM 側の複雑な実装を避け、viewer backend が PDM API を呼んで図面情報を解決する
- frontend は既存ナレッジ画面に寄せた図面詳細 UI を持ち、基本情報は bootstrap、補助セクションは mock detail で構成する
- 補助セクションの mock detail は見た目合わせ用であり、実データ連携対象外
- 社内 URL の直接参照は allowlist 設定時のみ有効にできる
- URL 直入力 / ローカルファイル読み込み UI は開発・検証用で、本番ビルドでは既定で無効

## 最初に確認してください

1. `README.md`
2. `docs/viewer-flow.md`
3. `docs/code-map.md`
4. `docs/integration-manual.md`
5. `docs/viewer-specification.md`

## 推奨起動方法

### 再現環境

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose up --build'
```

Linux bash:

```bash
docker compose up --build
```

- 利用環境での再現確認用として `nginx + gunicorn` で起動します
- frontend は `http://localhost:4173`
- viewer が使う API は同一 URL 配下の `/api/v1`
- frontend の `VITE_API_BASE_URL` と `VITE_LOCAL_FILE_ENABLED` は build 時点の `.env` 値で固定されます

### 任意: 開発向け確認

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '$PSDefaultParameterValues["*:Encoding"]="utf8"; [Console]::OutputEncoding=[System.Text.Encoding]::UTF8; docker compose -f docker-compose.dev.yml up --build'
```

Linux bash:

```bash
docker compose -f docker-compose.dev.yml up --build
```

- `Vite + Django runserver` の開発確認用です
- `VITE_DEV_PROXY_TARGET` はこの構成の `/api` 中継にだけ使います
- この開発構成では URL 直入力とローカルファイル読み込みを最初から有効にします
- 受入確認や納品前確認は debug UI を含まない再現環境で行うことを推奨します

## 受入確認手順

1. `.env.example` を `.env` にコピーする
2. `PDM_API_BASE_URL` と `PDM_DRAWING_RESOLVE_PATH_TEMPLATE` を利用環境に合わせる
3. `docker compose up --build` で backend と frontend を起動する
4. `http://localhost:4173/drawing/{drawingId}` を開く
5. bootstrap で図面メタ情報が表示されることを確認する
6. 改訂履歴、関連情報、変更履歴、属性情報、備考が表示されることを確認する
7. 2D がある図面で PDF / JPEG / TIFF を確認する
8. 3D がある図面で STL / STEP / STP を確認する
9. TIFF でページ切り替えが動くことを確認する
10. 3D でズーム、パン、リセット、断面が動くことを確認する
11. 開発構成では URL 直入力とローカルファイル読み込みが既定で表示されることを確認する

## 主な環境変数

- `DJANGO_ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `DJANGO_SQLITE_PATH`
- `VIEWER_ALLOWED_SCHEMES`
- `VIEWER_INTERNAL_URLS_ENABLED`
- `VIEWER_INTERNAL_HOST_ALLOWLIST`
- `VIEWER_INTERNAL_CIDR_ALLOWLIST`
- `PDM_API_BASE_URL`
- `PDM_DRAWING_RESOLVE_PATH_TEMPLATE`
- `PDM_REQUEST_TIMEOUT_SECONDS`
- `VIEWER_TIMEOUT_SECONDS`
- `VIEWER_MAX_DOWNLOAD_BYTES`
- `VIEWER_ARTIFACT_TTL_SECONDS`
- `VIEWER_STEP_ENABLED`
- `VIEWER_STEP_STL_TOLERANCE`
- `VIEWER_STEP_STL_ANGULAR_TOLERANCE`
- `VIEWER_LOCAL_FILE_ENABLED`
- `VIEWER_STORAGE_ROOT`
- `VITE_API_BASE_URL`
- `VITE_DEV_PROXY_TARGET`
- `VITE_LOCAL_FILE_ENABLED`

## 重要な注意

- 本番の viewer は `drawingId` 起動前提です
- backend は受信した Cookie / Authorization を PDM API 呼び出しへ引き継ぎます
- PDM API は `drawingId -> metadata + 2D/3D source URL` を返せる必要があります
- PDM API の返却形は、少なくとも次のどちらかを満たす必要があります
  - `source_2d_url` と `source_3d_url` を返す
  - `drawing_file_versions` 相当の配列で `file_name` と `file_path` を返す
- viewer backend は上記の情報から 2D/3D の表示対象を判定します
- ローカルファイル upload を使う場合は backend の `VIEWER_LOCAL_FILE_ENABLED` と frontend の `VITE_LOCAL_FILE_ENABLED` を両方有効にします
- 社内 URL を直接開く場合は `VIEWER_INTERNAL_URLS_ENABLED=true` と allowlist 設定が必要です
- allowlist に一致しない private / loopback 宛ては拒否されます
- ローカルファイル upload と URL 直入力は本番ビルドでは既定で無効です
- 開発構成では URL 直入力とローカルファイル読み込みを既定で有効にします
- `docker compose up --build` では frontend の `VITE_*` は build 時に固定されます

## 参照文書

- 仕様書: `docs/viewer-specification.md`
- データフロー: `docs/viewer-flow.md`
- コードマップ: `docs/code-map.md`
- 技術概要: `docs/technology-summary.md`
- 組み込み手順: `docs/integration-manual.md`
- サードパーティ通知: `docs/THIRD_PARTY_NOTICES.md`
- ライセンス文書: `docs/licenses/`
