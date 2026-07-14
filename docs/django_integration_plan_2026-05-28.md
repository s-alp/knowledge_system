# Django統合計画

- 作成日: 2026-05-28
- 目的: ICAD 2D/3D 抽出、タグ・属性自動付与、管理画面を、Django ベースのナレッジシステムへどう組み込むかを具体化する。
- 前提:
  - ナレッジシステム本体のソースコードは共有されていない。
  - 実際の本体へ後で移植できるよう、Django モジュールとして独立性を高く設計する。
  - `2D_3D_CAD_VIEWR` は UI / viewer 導線の参照元として扱う。

## 1. 今回の再確認結果

### 1.1 確認対象

- 図面管理一覧: `http://210.165.3.139/web/drawing`
- 指定図面詳細: `http://210.165.3.139/web/drawing/6a311357-8edd-4501-9ad2-d806b10b58be`

### 1.2 事実として確認できたこと

- 両 URL とも到達自体はできる。
- ページタイトルは `ナレッジ`。
- 静的 HTML として取得できるのは SPA のシェルのみで、`div#root` と JS/CSS バンドル参照しか見えない。
- `manifest.json` 構文エラーと hydration 警告は確認できるが、図面詳細の DOM や実データ契約は HTML だけでは確認できない。

### 1.3 設計上の意味

- 本体の詳細実装には依存できないため、統合計画は以下の前提で作る。
  - Django の app 単位で自己完結する
  - API / service / task / model を分離する
  - 既存本体へ後差ししやすい薄い境界にする

### 1.4 2026-05-28 実装後の追加事実

- 同一 `.icd` から `2d` / `3d` の両抽出ができた。
- そのため、`drawing` 単位で `source_kind` を固定する前提は不適切だった。
- `RegisteredDrawing` は 1 ファイル 1 レコードとし、抽出モードは `job / snapshot` 単位で持つ構成へ切り替えた。
- Linux/Docker 側は制御プレーンのまま残し、Windows 側が ICAD 実行と抽出を担当する前提がより妥当になった。

## 2. 目標像

実装後の流れは以下を想定する。

1. 図面管理ページから 2D/3D 図面を登録する
2. Django が抽出ジョブを作成する
3. Django task が C# 抽出コアを呼ぶ
4. 生抽出 JSON を受け取り、Django service 層で正規化する
5. `canonical_attributes` と `derived_tags` を保存する
6. 管理ページで抽出結果を確認・補正する
7. viewer 詳細や RAG が保存済み属性を参照する

## 3. 推奨 app 構成

本体へ後で移植しやすいよう、Django 側は新規 app を分ける。

### 推奨 app 名

- `drawing_metadata`

### ディレクトリ構成案

```text
drawing_metadata/
  apps.py
  models.py
  admin.py
  urls.py
  api/
    serializers.py
    views.py
  services/
    extraction_runner.py
    normalization.py
    tag_builder.py
    persistence.py
    viewer_payload.py
    rag_payload.py
  tasks/
    extraction_tasks.py
  management/
    commands/
      reextract_drawing_metadata.py
  migrations/
```

### 2026-05-28 実装反映

- standalone backend を `backend/` 配下に作成済み
- project 名は `knowledge_system_backend`
- `apps/drawing_metadata/` に以下を配置済み
  - `api/serializers.py`
  - `api/views.py`
  - `services/extraction_runner.py`
  - `services/normalization.py`
  - `services/tag_builder.py`
  - `services/persistence.py`
  - `tasks/extraction_tasks.py`
  - `management/commands/process_drawing_metadata_jobs.py`
  - `templates/drawing_metadata/*.html`
- mode-aware 化も反映済み
  - `RegisteredDrawing` は source file のみ保持
  - `DrawingMetadataExtractionJob` は `extraction_mode`, `worker_name`, `lease_expires_at`, `retry_count` を保持
  - `DrawingMetadataSnapshot` は `drawing + extraction_mode` の unique 構成

## 4. Django 側の責務分担

### 4.1 Model 層

- 抽出ジョブ状態
- 生抽出 JSON
- 正規化属性
- 派生タグ
- 手動補正
- 実行履歴

### 4.2 Service 層

- C# 抽出器呼び出し
- JSON 読み込み
- 正規化
- タグ生成
- viewer/RAG 向け payload 生成

### 4.3 Task 層

- 長時間抽出処理の非同期実行
- OCR や STEP 重処理の切り分け
- 失敗時のリトライ

### 4.4 API 層

- 一覧取得
- 詳細取得
- 再抽出起動
- 補正保存
- 抽出ステータス確認

### 4.5 Admin / 管理 UI 層

- 抽出履歴確認
- 手動補正
- 強制再実行
- エラー確認

## 5. 同期/非同期の切り分け

### 同期に寄せてよい処理

- 図面登録レコード作成
- 抽出ジョブ発行
- 既存保存データの取得
- viewer / 一覧に返す軽量メタデータ取得

### 非同期に寄せるべき処理

- C# 抽出コア実行
- OCR
- STEP 重解析
- RAG 再インデックス

### 実装メモ

- 今回は Celery ではなく **DB-backed worker command** を採用した
- 理由:
  - 本体の既存ジョブ基盤が未共有
  - 先に request thread から重処理を外すことを優先
  - 後で Celery / Windows worker / 外部サービスへ差し替えやすいため
