# tasklist

## 最終ゴール進行状況（2026-07-16 再監査）

- [x] 1 ICDを1件として登録し、内部パーツツリーを一覧へ展開しない
- [x] 子階層だけをサブアセンブリ判定に使わず、外部参照・明示語・保存先・手動確定を分類根拠にする
- [x] 共有39件すべてに2D/3D snapshotを保持し、snapshot欠落0件を確認
- [x] 2D内容あり31件すべてでビュー・レイヤー情報を保持
- [x] 印刷枠あり28件、複数枠2件、枠未定義3件、2D要素なし8件を別状態で記録
- [x] 3D材質候補29件、質量38件、パーツ付加情報19件を確認し、無い値を捏造しない
- [x] 製品・装置・ユニット／部品の一覧・詳細・編集・変更履歴・根拠・図面紐づけを統合ビューワーへ実装
- [x] 業務ステータスから「確認待ち」等の抽出内部状態を分離
- [x] 質量・重量をkg、小数点以下2桁で表示
- [x] 低価値の形状・存在フラグタグを除外し、DB監査で禁止タグ0件・取得元欠落0件を確認
- [x] タグJSONに `source` / `evidence` / `confidence` / `reason` を必須化。既存82 snapshotを再正規化し、DB監査で禁止タグ0件、source/evidence/confidence/reason欠落0件を確認。全共有39件fixture検証にもタグ根拠必須チェックを追加し、issue 0件を確認
- [x] Gemini実APIを17ファイル・60候補で評価し、分類precision/recall 1.0、誤採用0を確認
- [x] Geminiの追加採用値0件を明記し、任意補助から正本へ格上げしない
- [x] Django 71件、フロント58件、C# 14件、system check、migration差分、本番ビルドを確認
- [x] Chromeで詳細・編集・根拠・図面紐づけ候補38件を確認し、ブラウザエラー0件。APIの図面候補は固定manifest対象39件、紐づけ画面では現在詳細中の図面を候補から除外。検証アップロードや重複登録は固定manifest対象外として分離
- [x] 製品・装置・ユニット／部品一覧とシステム設定に再表示キャッシュを追加し、API実測で設定初期6ms、部品一覧455ms、製品一覧962ms、登録一覧176ms、引継ぎ集計1215msを確認。引継ぎ集計は初期表示から外し、該当パネル選択時だけ取得
- [x] 抽出worker heartbeat、ジョブ状態集計、直近失敗ジョブ、失敗理由、再抽出条件を `システム設定 > ICAD抽出管理` に追加。ページ更新・移動後も、起票済み/待機中/抽出中/完了/失敗とworker稼働状態を同じ画面で確認できるようにした
- [x] ICADタグ・属性取得の個別レビュー画面で、登録詳細APIから2D/3D別の最新ジョブを復元し、ページ更新後もジョブ履歴に待機中/抽出中/完了/失敗を表示。待機中/抽出中の同一モードは再抽出ボタンを無効化し、連打による重複起票を防止
- [x] 創屋本番DBへ登録・変更・削除を行わず、移植用API・データ契約・引継ぎ資料を更新
- [x] 全差分・未追跡ファイル・起動中サーバーを最終監査し、未追跡0件、5173/8001起動中、検証通過を確認

現行の正本資料: `docs/icad_entity_operations_and_quality_handoff_2026-07-16.md`、`design-qa.md`、`output/souya_handoff/icad_shared_sample_current_audit_2026-07-16.json`。

判定基準: 印刷枠未定義、2D要素なし、質量なしは抽出失敗と混同せず、データ条件と確認根拠が説明できる場合のみ既知状態として扱う。創屋本番DBへの書き込みは行わない。

## 2026-07-14 再設計メモ

