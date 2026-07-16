# 2D/3D PDM Embedded Viewer コードマップ

## 目的

この文書は、主要ファイルの責務を短時間で把握するためのコードマップです。公開仕様は `docs/viewer-specification.md` を参照してください。

## バックエンド

### Docker / 実行

- `docker-compose.yml`
  - 提出向けの再現環境を起動する
- `docker-compose.dev.yml`
  - ホットリロード込みの開発環境を起動する
- `backend/Dockerfile`
  - Django と STEP 変換依存を含む backend image を組み立てる
- `backend/docker-entrypoint.sh`
  - migrate 実行後に runserver を起動する
- `frontend/Dockerfile`
  - フロントエンド build と nginx 配信イメージを組み立てる
- `frontend/nginx.conf`
  - SPA 配信のルーティングを定義する

### Django エントリポイント

- `backend/viewer_backend/settings.py`
  - viewer 関連の環境変数を定義する
- `backend/viewer_backend/urls.py`
  - `/api/v1/` 配下へ viewer API を接続する
- `backend/apps/viewer/api/urls.py`
  - drawingId bootstrap と 2D/3D の公開 API パスを定義する
- `backend/apps/viewer/api/views.py`
  - serializer、PDM resolver、viewer service をつなぐ薄い API 層
- `backend/apps/viewer/api/serializers.py`
  - bootstrap / session / job の API 入出力項目名を固定する

### 2D 処理

- `backend/apps/viewer/services/viewer2d.py`
  - 2D セッション生成、成果物 cleanup、TIFF ページ数反映
- `backend/apps/viewer/services/tiff_pages.py`
  - TIFF ページ数取得とページ PNG 化
- `backend/apps/viewer/services/filetypes.py`
  - 2D/3D の形式判定

### 3D 処理

- `backend/apps/viewer/services/viewer3d.py`
  - 3D ジョブ生成、キャッシュ、変換実行、状態更新
- `backend/apps/viewer/services/converters.py`
  - `ThreeDConversionBackend` 抽象と CadQuery/ocp 実装
- `backend/apps/viewer/services/runtime.py`
  - 実行時 backend の組み立て

### 共通基盤

- `backend/apps/viewer/services/pdm.py`
  - `drawingId -> metadata + 2D/3D source URL` の解決を担当する
- `backend/apps/viewer/services/fetchers.py`
  - URL 取得と制限チェック
- `backend/apps/viewer/services/storage.py`
  - 一時成果物の保存先とファイル操作
- `backend/apps/viewer/services/jobs.py`
  - 2D session / 3D job の永続化と状態更新
- `backend/apps/viewer/models.py`
  - Django model 定義
- `backend/apps/viewer/domain/types.py`
  - service 間で使う型定義
- `backend/apps/viewer/services/errors.py`
  - API まで伝播する独自例外

## フロントエンド

### 画面の入口

- `frontend/src/App.tsx`
  - drawingId の解析、bootstrap 読み込み、2D / 3D タブ切り替え、ライセンス導線表示、補助セクション配置
- `frontend/src/main.tsx`
  - React アプリの起動
- `frontend/src/shared/components/DrawingEntryPanel.tsx`
  - 開発画面の入口として `drawingId / URL` 入力とローカルファイル起動を提供する

### ICADタグ・属性と対象物

- `frontend/src/features/drawingMetadata/IcadExtractionReviewPage.tsx`
  - ICAD登録、2D/3D抽出、状態自動更新、条件付き再抽出、手直し、候補確定を担当する
- `frontend/src/features/knowledgeEntities/IcadEntityPages.tsx`
  - ICAD 3D構成由来の製品・装置・ユニット/部品の一覧と詳細を表示する
- `frontend/src/features/knowledgeEntities/useKnowledgeEntities.ts`
  - 対象物一覧/詳細APIの読込状態を管理する
- `frontend/src/features/knowledgeSettings/TagAutomationSettingsPage.tsx`
  - AI/API/抽出対象/採用ルールを実設定APIから表示する
- `../backend/apps/drawing_metadata/services/icad_entities.py`
  - 子ノードありをアセンブリ/サブアセンブリ、子ノードなしを末端部品として分類し、属性・タグ・根拠を組み立てる
- `../backend/apps/drawing_metadata/api/views.py`
  - ICAD登録、抽出ジョブ、レビュー、対象物、設定のAPI入口を提供する

`../backend` は統合先の `knowledge_system/backend` を表す。提出viewer単体の `backend/apps/viewer` と混同しない。

### 2D viewer

