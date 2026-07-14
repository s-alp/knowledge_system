# tasklist

## 2026-07-14 再設計メモ

- 新規方針:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_cad_tag_attribute_redesign_2026-07-14.md`
- 取得可能性調査:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_2d_3d_extraction_capability_matrix_2026-07-14.md`
- 共有サンプル実抽出メモ:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_shared_sample_extraction_findings_2026-07-14.md`
- 創屋向け連携項目表:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\souya_icad_tag_attribute_handoff_2026-07-14.md`
- 位置づけ:
  - 既存 PoC の延長ではなく、ICAD 2D/3D から何を取得し、何にタグ・属性を付与するかを再定義した設計メモ。
  - 取得可能性調査では、SXNET根拠、現行PoC実装状況、実サンプル確認状況、未確認事項を分けている。
  - 旧 `texts` / `dimensions` 中心の 2D 抽出では粗いため、`図枠` / `中央図面` / `寸法・注記・加工指示` を分ける。
  - 3D は `SxWF.getInfPartTree()` を中核に、アセンブリ、部品、外部参照、材質、要素統計を分ける。
  - 2D/3D のどちらかを固定の正本にせず、図面名、図面サイズ、重量、材質、PRFX、ユニット番号などは両方から候補取得して照合する。
  - 2D からも材質、重量、担当者、承認者、日付、尺度、表面処理、塗装指示などを取得対象にする。
  - 現行抽出器は2D/3D有無を明示判定しておらず、空に近い抽出でも成功扱いになるため、`detect` または `source-kind=auto` が必要。
  - 図枠外/印刷範囲外の文字は、現時点では削除せず、座標と出図範囲を記録して `inside_print_area` として判定する方針。
  - 2D訂正表/訂正理由と、3Dパーツ付加情報はタグ・属性生成の重要な evidence source として追加する。
  - 客先が分散した実データを前提に、会社別固定座標ではなく、VS一覧、印刷枠、文字座標、部品付加情報を汎用証拠として保存する。
  - ICAD SX 2025 では `ICADX4J.EXE` が起動済みプロセスとして残るため、起動済み判定に `icadx4j` を含める。
  - 現時点で確認済みの共有サンプルは39件。追加サンプルが必要な場合は、必要なデータ種別を明示してユーザーへ依頼する。
  - 最新16件は `detect` を実行済み。全件 `has_3d=true`、9件 `has_2d=true`、7件は `has_2d_container=true` だが2D実体なし。
  - 本番ナレッジシステムの実画面は読み取り専用で確認済み。図面/プロジェクト/製品・装置・ユニット/部品の一覧にはタグ・属性列は未表示。
  - 本番フロント資産では `drawing_attributes` / `product_attributes` / `part_attributes` の参照を確認。`project_attributes` は未確認。
  - 図面詳細系には `tags` / `attributes` の受け口があり、実画面でも基本情報に `タグ` と `属性情報` が見えるため、創屋への初期連携は図面詳細を優先候補にする。
  - 製品・装置・ユニット詳細と部品詳細には `属性情報` が見えるがタグ欄は未確認。プロジェクト詳細にはタグ/属性の表示口が見えない。
  - 図面詳細の3D表示切替では `/web/public/models/test_000445.gltf` 読み込みエラーを確認。抽出器とは別件だが、2D/3Dプレビュー fixture 作成時の創屋確認事項にする。
  - `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を確認し、タグ候補レビュー画面は既存ビューワー同様、薄い View と表示 service に分ける方針にした。
  - 2D文字・寸法・記号系に `position_x/y/z` と `inside_print_area` を追加。`TR1D9K99027.icd` では文字190件すべてに座標が付き、185件が印刷枠内、5件が印刷枠外。
  - `SxGeomSpline2D` / 楕円弧 / ハッチング / 表面粗さ / 切断線 / デルタ / データムを primitive として取り込み。`TR1D9K99027.icd` と `CAA5012-02430002P1R1.icd` で `unsupported_geometry=0` を確認。
  - 3Dマスプロパティは `SxWF.getExtent()` -> `SxWF.getEntList()` -> `SxEnt.getMass()` で実装済み。`6800DDU.icd` / `474300AC219.icd` / `TR1D9Q00027.icd` で `mass_probe_status=available` を確認。
  - 2D図枠欄名候補を `title_block_candidates` と `title_block_fields` として追加。`TR1D9K99027_allviews_2d.json` は候補10件、`DFR-CM1-AA0305300011_2d.json` は材質候補を確認。
  - 2D primitive 由来の `geometry_feature_candidates` を追加。`CAA5012-02430002P1R1_primitives_2d.json` でハッチング8件、表面粗さ2件、長穴候補17件を確認。
  - Gemini API 低温度JSON分類サービスを追加。`title_block_candidates` の欄名分類補助に限定し、許可field外や範囲外indexは破棄する。
  - 3D材質APIを追加。`6800DDU.icd` で `material_probe_status=available`、`SUS440C`、比重7.7、17要素を確認。
- 次に着手する場合:
  - v2 raw schema を確定する。
  - 2D 抽出を `title_block` / `drawing_body` / `dimensions` / `notes` / `balloons` / `manufacturing_symbols` へ分離する。
  - `cross_source_reconciliation` として 2D 候補、3D 候補、採用値、差異、要確認理由を保持する。
  - Gemini API は曖昧分類の補助に限定し、CAD に存在しない値の推測採用は禁止する。

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
- [x] ICAD起動済み判定に `icadx4j` を追加
- [x] `detect` コマンドで2D/3D有無、2Dコンテナ有無、VS/印刷枠/ジオメトリ/パーツ数を返す
- [x] 2D抽出を全VS対象に拡張
- [x] 2D抽出でVS情報、印刷枠、レイヤー、要素所属レイヤーを保持
- [x] 抽出結果に保存フォルダ、ファイル名、拡張子を保持
- [x] 3Dパーツ付加情報を `ex_info_fields` として保持
- [x] Django詳細画面に2D/3D抽出サマリを追加
- [x] Django側にタグ候補レビュー画面を追加
- [x] 最新共有16件の `detect` を実行して結果を保存
- [x] 本番ナレッジシステム実画面とフロント資産を読み取り専用で確認
- [x] 2D文字・寸法・記号系へ座標と `inside_print_area` を追加
- [x] `TR1D9K99027.icd` で印刷枠内外判定を実データ確認
- [x] `SxGeomSpline2D` など未対応2Dジオメトリを primitive として取り込み
- [x] `TR1D9K99027.icd` / `CAA5012-02430002P1R1.icd` で `unsupported_geometry=0` を確認
- [x] 3Dマスプロパティを raw extract / canonical / detail display に追加
- [x] 実サンプル3件で重量・質量・体積・面積・重心取得を確認
- [x] ナレッジシステム実画面を視覚確認し、図面/プロジェクト/製品・装置・ユニット/部品の受け口差分を整理
- [x] 2D図枠欄名の初期辞書、候補レビュー表示、図枠由来タグ生成を追加
- [x] 2D primitive から形状・記号特徴候補タグを生成
- [x] 図面/プロジェクト/製品・装置・ユニット/部品別の創屋連携項目表を作成
- [x] Gemini API 低温度JSON分類サービスの入口を追加
- [x] 3D全体要素の材質一覧を取得
- [x] 2D/3D照合結果を `reconciledAttributes` として保持し、詳細画面に採用値・差異・理由を表示
- [x] 表面粗さ値、断面/切断表現、長穴/楕円候補、穴/円候補を 2D 形状・記号属性として保持し、詳細画面に表示

## 次に着手する

- [ ] 2D図枠欄名辞書を実サンプルで拡充し、Gemini API 低温度 JSON 分類をジョブへ組み込む
- [ ] 3D材質を部品単位へ紐づける
- [ ] 創屋確認後の本番API/fixture名を連携項目表へ反映
    - `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxEntSeg.getGeomList.html`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Contracts\Models.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\GeometryMapper.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\tests\IcadExtraction.SxNet.Tests\GeometryMapperTests.cs`
- [ ] 2D/3D有無判定とICAD起動済み判定を強化
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_shared_sample_extraction_findings_2026-07-14.md`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_2d_3d_extraction_capability_matrix_2026-07-14.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\Program.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\IcadProcessStarter.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\SxNetOpenContext.cs`
- [ ] VS一覧と印刷枠を raw_extract へ取り込む
  - 参照資料:
    - `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxModel.getVSList.html`
    - `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxModel.getInfPrintList.html`
    - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_shared_sample_extraction_findings_2026-07-14.md`
  - 次に触るファイル:
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Contracts\Models.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\Icad2DExtractor.cs`
    - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\GeometryMapper.cs`
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