- さらに、ICAD を自動起動する場合は **その worker が起こした ICAD だけを終了対象にする** 方針を取る
- Windows 抽出 worker は `process_drawing_metadata_jobs --loop --mode all` でDB上の `DrawingMetadataExtractionJob` を claim し、Django backend は Linux/Docker 側に置ける
- worker は C# runner を `1ジョブ=1プロセス呼び出し` で実行し、`raw_extract -> canonical_attributes -> derived_tags` はDjango service層で処理する
- 抽出処理に入る直前に lease を `max(DRAWING_METADATA_JOB_LEASE_SECONDS, DRAWING_METADATA_EXTRACTOR_TIMEOUT_SECONDS + 60)` 秒へ延長する。これにより、長いICAD抽出中に別workerが同じjobを再claimする事故を避ける

### 避けるべきこと

- Django の request thread 内で C# 抽出を完走させる
- view から直接 OCR や STEP 重解析を回す
- model save hook 内で外部プロセス実行する

## 6. 図面登録から保存までの処理フロー

1. Django view / API が図面登録要求を受ける
2. 図面レコードを作成する
3. `extraction_mode=2d|3d` を持つ抽出ジョブレコードを `queued` で作成する
4. Windows worker が DB から job を claim する
5. worker が必要なら `icad.exe` を起動し、C# 抽出器を呼ぶ
6. 結果 JSON を受け取る
7. service 層が `raw_extract -> canonical_attributes -> derived_tags` を生成する
8. `drawing + extraction_mode` 単位の snapshot を保存する
9. 読み出し時に `compose_drawing_metadata(drawing_id)` で 2d/3d を統合する
10. 必要なら viewer / RAG 用の更新ジョブを続けて投入する

## 7. Django モデルの最小単位

### 7.1 `DrawingMetadataExtractionJob`

想定項目:

- `id`
- `drawing_id`
- `extraction_mode`
- `status`
- `worker_name`
- `lease_expires_at`
- `retry_count`
- `started_at`
- `finished_at`
- `elapsed_ms`
- `error_message`
- `warnings_json`
- `extractor_name`
- `extractor_version`

### 7.2 `DrawingMetadataSnapshot`

想定項目:

- `drawing_id`
- `extraction_mode`
- `latest_job_id`
- `raw_extract_json`
- `canonical_attributes_json`
- `derived_tags_json`
- `manual_overrides_json`
- `normalizer_version`
- `tag_rule_version`
- `updated_at`
- `updated_by`

### 7.3 `DrawingMetadataAuditLog`

想定項目:

- `drawing_id`
- `extraction_mode`
- `action_type`
- `before_json`
- `after_json`
- `executed_by`
- `executed_at`

## 8. API の最小単位

### 8.1 一覧系

- `GET /api/drawing-metadata/`
  - 図面一覧
  - タグ・属性フィルタ

### 8.2 詳細系

- `GET /api/drawing-metadata/{drawing_id}/`
  - `snapshotsByMode`
  - `composedMetadata`
  - mode ごとの抽出根拠
  - mode ごとの手動補正

### 8.3 ジョブ系

- `POST /api/drawing-metadata/{drawing_id}/extract`
  - `extractionMode` を受けて再抽出開始
- `GET /api/drawing-metadata/jobs/{job_id}/`
  - ジョブ状態確認

### 8.4 補正系

- `PATCH /api/drawing-metadata/{drawing_id}/overrides`
  - `extractionMode` を受けて手動補正保存

## 9. viewer との接続

### 9.1 接続方針

- 既存 viewer の bootstrap を重くしない。
- 詳細表示用に別 API を切る。

### 9.2 返したいもの

- `tags`
- `attribute_groups`
- `remarks`
- `extraction_status`
- `manual_override_summary`

### 9.3 `2D_3D_CAD_VIEWR` を参考にする箇所

- 基本情報カード
- 属性情報セクション
- 備考セクション
- 補助セクションの配置感

## 10. RAG との接続

### 10.1 事前フィルタ

- `customer_name`
- `project_name`
- `equipment_category`
- `document_kind`
- `source_format`

### 10.2 再ランキング

- `part_names`
- `maker_keywords`
- `dimension_values`
- `spec_tokens`
- `process_keywords`
- `weld_note_texts`

### 10.3 更新タイミング

- 抽出確定後
- 手動補正確定後

## 11. 移植前提での実装方針

本体が無い現状では、以下の方針が安全である。

- Django app として自己完結させる
- 既存本体の図面モデルとは疎結合にする
- `drawing_id` を主な接続キーにする
- UI も「参考実装」として分離し、本体統合時にテンプレート/React 側へ移しやすくする

## 12. 本体が後で来た時の差し替えポイント

- 既存図面モデルとの FK/OneToOne 接続
- 認可
- 既存図面一覧/詳細導線への埋め込み
- viewer detail API のルーティング
- RAG インデックス更新フック

## 13. 実装前に必要な確認

1. 本体 Django のバージョン
2. task queue の採用有無
3. 既存図面モデルの主キー形
4. 図面管理の既存 API 契約
5. viewer detail の既存 API 有無
6. RAG 更新の既存ジョブ基盤有無

## 14. 結論

- 本体ソースが無い現時点では、`Django app として後移植できる構成` を取るのが最も現実的である。
- 実装の中心は `C# 抽出コア + Django service/task + 管理 UI` の 3 層になる。
- 本来はナレッジシステム本体へ直接組み込むべきだが、現状では「後で本体へ差し込みやすい独立モジュール」を先に作るのが最適解である。
- Docker に載せやすいのは Django / worker 側であり、`sxnet` 抽出器は Windows 側へ分離する前提が妥当である。