- `frontend/src/features/viewer2d/pages/Viewer2DPage.tsx`
  - 2D 画面の状態管理、ページ状態、API 呼び出し
- `frontend/src/features/viewer2d/components/Viewer2DPreviewPane.tsx`
  - 2D プレビュー専用の viewport state、toolbar、canvas と stage サイズ連携を閉じ込める
- `frontend/src/features/viewer2d/hooks/useViewer2DDocument.ts`
  - 2D 表示対象の読み込み制御
- `frontend/src/features/viewer2d/components/TwoDViewerCanvas.tsx`
  - pointer 入力、アンカー付きズーム、操作中の高解像度差し替え保留を担う 2D 描画本体
- `frontend/src/features/viewer2d/controls/Viewer2DToolbar.tsx`
  - Tabler Icons ベースの 2D 操作 UI
- `frontend/src/features/viewer2d/adapters/`
  - `pdf` / `jpeg` / `tiff` の描画差分を吸収する
- `frontend/src/features/viewer2d/state/viewer2dState.ts`
  - 2D の pan / rotate / zoomAt を含む viewport 状態遷移を整理する

### 3D viewer

- `frontend/src/features/viewer3d/pages/Viewer3DPage.tsx`
  - 3D 画面の状態管理、job polling、断面 UI、プレビュー右上の操作 UI 配置
- `frontend/src/features/viewer3d/components/ThreeDViewerScene.tsx`
  - Three.js ベースの 3D 描画本体
- `frontend/src/features/viewer3d/controls/Viewer3DToolbar.tsx`
  - 拡大/縮小、断面、輪郭強調、リセットをまとめた 3D 操作 UI
- `frontend/src/features/viewer3d/hooks/useViewer3DJob.ts`
  - 3D job の取得制御
- `frontend/src/features/viewer3d/utils/meshAnalysis.ts`
  - 断面キャップ可否の補助判定
- `frontend/src/features/viewer3d/state/viewer3dState.ts`
  - 3D の状態遷移を整理する

### shared

- `frontend/src/shared/api/client.ts`
  - drawing bootstrap と viewer API の request helper を集約する
- `frontend/src/shared/drawingRoute.ts`
  - pathname / query から drawingId を抽出する
- `frontend/src/shared/hooks/useDrawingBootstrap.ts`
  - drawing bootstrap の取得制御を行う
- `frontend/src/shared/hooks/useViewerSourceLoader.ts`
  - 2D / 3D 共通の debug 用 URL / upload 開始処理をまとめる
- `frontend/src/shared/components/ViewerSourcePanel.tsx`
  - 2D / 3D 共通の debug 入力 UI をまとめる
- `frontend/src/shared/types/viewer.ts`
  - API レスポンス型を定義する
- `frontend/src/shared/types/loading.ts`
  - ローディング表示の型を定義する
- `frontend/src/shared/loadingMessages.ts`
  - 表示フェーズごとの文言を定義する
- `frontend/src/shared/components/MetadataBar.tsx`
  - 共通メタデータ表示
- `frontend/src/shared/components/DrawingOverviewPanel.tsx`
  - 基本情報、属性情報、備考、メタ情報の表示骨格
- `frontend/src/shared/components/DrawingSupplementPanels.tsx`
  - 改訂履歴、関連情報、変更履歴の補助セクションと空状態表示
- `frontend/src/shared/components/IconToolbarButton.tsx`
  - Tabler Icons を載せる共通アイコンボタン
- `frontend/src/shared/components/LocalFilePicker.tsx`
  - ローカルファイル選択 UI
- `frontend/src/shared/components/LoadingNotice.tsx`
  - ローディング状態表示
- `frontend/src/shared/components/LicensePanel.tsx`
  - ヘッダー上の折りたたみ式ライセンス導線 UI
- `frontend/src/shared/knowledge/drawingKnowledge.ts`
  - `viewerBootstrap.metadata.knowledgeDetail` を補助セクション表示用に正規化する
- `frontend/src/shared/env.ts`
  - フラグ系環境変数の解釈

## テスト

- `backend/tests/`
  - backend service/API の結線と制約を確認する
- `frontend/src/**/*.test.ts*`
  - state、toolbar、utility、env の挙動を確認する

## 文書との対応

- API 契約を変えたら `docs/viewer-specification.md` を更新する
- 画面/API の流れを変えたら `docs/viewer-flow.md` を更新する
- ファイル責務や配置を変えたらこの文書を更新する
- 納品や組み込み前提を変えたら `docs/integration-manual.md` と `docs/handover-package-manual.md` を更新する