- 新規方針:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_cad_tag_attribute_redesign_2026-07-14.md`
- 取得可能性調査:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_2d_3d_extraction_capability_matrix_2026-07-14.md`
- 共有サンプル実抽出メモ:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_shared_sample_extraction_findings_2026-07-14.md`
- 創屋向け連携項目表:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\souya_icad_tag_attribute_handoff_2026-07-14.md`
- タグ選定・2D/3Dビューワー連携仕様:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_selection_and_viewer_ui_spec_2026-07-15.md`
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
  - 2026-07-15 に本番詳細ページを読み取り専用で再確認。図面詳細は `タグ` / `属性情報` / 2D・3D切替あり、製品・装置・ユニット詳細と部品詳細は `属性情報` あり、プロジェクト詳細はタグ/属性表示口なし。証跡は `output\knowledge_ui_screenshots_2026-07-15\production-*-detail-current-2026-07-15.png`。
  - 図面詳細系には `tags` / `attributes` の受け口があり、実画面でも基本情報に `タグ` と `属性情報` が見えるため、創屋への初期連携は図面詳細を優先候補にする。
  - 製品・装置・ユニット詳細と部品詳細には `属性情報` が見えるがタグ欄は未確認。プロジェクト詳細にはタグ/属性の表示口が見えない。
  - `knowledgeSystemPayloadPreview` を登録済み11図面のfixtureへ同梱確認済み。ただしローカルDB内の古い11件は正規化属性が薄く、10件は対象別属性候補0件。実抽出入り代表では部品向け候補2件を確認。
  - 抽出済みJSONをDBへ再投入する `import_drawing_metadata_extracts` を追加。代表3図面の2D/3Dを取り込み直してfixtureを14図面へ更新し、payload候補あり4図面を確認。
  - `build_icad_extract_import_manifest.py` で共有済み112 JSONから24図面/43ファイルを選定。manifest取込後の登録は35図面。創屋引き渡しfixtureはsnapshotなし10図面を除外し、抽出済み25図面、2D/3D両方あり20図面。
  - 創屋引き渡しfixture契約検証で、2D snapshot 20件すべてに `raw_2d_sections.v1` の6区画が揃うことを確認。検証スクリプト側でも2D構造化セクション必須をチェックする。
  - 2D/3D照合の `conflicts` は設計レビュー対象に限定し、`source_kind`、`confidence_summary`、件数系、存在フラグ系の差分は `diagnosticConflicts` としてJSON証跡に残す。再生成fixture 25図面ではレビュー競合0件、診断差分93件。
  - manifest取込後の代表図面 `CAA5012-02434000K1R1.icd` をローカルDjango詳細画面でChrome確認。図面/製品・装置・ユニット/部品/プロジェクト別の `本番タグ・属性 payload プレビュー` が見た目上も表示され、payload表の横長文字列向け折り返しと横スクロールを追加。
  - 2D詳細画面に `ビュー別取得状況` と `レイヤー別取得状況` を追加。文字/寸法/図形primitiveをビュー別・レイヤー別に集計し、印刷枠内/外/判定不明の件数を確認できるようにした。
  - `summarize_2d_extraction_coverage.py` で共有済み2D抽出JSONを集計。代表manifestでは2D対象19ファイル中、ビュー情報なし17、印刷枠情報なし17、レイヤー情報なし17、印刷枠判定不明1,388要素を確認。全量側は途中抽出JSONを含むため再抽出対象の洗い出しに使う。
  - 図面詳細の3D表示切替では `/web/public/models/test_000445.gltf` 読み込みエラーを確認。抽出器とは別件だが、2D/3Dプレビュー fixture 作成時の創屋確認事項にする。
  - `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を確認し、タグ候補レビュー画面は既存ビューワー同様、薄い View と表示 service に分ける方針にした。
  - 2026-07-15 に `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を `integrations\2D_3D_CAD_VIEWR` へコピーし、提出済み2D/3Dビューワーの実装を基準に再確認した。完成版UIはDjango検証画面ではなく、2D/3Dビューワーの `drawingId -> bootstrap -> viewer2d/viewer3d open` の流れにタグ・属性補助パネルを足す方針へ戻す。
  - `integrations\2D_3D_CAD_VIEWR` は、図面管理を2D画像図/3D中間ファイルの読み込みと図面タグ表示に限定し、製品・装置・ユニット詳細と部品詳細は図面読み込み状態に依存しない独立ページとして表示する方針に修正。5173の実画面で `図面管理 -> 製品・装置・ユニット -> 部品 -> 図面管理` の切替と、製品/部品で `図面情報の読み込み後に表示します` が出ないことを確認。
  - 製品・装置・ユニット詳細と部品詳細の `紐づき` カードからもページ遷移できるように修正。5173の実画面で、製品・装置・ユニットの部品カードから部品詳細、部品詳細の図面カードから図面管理、部品詳細の製品・装置・ユニットカードから製品・装置・ユニット詳細へ遷移することを確認。
  - 提出済み2D/3Dビューワーの `GET /api/v1/drawings/{drawingId}/bootstrap` 契約を確認し、detail API 内の `viewerBootstrap` と同一形状を返す読み取り専用互換APIを追加。末尾スラッシュありも許容する。
  - 2D文字・寸法・記号系に `position_x/y/z` と `inside_print_area` を追加。`TR1D9K99027.icd` では文字190件すべてに座標が付き、185件が印刷枠内、5件が印刷枠外。
  - 2D文字・寸法・記号系に `print_frame_no` を追加。複数枚/複数印刷枠の図面で、要素がどの印刷枠に属するかを追跡する。`TR1D9K99027.icd` の再抽出では印刷枠1、文字190、寸法21、primitive862、文字の所属枠あり185件、印刷枠外文字5件を確認。
  - `probe-2d-print` を追加し、印刷実行なしで `SxModel.getInfPrintList()` と `SxInfPlot.getInfPlotList()` / `getInfDefPlot()` を確認。`TR1D9K99027.icd`、`DFR-CM1-AA0305300011.icd`、`217008-41J-3004.icd` は各1印刷枠、プロッタ3件、デフォルト `CubePDF` を取得できた。
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
  - 統合済み `integrations\2D_3D_CAD_VIEWR` の `viewer2d/open` / `viewer3d/open` を 501 応答から snapshot 由来プレビュー応答へ更新。2D は抽出JSONから生成した SVG、3D は抽出パーツ数に基づく STL メタデータプレビューを返し、既存ビューワーの raster/STL adapter で開けることを確認。
  - `?mode=3d` を初期表示モードとして解釈するようにし、2D/3D 直リンクを分けて確認できるようにした。`acc7d751-2006-46a3-9e9a-469c0abaefa2` で 2D SVG プレビューと 3D STL プレビューが表示され、3D 側は Playwright コンソールエラー0件。
  - 画面確認証跡は `C:\Users\s-iwata\Desktop\knowledge_system\output\knowledge_ui_screenshots_2026-07-15\viewer-2d-svg-preview-full-2026-07-15.png` と `viewer-3d-stl-preview-fixed-full-2026-07-15.png` に保存。証跡画像は git 管理外。
  - コピー済み既存ビューワー backend を確認。実変換は `viewer2d/open/upload` が PDF/JPEG/TIFF、`viewer3d/open/upload` が STL/STEP、PDM drawingId 経由が `source_2d_url` / `source_3d_url` 解決という契約。`.icd` ファイルそのものを直接2D/3D表示資産へ変換する口は既存backendにはない。
  - `DrawingMetadataSnapshot` の `canonical_attributes_json` / `raw_extract_json` に `viewer_assets` または `preview_assets` を入れる薄い契約を追加。2D は PDF/JPEG/TIFF URL、3D は STL URL があればメタデータプレビューより優先して既存ビューワーへ渡す。TIFF は既存ビューワー同様、`pageImageUrls` がある場合だけ直接扱う。
  - 2026-07-15 に本番ナレッジシステムの製品・装置・ユニット一覧/詳細、部品一覧/詳細をPlaywrightで読み取り確認。製品・部品一覧は `検索条件` と `検索結果` を白枠セクションで分け、結果はテーブル行クリックで詳細へ遷移する構成。詳細は `基本情報`、`属性情報`、`関連情報`、`変更履歴` を白枠セクションで表示する構成として、コピー済み2D/3Dビューワー側の製品・装置・ユニット/部品ページへ反映。図面管理は `図面を開く` 読み込み入口のまま維持していることをローカル5173で確認。
- 次に着手する場合:
  - 今回の SVG/STL は「抽出結果を既存ビューワー面で確認するためのメタデータプレビュー」であり、CAD形状そのものの変換ではない。次は ICAD 側で PDF/STL/STEP 等の実表示資産を生成するか、既存2D/3Dビューワーbackendの STEP->STL 変換APIへ接続し、`.icd` 由来の実図面画像/PDF相当と実3Dモデル相当を返す。
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
- [x] 2D文字・寸法・記号系へ所属印刷枠 `print_frame_no` を追加
- [x] `TR1D9K99027.icd` で印刷枠内外判定を実データ確認
- [x] `probe-2d-print` で3サンプルの出図範囲枠とプロッタ定義を読み取り専用確認
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
- [x] 2D raw証跡を `raw_2d_sections.v1` として `title_block` / `drawing_body` / `dimensions` / `notes` / `balloons` / `manufacturing_symbols` の6区画へ構造化。印刷枠がある場合は `inside_print_area=true` の要素だけを自動利用数へ含める
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
- [x] manifest経由で代表24図面を取り込み、登録35図面 / 抽出済み25図面 / 2D3D両方あり20図面まで拡張
- [x] 再抽出manifestをDBへ取り込み、snapshotなし10図面を除外した創屋連携fixture 25図面を `drawing_metadata_fixture_reextract_2026-07-15.json` として再生成
- [x] `SxGeomLine2D` の座標取得を scalar `x1/y1/x2/y2` だけでなく `pnt1/pnt2` 系へ拡張し、代表2D 19件で印刷枠判定不明を `488` まで低減
- [x] `analyze_2d_print_area_unknowns.py` を追加し、印刷枠判定不明の理由を座標欠落/座標あり判定失敗/primitive型別に分解して確認
- [x] SXNETの `SxGeomHatch` は直接座標/外接矩形を確認できないため座標を捏造せず、raw証跡として残す方針を資料化
- [x] 印刷枠がある図面では `inside_print_area=true` の要素だけを自動タグ・検索候補へ使い、枠不明要素はraw証跡に残すよう正規化層を強化
- [x] 旧fixtureとの差分を `drawing_metadata_fixture_tag_diff_unknown_filter_2026-07-15.json` に保存し、自動タグ9件、`part_keywords` 1,031件、`spec_tokens` 1,014件、ハッチング/断面カウント169件のノイズ削減を確認
- [x] 創屋引き渡しfixtureの契約検証スクリプト `validate_drawing_handoff_fixture.py` を追加し、25図面、2D snapshot 20件、3D snapshot 25件、図面/製品・装置・ユニット/部品/プロジェクト各25件の読み取り専用payloadを検証
- [x] 本番ナレッジシステムのプロジェクト、製品・装置・ユニット、部品、図面、AI検索、類似検索をChrome実画面で再確認し、読み取り専用スクリーンショットを `output\knowledge_ui_screenshots_2026-07-15` に保存
- [x] 本番ナレッジシステム図面詳細の2D/3D切替をChromeで目視確認し、3D GLTF読み込みエラーを記録
- [x] ローカルDjango詳細画面とタグレビュー画面をChromeで目視確認し、2D/3Dあり、viewerタグ、保存フォルダ、パーツ付加情報数、統合タグ、2D/3D競合が画面に出ることを確認
- [x] 2D構造化セクションを詳細画面へ追加し、`CAA5012-02434000K1R1.icd` で図枠/中央図面/寸法/注記/バルーン/製造記号の6行、印刷枠内外/判定不明件数、サンプルが見えることをChromeで確認
- [x] 本番ナレッジシステム実画面をChromeで再確認し、プロジェクト/製品・装置・ユニット/部品/図面/AI検索/類似検索のスクリーンショットを `output\knowledge_ui_screenshots_2026-07-15\60-*.png` 以降へ保存。製品・装置・ユニットの実URLは `/web/product`
- [x] 2D/3D照合の診断差分を `diagnosticConflicts` へ分離し、RAG投入前レビュー対象の `conflicts` に内部品質・件数・抽出元差分が混ざらないようにした。fixture契約検証で valid=true、issue 0件。ローカル詳細画面で `2D/3Dレビュー競合数` と `2D/3D診断差分数` の表示をChrome確認
- [x] 本番ナレッジシステムをChrome実画面で追加確認し、メニュー経由の正しいURLとして統合検索 `/web/integrated_search`、類似検索 `/web/drawing/similar_search` を確認。プロジェクト詳細はタグ/属性欄なし、製品・装置・ユニット詳細と部品詳細は属性情報欄あり、図面詳細はタグ/属性情報欄あり
- [x] タグレビュー画面に本番受け渡しpayload候補、対象別属性候補、対象別タグ候補を追加。図面/製品・装置・ユニット/部品/プロジェクトへ何を渡すかを1画面で確認できるようにし、`output\knowledge_ui_screenshots_2026-07-15\89-local-tag-review-payload-targets.jpg` でChrome確認
- [x] 既存2D/3Dビューワーの bootstrap API 契約を確認し、`/api/v1/drawings/{drawingId}/bootstrap` 互換の読み取り専用APIを追加
- [x] ブラウザで見せるローカル検証用成果物の入口として `/internal/drawing-metadata/handoff/` を追加。本番組み込みUIではなく、抽出・正規化・タグ生成・対象別payload・APIリンクの横断確認画面として扱う
- [x] `/internal/drawing-metadata/handoff/` の `2D=false / 3D=false` 表示はICAD実体なしではなく、抽出snapshotなしを意味するため、検証画面上は `未抽出` / `2Dのみ抽出済み` / `3Dのみ抽出済み` / `2D/3D抽出済み` として表示するよう修正
- [x] タグ選定仕様を作成し、タグ化する項目、属性に留める項目、自動タグ化しない項目、図面/プロジェクト/製品・装置・ユニット/部品別の適用先を整理
- [x] 既存2D/3Dビューワー契約を壊さず、`viewerBootstrap.metadata.tagAttributes` に図面/プロジェクト/製品・装置・ユニット/部品別のタグ・属性補助パネルpayloadを追加
- [x] 未抽出を放置せず、`viewerBootstrap.metadata.extractionDiagnostics` で `partial` / `not_extracted`、未抽出モード、ビュー差・レイヤー差・印刷枠差・パーツ付加情報差の再確認条件を返すようにした
- [x] `backend\.venv` を Python 3.12.10 で作り直し、pytest の一時領域を `tmp/pytest_run` に固定して AppData 側権限に依存しないテスト実行へ切り替えた
- [x] 未抽出・部分抽出を条件別再抽出キューへ回す土台を追加。ジョブに `extraction_profile` / `extraction_options_json` / `diagnostics_json` を保存し、2Dは全ビュー・全レイヤー・印刷枠、3Dはパーツツリー・材質・パーツ付加情報・重量系の再確認profileで起票できるようにした
- [x] `queue_missing_drawing_metadata_extracts` 管理コマンドを追加し、snapshot欠落モードを「存在しない」ではなく、条件別再抽出対象としてキューへ積めるようにした
- [x] Python 3.12.10 で `drawing_metadata` テスト49件と `manage.py check` を確認
- [x] Django worker から C# 抽出CLIへ `--extraction-profile` / `--extraction-options-json` を渡し、抽出結果JSONへ `extraction_profile` / `extraction_options` / `condition_diagnostics` として保存するようにした
- [x] .NET 8 の solution test と net48 runner build で、条件profile/options追加後も既存抽出runnerがビルドできることを確認
- [x] `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を `integrations\2D_3D_CAD_VIEWR` へコピーし、`.env` / DB / media / frontend build / node_modules はignore、`.env.example` は追跡対象として整理
- [x] コピーした2D/3Dビューワーの bootstrap 型へ `metadata.tagAttributes` / `metadata.extractionDiagnostics` を追加し、補助パネルで図面/プロジェクト/製品・装置・ユニット/部品別のタグ・属性候補を表示
- [x] `extraction_options` を C# 2D/3D 抽出ロジック内へ反映し、全ビュー/全レイヤー/印刷枠/図枠外記録/パーツツリー/材質/パーツ付加情報/重量系の走査条件を切り替え可能にした
- [x] 条件反映後に `drawing_metadata` pytest、Django check、.NET solution test、net48 runner build、コピー済みビューワーの対象Vitestとfrontend buildを確認
- [x] コピー済み2D/3Dビューワーを `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8001` で起動し、実データ `XH30-A08001-R03-JP_ロードカップ部改造.icd` の `viewerBootstrap` を表示。図面/プロジェクト/製品・装置・ユニット/部品の4対象、タグ候補、属性候補、レビュー要表示をPlaywrightで確認
- [x] knowledge_system側に `/api/v1/drawings/{drawingId}/viewer2d/open` / `viewer3d/open` を追加。現時点ではICADプレビュー変換API未接続のため、HTML 404ではなく `viewer_2d_source_not_connected` / `viewer_3d_source_not_connected` のJSONエラーを返し、ビューワー画面の `Unexpected token '<'` とReactの最大更新深度警告を解消
- [x] `U8718-S71-002_A3.icd` を条件profile付きで再抽出。dry-runで `PLAN 2d 2d_all_views_layers_print_frame` を確認し、実ジョブ `a42eedae-749b-4c15-847d-f42bd106ce28` が `activeExtractionProfile=2d_all_views_layers_print_frame` / `scanAllViews=true` / `scanAllLayers=true` / `classifyPrintFrame=true` / `recordOutsidePrintFrame=true` / `recordUnknownPrintArea=true` で成功。bootstrapは `has2d=true`, `has3d=true`, `status=extracted`
- [x] SXNET `SxModel.export(path, fname, file_type)` と `SxOptExport.FILE_TYPE_STL_MULTI=8` を確認し、C#抽出runnerへ `--preview-output-dir` / `--preview-public-base-url` / `--preview-file-name-prefix` を追加。3D抽出時にSTLプレビュー資産を `viewer_assets.3d` へ保存し、Django側の `/api/v1/drawing-metadata-preview-assets/{job_id}/{filename}` で配信できるようにした
- [x] 既存ビューワー連携の実資産URL判定を同一Django内の相対URLにも対応。`viewer3d/open` は生成STLの `viewer_assets.3d[].url` があればメタデータSTLより優先して既存3Dビューワーadapterへ渡す。2DはSXNET print/plot設定未検証のため、プレビュー生成要求時に `viewer_assets.2d[].status=unsupported` とwarningを残す
- [x] 実ICAD `6800DDU.icd` で `--preview-output-dir` 付き3D抽出を実行し、SXNET export から `preview_probe_6800ddu_fixed.stl` 980,724 bytes を生成できることを確認。抽出JSONには `viewer_assets.3d[0].status=ready`、`model_format=stl`、`file_path`、`url`、`size_bytes` が入る
- [x] `probe_3d_preview_assets.py` を追加し、manifest上位8件で3D STL preview生成を横断実行。ライズ、シブヤパッケージングシステム、ラップマスターウォルターズジャパン、SBY、NKS、ZCSET、宮本工業所、アースエンジニアリングの8件すべて `viewer_assets.3d.status=ready`、warning 0件。STLサイズは96,271 bytes から 74,086,436 bytes まで確認
- [x] 本番ナレッジシステム確認ではプロジェクト詳細にタグ/属性表示口が見えないため、プロジェクト側は一旦保留。既存受け口候補がある「製品・装置・ユニット」と「部品」向けに、タグチップ、属性情報、創屋連携payload候補を表示するページを追加。`/drawing-metadata/{id}/product-unit/` と `/drawing-metadata/{id}/parts/` をローカル起動中backendでHTTP確認し、どちらも200応答とタグ・属性UI表示を確認
- [x] 本番ナレッジシステム実画面を再確認し、左側メニューに「図面管理」「製品・装置・ユニット」「部品」が並ぶこと、各詳細の「関連情報」で紐づき確認を行うことを反映。ローカル画面の上部独自ボタンを撤去し、左側メニューと紐づき確認欄へ統一
- [x] Djangoジョブ経由で実ICAD `217008-41J-3004.icd` の3D抽出を実行し、`e32596c9-3fa6-4ae8-9f57-634aaf9ce85b.stl` 96,271 bytes を `preview_assets` へ生成。`viewer3d/open` が `actual_stl` を返し、既存3Dビューワーで実STL、タグ・属性候補、関連情報、左メニューの「製品・装置・ユニット」表記、ステータス「表示中」をPlaywrightで確認
- [x] 既存3Dビューワーで複数STL表示を確認。`PSG011-PA1100_クリーニング駆動.icd` は 70,249,978 bytes のSTLをDjangoジョブ経由で生成し約6秒で表示中、`CAA5012-02434000K1R1.icd` は 38,479,119 bytes のSTLを約5.5秒で表示中。どちらもエラーなし、初期カメラ収まり、タグ・属性候補、関連情報の表示をPlaywrightとスクリーンショットで確認
- [x] 大型3Dモデルで部品カードが縦長になりすぎる問題へ対応。長い属性値は160文字プレビューと `details` 展開にし、7件目以降は「ほか n 属性」として表示。70MB級 `PSG011-PA1100` で折りたたみ2件、ほか6属性、表示中、エラーなしをPlaywrightとスクリーンショットで確認
- [x] コピー済み2D/3Dビューワーのフロント構成を確認し、`features/viewer2d` と `features/viewer3d` はビュワー専用、`features/knowledgeEntities` は製品・装置・ユニット/部品/プロジェクトの対象物画面専用として分離。`App.tsx` は画面切替とビュワー起動の統括に戻し、タグ自動取得本体はバックエンド/抽出器側の責務として混在させない方針を明記
- [x] タグ自動取得の配置方針を画面へ反映。フロントの `システム設定` に `タグ自動取得設定` を追加し、設定値、Gemini低温度JSON分類、対象別マッピング、2D/3D採用ルールを表示。`ICAD抽出管理` と `API仕様・引継ぎ資料` は同じシステム設定内の管理パネルで開き、登録済みICAD、snapshot、ジョブ、保存元パス、対象別payload/APIリンクを確認できる。Djangoローカル確認画面は `/internal/drawing-metadata/system/tag-automation/` へ退避し、5173側のシステム設定から旧Django画面や図面管理へ遷移しないよう修正
- [x] システム設定の `ICAD抽出管理` クリック時に図面管理へ戻らないことをPlaywrightで再確認。`API仕様・引継ぎ資料` にはバックエンド集計API由来のAPI一覧10件、対象範囲、対象別payload件数、ICD別抽出状態を表示し、旧説明文言「ユーザー画面には表示しません」「通常画面へ出さず」が出ないことを確認
- [x] 製品・装置・ユニット/部品一覧とシステム設定の読み込み遅延を改善。製品/部品一覧はraw 3Dパーツ全量ではなくcanonical要約で初期表示し、rawのみデータはフォールバック。登録一覧と引継ぎ集計は巨大raw JSONを読まないquerysetへ変更。システム設定は初期表示で設定APIのみ読み、ICAD抽出管理/API仕様はクリック時に遅延取得。実測で製品一覧20,058ms→1,676ms、部品一覧9,261ms→768ms、登録一覧9,596ms→281ms、引継ぎ14,797ms→906ms、設定API99ms→22ms
- [x] 図面管理補助パネルと旧プロジェクト仮画面から `PRJ-OP30` / `OP30 カセット` / 架空担当者・日付などの固定サンプル表示を撤去。実bootstrapにあるタグ・属性候補だけ表示し、プロジェクトは受け口未確認のプレースホルダーに戻す。Playwrightで旧固定サンプル非表示を確認
- [x] 2D/3Dビューワー統合フロントの production 側から `shared/mock/drawingKnowledge` / `DrawingKnowledgeMock` / `buildDrawingKnowledgeMock` の命名を撤去し、実bootstrap由来の補助情報として `shared/knowledge/drawingKnowledge` / `DrawingKnowledgeDetail` / `buildDrawingKnowledgeDetail` へリネーム。固定モックではなく実データ表示用モジュールであることをコード上も明確化

