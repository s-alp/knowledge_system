# tasklist

## 別会話で再開する人向け

### 最初に読む資料

1. `C:\Users\s-iwata\Desktop\knowledge_system\AGENTS.md`
2. `C:\Users\s-iwata\Desktop\knowledge_system\README.md`
3. `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_implementation_backlog_2026-05-26.md`
4. `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
5. `C:\Users\s-iwata\Desktop\knowledge_system\docs\extraction_result_schema_2026-05-28.md`
6. `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_extraction_poc_setup_2026-05-28.md`

### 現在の前提

- 同一 `.icd` を `2d` / `3d` の両 mode で抽出する前提
- Linux / Docker 側は制御プレーン
- Windows 側は `sxnet.dll` / `icad.exe` / `net48` runner を持つ抽出 worker
- `RegisteredDrawing` は 1 ファイル 1 レコード
- mode は `DrawingMetadataExtractionJob.extraction_mode` / `DrawingMetadataSnapshot.extraction_mode` で扱う
- ICAD 自動起動は可能だが、worker が起動した ICAD だけ終了対象にする
- 実抽出済みサンプル:
  - `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\9NK452WX90-00-LINER-A3-3D-01.json`
  - `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\9NK452WX90-00-LINER-A3-2D-01.json`
  - `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\9NK452RS60-03-CASSETTE-A0-3D-01.json`

## 完了済み

- [x] RAG 精度検証用の整理資料を作成
- [x] ICAD タグ・属性の調査結果を整理
- [x] タグ・属性の設計計画を作成
- [x] 実装引継ぎバックログを作成
- [x] C# / Django(Python) 分担アーキテクチャ案を作成
- [x] Django 統合計画を作成
- [x] 抽出結果スキーマ定義案を作成
- [x] タグ・属性管理 UI 計画を作成
- [x] HTML 要約報告を作成
- [x] standalone Django backend を作成
- [x] `drawing_metadata` app の API / service / task / template を実装
- [x] `net48` 抽出 CLI の PoC 骨格を作成
- [x] `SxFileModel.open(true)` 起点の 3D 抽出経路を実装
- [x] 2D geometry mapping の雛形を実装
- [x] Docker 化しやすい backend / worker 構成を追加
- [x] 同一 `.icd` を `2d` / `3d` mode で抽出できることを確認
- [x] `source_kind` を drawing から job / snapshot 単位へ移行
- [x] Windows worker 前提の mode-aware API / snapshot 構成へ更新
- [x] ICAD auto-start / auto-shutdown オプションを追加

## 次に着手する

- [ ] `SxGeomSpline2D` を raw_extract へ取り込む
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\extraction_result_schema_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_extraction_poc_setup_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxEntSeg.getGeomList.html`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Contracts\Models.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\GeometryMapper.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\tests\IcadExtraction.SxNet.Tests\GeometryMapperTests.cs`
- [ ] symbol / hatch / cutline 系の 2D geometry 対応を追加
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxEntSeg.getGeomList.html`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\extraction_result_schema_2026-05-28.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\GeometryMapper.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\ReflectionHelpers.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\tests\IcadExtraction.SxNet.Tests\GeometryMapperTests.cs`
- [ ] Windows 抽出 worker と Linux/Docker backend の接続方式を確定
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\README.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_csharp_python_architecture_2026-05-27.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_extraction_poc_setup_2026-05-28.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\management\commands\process_drawing_metadata_jobs.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\tasks\extraction_tasks.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docker-compose.backend.yml`
- [ ] worker lease / heartbeat の強化
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\README.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\models.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\tasks\extraction_tasks.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\tests\test_worker_claim.py`
- [ ] viewer detail API 契約へ接続
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\tag_attribute_management_ui_plan_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR\docs\viewer-specification.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\services\composition.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\api\serializers.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\api\views.py`
- [ ] RAG 更新ジョブとの連携を具体化
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\extraction_result_schema_2026-05-28.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_implementation_backlog_2026-05-26.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\services\composition.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\services\tag_builder.py`
    - `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\api\views.py`

## 保留中の確認事項

- [ ] ナレッジシステム本体 Django のバージョン確認
- [ ] 図面管理の既存保存先仕様確認
- [ ] viewer detail の既存 API 契約確認
- [ ] RAG 更新ジョブの既存基盤確認
- [ ] `sxnet.dll` の正式配置・参照条件確認

## 補足

- `backend/` / `src/` / `tests/` の差分が大きいので、別会話で再開するときは最初に `git status` を見ること
- GUI は最小の Django 管理導線があり、`http://127.0.0.1:8001/drawing-metadata/` で確認できる
- `runserver` はローカルで `8001` に上げている
