# 技術概要

この文書は、本システムの構成を短時間で把握するための概要資料です。

## 対象システム

- PDM 埋込向け 2D/3D ビューア
- 2D は `PDF / JPEG / TIFF`
- 3D は `STL / STEP`

## 実行形態

- 推奨再現環境: `docker compose up --build`
- 開発向け: `docker compose -f docker-compose.dev.yml up --build`
- ローカル起動: Python / Node.js を直接導入して起動可能

## 言語

- バックエンド: `Python 3.11`
- フロントエンド: `TypeScript`

## フレームワーク / ランタイム

- バックエンド: `Django`, `Django REST framework`
- フロントエンド: `React`, `Vite`
- 再現環境 backend 配信: `gunicorn`
- 再現環境フロント配信: `nginx`

## 主要モジュール

### バックエンド

- `django`
- `djangorestframework`
- `django-cors-headers`
- `pillow`
- `requests`
- `python-dotenv`

### STEP 変換

- `cadquery`
- `ocp`
- `OCCT`

### フロントエンド

- `react`
- `react-dom`
- `three`
- `@react-three/fiber`
- `@react-three/drei`
- `pdfjs-dist`
- `utif`

## DB / 保存

- 開発時 DB は `SQLite`
- Docker では `DJANGO_SQLITE_PATH` と `VIEWER_STORAGE_ROOT` を volume 側へ向けて永続化する
- 一時成果物はバックエンド側の保存領域で管理する
- 再現環境の frontend 設定値は `VITE_*` を build 時に確定する

## 処理方式

- フロントエンドは `/drawing/{drawingId}` から drawingId を解析して起動する
- バックエンドは PDM API ブリッジ、形式判定、変換、成果物管理を担当する
- バックエンドは受信した Cookie / Authorization を PDM API 呼び出しへ引き継ぐ
- フロントエンドは bootstrap 読み込み、ナレッジ風詳細 UI の構成、状態管理、操作 UI を担当する
- API は Django/DRF ベースの REST API で公開する
- TIFF はバックエンドでページごとに PNG 化して返す
- STL はそのまま表示する
- STEP は既定で STL に変換してから表示する
- 断面キャップは閉じた STL メッシュを対象とする
- 改訂履歴、関連情報、変更履歴、属性情報、備考は `viewerBootstrap.metadata.knowledgeDetail` の実データで構成している

## 参考資料

- 仕様書: `docs/viewer-specification.md`
- データフロー: `docs/viewer-flow.md`
- 組み込み手順: `docs/integration-manual.md`

## ライセンス上の注意

- STEP 変換では `CadQuery / OCP / OCCT` を使用する
- 配布時は `docs/THIRD_PARTY_NOTICES.md` と `docs/licenses/` の同梱を前提とする
- UI 上でもヘッダーのライセンス導線からライセンス情報へアクセスできる