## 創屋との接続時に確認する

- [ ] 創屋確認後の本番API/fixture名を連携項目表へ反映
- [ ] 創屋側の2D画像／3D中間ファイル生成・保存契約へ、確定済みタグ・属性payloadを接続
## 保留中の確認事項

- [ ] ナレッジシステム本体 Django のバージョン確認
- [ ] 図面管理の既存保存先仕様確認
- [ ] RAG 更新ジョブの既存基盤確認
- [ ] `sxnet.dll` の正式配置・参照条件確認

## 補足

- `backend/` / `src/` / `tests/` の差分が大きいので、別会話で再開するときは最初に `git status` を見ること
- ユーザーが触るメイン画面は `http://127.0.0.1:5173/` の2D・3Dビューワー統合フロント。`http://127.0.0.1:8001/` はAPI専用ステータス、`/drawing-metadata/` は通常画面として使わない
- Django HTMLの横断確認画面は開発用に `/internal/drawing-metadata/` へ退避。システム設定から旧Django画面や図面管理へ遷移せず、`ICAD抽出管理` / `API仕様・引継ぎ資料` を設定画面内で表示することをChrome検証済み
- 固定manifest `output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json` をシステム設定・製品/部品・図面候補・引継ぎ集計の標準スコープに設定。全登録68件のうち共有対象39件だけを表示し、対象39件は2D/3D snapshotあり39件、未抽出0件。対象外29件は検証アップロード、重複、途中検証用 `cad_data` として `scripts\audit_registered_drawings.py` で確認
- `runserver` はローカルで `8001`、Viteは `5173` に上げている
