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
  - 個別レコード送信候補の静的解析で、属性値 payload は `attribute` / `attribute_option` / `attribute_value` 形状が候補。図面 `tags` は既存候補、製品・部品・プロジェクトのタグ保存口は未確認。
  - 図面詳細系には `tags` / `attributes` の受け口があり、実画面でも基本情報に `タグ` と `属性情報` が見えるため、創屋への初期連携は図面詳細を優先候補にする。
  - 製品・装置・ユニット詳細と部品詳細には `属性情報` が見えるがタグ欄は未確認。プロジェクト詳細にはタグ/属性の表示口が見えない。
  - `knowledgeSystemPayloadPreview` を登録済み11図面のfixtureへ同梱確認済み。ただしローカルDB内の古い11件は正規化属性が薄く、10件は対象別属性候補0件。実抽出入り代表では部品向け候補2件を確認。
  - 抽出済みJSONをDBへ再投入する `import_drawing_metadata_extracts` を追加。代表3図面の2D/3Dを取り込み直してfixtureを14図面へ更新し、payload候補あり4図面を確認。
  - `build_icad_extract_import_manifest.py` で共有済み112 JSONから24図面/43ファイルを選定。manifest取込後のfixtureは35図面、payload候補あり25図面、2D/3D両方あり20図面。
  - manifest取込後の代表図面 `CAA5012-02434000K1R1.icd` をローカルDjango詳細画面でChrome確認。図面/製品・装置・ユニット/部品/プロジェクト別の `本番タグ・属性 payload プレビュー` が見た目上も表示され、payload表の横長文字列向け折り返しと横スクロールを追加。
  - 2D詳細画面に `ビュー別取得状況` と `レイヤー別取得状況` を追加。文字/寸法/図形primitiveをビュー別・レイヤー別に集計し、印刷枠内/外/判定不明の件数を確認できるようにした。
  - `summarize_2d_extraction_coverage.py` で共有済み2D抽出JSONを集計。代表manifestでは2D対象19ファイル中、ビュー情報なし17、印刷枠情報なし17、レイヤー情報なし17、印刷枠判定不明1,388要素を確認。全量側は途中抽出JSONを含むため再抽出対象の洗い出しに使う。
  - 図面詳細の3D表示切替では `/web/public/models/test_000445.gltf` 読み込みエラーを確認。抽出器とは別件だが、2D/3Dプレビュー fixture 作成時の創屋確認事項にする。
  - `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を確認し、タグ候補レビュー画面は既存ビューワー同様、薄い View と表示 service に分ける方針にした。
  - 2D文字・寸法・記号系に `position_x/y/z` と `inside_print_area` を追加。`TR1D9K99027.icd` では文字190件すべてに座標が付き、185件が印刷枠内、5件が印刷枠外。
  - `SxGeomSpline2D` / 楕円弧 / ハッチング / 表面粗さ / 切断線 / デルタ / データムを primitive として取り込み。`TR1D9K99027.icd` と `CAA5012-02430002P1R1.icd` で `unsupported_geometry=0` を確認。
  - 3Dマスプロパティは `SxWF.getExtent()` -> `SxWF.getEntList()` -> `SxEnt.getMass()` で実装済み。`6800DDU.icd` / `474300AC219.icd` / `TR1D9Q00027.icd` で `mass_probe_status=available` を確認。
  - 2D図枠欄名候補を `title_block_candidates` と `title_block_fields` として追加。`TR1D9K99027_allviews_2d.json` は候補10件、`DFR-CM1-AA0305300011_2d.json` は材質候補を確認。
  - 2D primitive 由来の `geometry_feature_candidates` を追加。`CAA5012-02430002P1R1_primitives_2d.json` でハッチング8件、表面粗さ2件、長穴候補17件を確認。
  - Gemini API 低温度JSON分類サービスを追加。`title_block_candidates` の欄名分類補助に限定し、許可field外や範囲外indexは破棄する。
  - Gemini API 低温度JSON分類を2D抽出ジョブへ組み込み。APIキー未設定時はスキップし、API失敗時は `title_block_llm_classification_failed` warning として保持する。
  - 実サンプル2D図枠候補の洗い出し用に `scripts\probe_title_block_llm.py` を追加。共有抽出JSON 69件中、図枠候補ありは11ファイル/5サンプル。
  - Gemini実API分類は、OS環境変数の古いキー優先と旧モデル指定が原因で失敗していた。`backend\.env` 優先、`gemini-flash-latest` 主モデル、フォールバックモデルありへ修正し、代表manifest上位5サンプルで実API分類応答を確認済み。
  - `製図者` など欄名単体から `者` を値として採用する誤判定を抑止。候補行には残すが、`title_block_fields` へは採用しない。
  - 2D訂正内容候補を `revision_note_candidates` として追加。訂正/改訂/変更/修正/REV系の根拠文字、座標、印刷枠内外を保持し、詳細画面に表示。
  - 訂正内容候補がある場合は、本文ではなく存在だけを `改訂情報あり` タグとして生成。
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
- [x] manifest取込後の代表図面で本番タグ・属性payloadプレビューのローカル実画面確認を実施
- [x] 2Dビュー別/レイヤー別/印刷枠内外カバレッジを詳細画面と集計スクリプトで確認
- [x] 代表manifestの2D対象19件を最新runnerで再抽出し、ビュー121、印刷枠22、レイヤー4845、寸法1492、図形primitive20477まで取得できることを確認
- [x] 再抽出後の2Dカバレッジで `itemsWithoutView=0` を確認。`SxGeomLine2D` の `pnt1/pnt2` 座標取得を追加し、印刷枠判定不明は `unknownPrintArea=13569` から `488` まで減少。残りは主にハッチングと座標なし文字として記録
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
- [x] 3D全体材質とパーツ付加情報から部品材質候補を生成し、詳細画面に表示
- [x] Gemini API 低温度JSON分類を2D抽出ジョブへ組み込み、候補行へAI分類理由を表示
- [x] 実サンプル図枠候補の調査スクリプトを追加し、Gemini APIキー無効時の原因記録を強化
- [x] `.env` のGemini設定を再確認し、実API再プローブでも `API_KEY_INVALID` になることを記録
- [x] 図枠欄名単体の末尾文字を値として誤採用しないよう正規化を強化
- [x] 2D訂正内容候補を正規化属性と詳細画面に追加
- [x] 訂正内容候補から低ノイズの `改訂情報あり` タグを生成
- [x] `SxInfPartTree.entpart` 経由で3D部品単位の材質一覧を取得し、`parts[].materials` と高信頼の部品材質候補へ反映
- [x] ナレッジシステム実画面をChromeで再確認し、図面/プロジェクト/製品・装置・ユニット/部品詳細のタグ/属性表示差分をスクリーンショット保存
- [x] 共有済みICAD 39件で `parts[].materials` の取得率、部品パス、warning を横断集計
- [x] 材質ID `ZZZ`, `75`, `CDQ` を未解決材質として分離し、低信頼の `材質要確認` タグにする
- [x] 文字化け図枠候補をGemini分類対象から除外し、元候補indexへ戻して適用する
- [x] 共有抽出JSON 69件でGemini分類前フィルタを再プローブし、上位5サンプルのU+FFFD除外0件を記録
- [x] ICAD/SXNETアクセスをプロセス間Mutexで直列化し、3並列detectが全件成功することを確認
- [x] 2D/3D有無判定を強化し、2Dセグメント数を `detect` 出力と共有16件サマリに追加
- [x] VS一覧と印刷枠を raw_extract に取り込み、Django詳細画面の2Dサマリへ表示
- [x] symbol / hatch / cutline 系の2D geometryを primitive として保持し、特徴候補タグへ展開
- [x] Windows 抽出 worker と Linux/Docker backend の接続方式をDB-backed workerとして確定
- [x] 抽出開始前にjob leaseを抽出timeoutより長く延長し、長時間ICAD処理中の二重claimを防止
- [x] detail API に viewer 仕様互換の `viewerBootstrap` を追加
- [x] RAG投入用の読み取り専用 `rag-payload` API を追加し、事前フィルタ・再ランキング信号・要確認理由を分離
- [x] 材質ID辞書を正式材質・要確認・除外に分け、未登録コードを通常材質タグへ混ぜない
- [x] 2D図枠候補で `製図者` や `１．使用材料` のラベル片を値として誤採用しないよう強化
- [x] 創屋連携確認用に detail/viewer/RAG payload を同梱した fixture 出力コマンドを追加
- [x] 通常DBの登録済み11図面から創屋連携fixtureを実生成し、全件に detail/viewer/RAG payload が入ることを確認
- [x] APIの末尾スラッシュあり/なしを両方受け、フロント実装差で404にならないようにする
- [x] ローカルDjangoを実HTTP確認し、一覧画面、登録一覧API、詳細API、RAG payload API が返ることを確認
- [x] ローカル詳細画面に創屋連携・viewer/RAG受け渡し確認欄を追加し、Chromeで見た目を確認
- [x] 本番ナレッジシステムのAI検索、プロジェクト、製品・装置・ユニット、部品、図面管理の一覧/詳細をChromeで読み取り確認
- [x] 本番フロント資産を読み取り解析し、`drawing_attributes` / `product_attributes` / `part_attributes` と図面 `tags` の受け口候補を確認
- [x] Gemini APIキー設定後の `API_KEY_INVALID` 原因を特定し、`backend\.env` 優先読み込みと利用可能モデルへの切替で解消
- [x] `gemini-flash-latest` 主モデル、`gemini-3.1-flash-lite` / `gemini-3.5-flash` フォールバックを追加し、503/タイムアウト/不正JSON時の継続性を強化
- [x] 代表manifest上位5サンプルでGemini実API分類応答を確認し、CADに無い値を生成せずラベルのみ候補を低信頼で落とすことを記録
- [x] 本番フロント資産から個別レコードpayload候補を静的解析し、図面/製品・装置・ユニット/部品/プロジェクト向けの読み取り専用 `knowledgeSystemPayloadPreview` を detail API / fixture / 詳細画面に追加
- [x] `knowledgeSystemPayloadPreview` を通常DBの登録済み11図面から再fixture生成し、全件に同梱されることと対象別payload候補件数を横断確認
- [x] 抽出済みJSONを2D/3D snapshotとしてDBへ再投入する管理コマンドを追加し、代表3図面でfixture候補数が増えることを確認
- [x] 共有済み抽出JSONの中から各客先代表を選び、重複/旧形式を避けた取込manifestを作成
- [x] manifest経由で代表24図面を取り込み、fixture 35図面 / payload候補あり25図面 / 2D3D両方あり20図面まで拡張
- [x] 再抽出manifestをDBへ取り込み、創屋連携fixture 35図面を `drawing_metadata_fixture_reextract_2026-07-15.json` として再生成
- [x] `SxGeomLine2D` の座標取得を scalar `x1/y1/x2/y2` だけでなく `pnt1/pnt2` 系へ拡張し、代表2D 19件で印刷枠判定不明を `488` まで低減
- [x] `analyze_2d_print_area_unknowns.py` を追加し、印刷枠判定不明の理由を座標欠落/座標あり判定失敗/primitive型別に分解して確認
- [x] SXNETの `SxGeomHatch` は直接座標/外接矩形を確認できないため座標を捏造せず、raw証跡として残す方針を資料化
- [x] 印刷枠がある図面では `inside_print_area=true` の要素だけを自動タグ・検索候補へ使い、枠不明要素はraw証跡に残すよう正規化層を強化
- [x] 旧fixtureとの差分を `drawing_metadata_fixture_tag_diff_unknown_filter_2026-07-15.json` に保存し、自動タグ9件、`part_keywords` 1,031件、`spec_tokens` 1,014件、ハッチング/断面カウント169件のノイズ削減を確認
- [x] 本番ナレッジシステムのプロジェクト、製品・装置・ユニット、部品、図面、AI検索、類似検索をChrome実画面で再確認し、読み取り専用スクリーンショットを `output\knowledge_ui_screenshots_2026-07-15` に保存
- [x] 本番ナレッジシステム図面詳細の2D/3D切替をChromeで目視確認し、3D GLTF読み込みエラーを記録
- [x] ローカルDjango詳細画面とタグレビュー画面をChromeで目視確認し、2D/3Dあり、viewerタグ、保存フォルダ、パーツ付加情報数、統合タグ、2D/3D競合が画面に出ることを確認

## 次に着手する

- [ ] 創屋確認後の本番API/fixture名を連携項目表へ反映
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
