# 創屋向け ICADタグ・属性連携項目表

- 作成日: 2026-07-14
- 対象: ICAD 2D/3D 抽出結果、タグ候補、属性候補を本番ナレッジシステムへ連携するための受け渡し整理
- 前提: 本番ナレッジシステムへの登録、更新、削除は創屋側で実装する。こちらは抽出、正規化、候補生成、fixture/API契約案を提供する。

## 1. 本番実画面の確認結果

読み取り専用で確認した。登録、変更、削除は行っていない。

| 対象 | 一覧の見た目 | 詳細の見た目 | 既存受け口の見立て | 初期連携優先度 |
| --- | --- | --- | --- | --- |
| 図面 | タグ/属性列は未表示。`紐づき概要` に PRJ / 製品 / 部品関係が出る | 基本情報に `タグ` と `属性情報` が表示される。2D/3Dプレビュー切替あり | `tags` / `attributes` / `drawing_attributes` が初期受け口候補 | 高 |
| プロジェクト | タグ/属性列は未表示 | タグ/属性の表示口は見えない | `project_attributes` は未確認。追加APIまたは補助タブが必要 | 中 |
| 製品・装置・ユニット | タグ/属性列は未表示 | `属性情報` は表示されるがタグ欄は見えない | `product_attributes` が属性受け口候補 | 中 |
| 部品 | タグ/属性列は未表示 | `属性情報` は表示されるがタグ欄は見えない | `part_attributes` が属性受け口候補 | 中 |

図面詳細の3D表示へ切り替えた際、`/web/public/models/test_000445.gltf` の読み込みで `Unexpected token '<'` エラーを確認した。抽出器とは別件だが、2D/3Dプレビュー fixture 作成時の確認事項として創屋へ共有する。

2026-07-15 に Chrome で本番実画面を再確認した。登録、変更、削除は行っていない。

- AI検索: `output\knowledge_ui_screenshots_2026-07-15\production-knowledge-ai-search-viewport.png`
- プロジェクト一覧: `output\knowledge_ui_screenshots_2026-07-15\production-project-list-viewport.png`
- プロジェクト詳細: `output\knowledge_ui_screenshots_2026-07-15\production-project-detail-viewport.png`
- 製品・装置・ユニット一覧: `output\knowledge_ui_screenshots_2026-07-15\production-product-unit-list-viewport.png`
- 製品・装置・ユニット詳細: `output\knowledge_ui_screenshots_2026-07-15\production-product-unit-detail-viewport.png`
- 部品一覧: `output\knowledge_ui_screenshots_2026-07-15\production-part-list-viewport.png`
- 部品詳細: `output\knowledge_ui_screenshots_2026-07-15\production-part-detail-viewport.png`
- 図面一覧: `output\knowledge_ui_screenshots_2026-07-15\production-drawing-list-viewport.png`
- 図面詳細: `output\knowledge_ui_screenshots_2026-07-15\production-drawing-detail-viewport.png`

追加所見:

- プロジェクト詳細は `基本情報` と `関連情報` が中心で、このサンプルではタグ/属性欄は見えない。プロジェクトへタグを反映するには、既存APIまたは補助タブの有無を創屋へ確認する必要がある。
- 製品・装置・ユニット詳細と部品詳細には `属性情報` 欄がある。ただしサンプルでは `属性情報がありません。` と表示され、一覧側にタグ/属性列は見えない。
- 図面詳細には `タグ` と `属性情報` 欄があり、2D/3D切替もある。初期連携先は引き続き図面詳細を最優先にする。

同日に本番フロント資産 `index-B8bCj6lB.js` を読み取り専用で確認した。解析結果は `output\knowledge_ui_screenshots_2026-07-15\frontend_tag_attribute_contract_probe.json` に保存した。

| 対象 | フロント資産上の受け口所見 | 判断 |
| --- | --- | --- |
| 図面 | `getDrawingAttributes`, `/drawing_attributes/`, `/drawing_attributes/{id}/`, `/drawing_attributes/reorder/` がある。図面詳細は response の `tags` と `attributes` を表示している | タグ・属性とも既存受け口候補あり |
| 製品・装置・ユニット | `getProductAttributes`, `/product_attributes/`, `/product_attributes/{id}/`, `/product_attributes/reorder/` がある。詳細は response の `attributes` を表示している | 属性の既存受け口候補あり。タグは未確認 |
| 部品 | `getPartAttributes`, `/part_attributes/`, `/part_attributes/{id}/`, `/part_attributes/reorder/` がある。詳細は response の `attributes` を表示している | 属性の既存受け口候補あり。タグは未確認 |
| プロジェクト | `project_attributes` はフロント資産内で見当たらない。詳細取得のマッピングにも `attributes` / `tags` は見えない | 既存受け口は弱い。創屋確認が必要 |
| 文書 | 文書登録/詳細には `tags` があり、注記上も自動抽出・手動追加/削除が想定されている | 参考。今回のICAD図面連携の主対象ではない |

追加で `scripts\probe_frontend_entity_payload_contract.py` を作成し、個別レコード送信時の payload 候補を本番フロント資産から静的解析した。結果は `output\knowledge_ui_screenshots_2026-07-15\frontend_entity_payload_contract_probe.json` に保存した。

| 確認項目 | 静的解析結果 | こちら側の扱い |
| --- | --- | --- |
| 属性値 payload | `attribute`, `attribute_option`, `attribute_value` の形状候補を確認 | 本番マスタIDが必要なため、こちらは `attributeName` と `attributeValue` を渡し、ID解決は創屋確認事項にする |
| 図面タグ | 図面詳細表示の `tags` と、送信候補 `tags` を確認 | 図面はタグ直接連携の第一候補 |
| 製品・装置・ユニットタグ | 詳細の属性表示はあるが、タグ保存口は未確認 | タグ専用口が無ければ属性 `自動タグ候補` として代替できる payload も併記 |
| 部品タグ | 詳細の属性表示はあるが、タグ保存口は未確認 | 材質・メーカー・規格タグは部品属性への代替候補として併記 |
| プロジェクトタグ/属性 | `project_attributes` / project tags は未確認 | 既存API追加、補助タブ、または関連図面由来の集約表示が必要 |

## 2. こちらが提供するデータ単位

| 提供単位 | 主なキー | 内容 | 備考 |
| --- | --- | --- | --- |
| `source_file` | `full_path`, `directory_path`, `file_name`, `extension` | 保存フォルダ、ファイル名、拡張子 | ユーザー要望により検索・追跡用属性として保持 |
| `raw_extract_2d` | `view_sheets`, `print_frames`, `layers`, `texts`, `dimensions`, `geometry_primitives` | SXNETから取得した2D証拠 | 図枠外/印刷枠外は削除せず `inside_print_area` で判定 |
| `raw_extract_3d` | `top_part`, `parts`, `mass_properties`, `mass_probe_status`, `materials`, `material_probe_status` | SXNETから取得した3D証拠 | パーツ付加情報は `ex_info_fields` として保持 |
| `canonical_attributes` | 下表参照 | 2D/3D横断の正規化属性 | 本番DB/APIへ渡す属性候補 |
| `derived_tags` | `tag`, `source`, `confidence`, `manual_flag`, `tag_rule_version` | 自動タグ候補 | 採用前にレビュー可能 |
| `reconciledAttributes` | `attribute`, `value2d`, `value3d`, `chosenValue`, `chosenMode`, `status`, `reason` | 2D/3D照合結果 | 一致、片側のみ、統合、手動上書き、競合を全属性単位で保持 |
| `conflicts` | `attribute`, `mode2dValue`, `mode3dValue`, `chosenValue`, `chosenMode`, `reason` | 2D/3D差異の抜粋 | 既存画面向けのレビュー対象。どちらかを正本に固定しない |
| `knowledgeSystemPayloadPreview` | `targets[].payloadPreview`, `targets[].attributes`, `targets[].tags` | 本番タグ・属性連携の候補payload | 本番登録は行わない。図面/製品・装置・ユニット/部品/プロジェクト別に、既存受け口・未確定点・属性マスタID未解決を明示 |

## 3. 図面へ連携する項目

図面は初期連携の最優先対象。詳細画面に `タグ` と `属性情報` の表示口がある。

| 分類 | 項目 | source | 連携先候補 | 信頼度方針 |
| --- | --- | --- | --- | --- |
| ファイル | ファイル名、保存フォルダ、フルパス | `source_file` | 図面属性 | 高 |
| 識別 | 図番、図面名、改訂 | `title_block_fields`, ファイル名, 3Dモデル名 | 図面属性 | 中。図枠辞書拡充後に上げる |
| 図面条件 | 図面サイズ、尺度、ビュー/用紙数、印刷枠数 | `print_frames`, `view_sheets` | 図面属性 | 中 |
| 2D図枠 | 担当者、検図者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号 | `title_block_candidates`, `title_block_fields` | 図面属性、タグ候補 | 候補値。根拠文字と座標を保持 |
| 2D図枠AI補助分類 | 曖昧な図枠候補の欄名 | `title_block_llm_classifications`, `title_block_candidates[].llm_*` | 図面属性候補の補助 | Gemini低温度JSON分類。既存候補値だけを分類し、CADに無い値は生成しない |
| 2D訂正内容 | 訂正、改訂、変更、修正、REV系の注記/表文字 | `revision_note_candidates`, `revision_note_count` | 図面属性、改訂履歴確認、`改訂情報あり` タグ | 改訂番号とは別に、根拠文字・座標・印刷枠内外を保持。本文そのものはタグ化しない |
| 2D特徴 | ハッチング、表面粗さ、切断線、データム、幾何公差、長穴候補、穴候補 | `geometry_feature_candidates` | 図面タグ候補 | 候補タグ。根拠ジオメトリ、件数、概要を保持 |
| 2D形状・記号属性 | 表面粗さ記号数/値、断面・切断表現数、長穴/楕円候補数、穴/円候補数、候補径 | `surface_roughness_*`, `section_feature_count`, `slot_candidate_*`, `hole_candidate_*` | 図面属性、類似検索フィルター補助 | 印刷枠外は除外。円や楕円は形状候補として保持し、用途断定はしない |
| 3D構成 | 最上位パーツ名、部品数、外部参照、ミラー、未解決参照 | `top_part`, `parts` | 図面属性、タグ候補 | 高 |
| 3D重量 | 質量、重量、体積、面積、密度、重心、単位、計算対象要素数 | `mass_properties` | 図面属性 | 中から高。`mass_probe_status` と warning を併記 |
| 3D材質 | 材質ID、材質名、比重、対象要素数 | `materials` | 図面属性、材質タグ候補 | 中。日本語材質名は文字コード揺れがあるため材質IDを主キー寄りに扱う |
| 3D部品材質候補 | パーツ階層、材質ID/材質名、比重、根拠、信頼度、材質分類 | `part_material_candidates` | 図面属性、部品属性 | `formal` は通常材質、`unresolved` は要確認、`excluded` はタグ化しない。パーツ付加情報内の材質らしい値は中信頼 |
| パーツ付加情報 | 客先固有フィールド、PRFX候補、材質候補、ユニット候補 | `parts[].ex_info_fields` | 図面属性、部品属性 | 中。客先ごとの辞書化が必要 |

## 4. プロジェクトへ連携する項目

プロジェクト詳細にはタグ/属性の表示口が見えなかったため、創屋への確認事項にする。

| 項目 | source | 活用イメージ | 創屋確認事項 |
| --- | --- | --- | --- |
| 客先名 | 保存パス、図枠文字、3Dパーツ情報 | プロジェクト検索、絞り込み | プロジェクト属性APIの有無 |
| 案件名/プロジェクト名 | 保存パス、ファイル配置、図面紐づき | 案件単位の検索 | 既存プロジェクトとのID対応方法 |
| 装置カテゴリ | 保存パス、図枠文字、部品名 | ガントリー、ロボット、フィーダー等の絞り込み | タグとして持つか属性として持つか |
| 代表図面/代表ユニット | 図面と製品・部品の紐づき | 関連資料の入口 | 既存関連テーブルの更新方法 |

## 5. 製品・装置・ユニットへ連携する項目

詳細に `属性情報` が見えるため、タグ欄が未表示でも属性連携候補になる。

| 項目 | source | 活用イメージ | 注意 |
| --- | --- | --- | --- |
| 装置カテゴリ | パス、図枠、3D構成 | 装置・工程単位の検索 | 一社固定語にしない |
| ユニット番号 | 図枠、部品表、3Dパーツ名、パーツ付加情報 | ユニット単位の検索 | PRFXと混同しない |
| PRFX | 図枠、部品表、3D任意情報 | 客先固有の部品/装置紐づけ | 表記揺れ辞書が必要 |
| 代表材質/表面処理 | 図枠、注記、3D材質候補 | 製作・調達検索 | 部品単位材質と装置代表材質を分ける |

## 6. 部品へ連携する項目

詳細に `属性情報` が見えるため、パーツ付加情報と3D部品情報の受け口候補になる。

| 項目 | source | 活用イメージ | 注意 |
| --- | --- | --- | --- |
| パーツ名、階層パス | `parts[].name`, `parts[].tree_path` | 部品検索、BOM接続 | 同名部品があるため階層も渡す |
| 参照図面名、参照パス | `ref_model_name`, `ref_model_path` | 外部部品追跡 | 未解決参照は警告として残す |
| パーツ付加情報 | `ex_info_fields` | 材質、PRFX、客先固有分類 | 澁谷工業/ニッケ系で重要 |
| 部品材質候補 | `materials`, `ex_info_fields` | 材質検索、調達/加工属性 | 単一パーツ/単一材質と材質表記パターン一致のみ自動候補化 |
| 外部参照、ミラー、読取専用、未解決 | `is_external`, `is_mirror`, `is_read_only`, `is_unloaded` | 流用/注意情報 | タグ化は中信頼 |
| 材質候補 | 2D図枠、2D注記、3D材質API、パーツ付加情報 | 加工・調達検索 | 3D全体材質と部品材質候補は実装済み。複数部品/複数材質の厳密紐づけは追加調査 |

## 7. API/fixture の最小契約案

PoC側では、創屋確認用の fixture 出力として以下を用意した。

```powershell
python backend\manage.py export_drawing_metadata_fixtures --output output\souya_handoff\drawing_metadata_fixture.json
```

この fixture には、図面詳細API相当の `detailApiPayload`、2D/3Dビューワー初期表示用の `viewerBootstrap`、RAG投入用の `ragPayload`、本番タグ・属性連携候補の `knowledgeSystemPayloadPreview` を同梱する。登録、変更、削除は行わない読み取り専用の受け渡しJSONである。

2026-07-15 に通常DBの登録済み図面で実生成した。

- 出力先: `output\souya_handoff\drawing_metadata_fixture_2026-07-15.json`
- 出力件数: 11図面
- 契約チェック: 11件すべてに `detailApiPayload`, `viewerBootstrap`, `ragPayload`, `knowledgeSystemPayloadPreview` が存在
- 追加payload横断確認: ローカルDB内の11件は古い登録データが多く、10件は対象別属性候補0件。実抽出入りの `9NK452WX90-00-LINER-A3-3D-01.icd` では部品向け属性候補2件を確認。抽出済みJSONの再投入が進むほど候補数が増える想定
- 実抽出入り代表: `9NK452WX90-00-LINER-A3-3D-01.icd`
  - `viewerBootstrap.availability.has2d=true`
  - `viewerBootstrap.availability.has3d=true`
  - `ragPayload.schemaVersion=drawing_metadata_rag_payload.v1`

抽出済みJSONをローカルDBへ再投入するため、`import_drawing_metadata_extracts` 管理コマンドを追加した。既存の保存serviceを通すため、`RegisteredDrawing`、2D/3D snapshot、latest job、audit log が揃う。ICADを再起動せず、共有済み抽出JSONから詳細画面/API/fixtureを再検証できる。

```powershell
python backend\manage.py import_drawing_metadata_extracts path\to\sample_2d.json path\to\sample_3d.json
```

同日に代表3図面の2D/3D抽出JSONを取り込み直し、fixtureを再生成した。

- 再生成後の出力件数: 14図面
- `knowledgeSystemPayloadPreview` 候補あり: 4図面
- 代表候補数:
  - `CAA5012-02430002P1R1.icd`: 図面 attrs=1/tags=3、製品 attrs=1、部品 attrs=2、プロジェクト attrs=1
  - `DFR-CM1-AA0305300011.icd`: 図面 attrs=2/tags=2、製品 attrs=1、部品 attrs=3/tags=1、プロジェクト attrs=1
  - `TR1D9K99027.icd`: 図面 attrs=2/tags=4、製品 attrs=1、部品 attrs=7/tags=2、プロジェクト attrs=1

同日にローカルDjangoを `http://127.0.0.1:8001` で起動し、実HTTPでも確認した。

- `GET /drawing-metadata/`: HTTP 200
- `GET /api/v1/drawing-metadata/registrations/`: 11件取得
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/`: `viewerBootstrap` あり
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/rag-payload/`: `schemaVersion=drawing_metadata_rag_payload.v1`
- 末尾スラッシュあり/なしの両方をAPIルーティングで受ける。フロント実装差で404にならないようにするため。

2026-07-15 にローカル詳細画面へ `創屋連携・viewer/RAG 受け渡し確認` 欄を追加した。初心者でも確認できるよう、詳細API、RAG投入payload API、タグレビュー画面へのリンク、viewer初期化情報、RAG事前フィルタ、RAGランキング信号、投入前レビューを表形式で表示する。

同欄へ `本番タグ・属性 payload プレビュー` を追加した。図面、製品・装置・ユニット、部品、プロジェクトの各対象について、既存受け口、タグAPI状態、タグ候補、属性候補数、payloadキー、候補endpointを表示する。`attribute` / `attribute_option` は本番マスタIDが必要なため、プレビューでは `null` とし、`bindingStatus=needs_attribute_master_binding` として創屋確認待ちを明示する。

- ローカル確認URL: `http://127.0.0.1:8001/drawing-metadata/7d47aa93-de58-467d-a145-4a584cd6c52b/`
- 画面確認画像: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-metadata-handoff-viewport.png`
- DOM確認: `創屋連携・viewer/RAG 受け渡し確認`, `詳細API`, `RAG投入payload API`, `viewer 初期化情報`, `RAG 事前フィルタ`, `RAG ランキング信号`, `投入前レビュー`, `本番タグ・属性 payload プレビュー` が表示されることを確認

```json
{
  "drawingId": "host drawing id",
  "sourceFile": {
    "fullPath": "J:\\...",
    "directoryPath": "J:\\...",
    "fileName": "sample.icd",
    "extension": ".icd"
  },
  "canonicalAttributes": {
    "drawing_number": null,
    "drawing_name": null,
    "customer_name": "澁谷工業",
    "equipment_category": "ロボット",
    "mass_probe_status": "available",
    "weight_value": 0.00540269,
    "title_block_fields": {
      "material": "SUS304"
    },
    "geometry_feature_candidates": [
      {
        "feature": "surface_roughness",
        "tag": "加工指示:表面粗さ",
        "confidence": "medium",
        "count": 2
      }
    ]
  },
  "derivedTags": [
    {
      "tag": "客先:澁谷工業",
      "source": "customer_name",
      "confidence": "high",
      "manual_flag": false
    }
  ],
  "reconciledAttributes": [
    {
      "attribute": "material",
      "value2d": "SUS304",
      "value3d": "SUS304",
      "chosenValue": "SUS304",
      "chosenMode": "3d",
      "status": "matched",
      "reason": "2Dと3Dの抽出値が一致したため採用しました。"
    },
    {
      "attribute": "weight_value",
      "value2d": "2.1kg",
      "value3d": 2.08,
      "chosenValue": 2.08,
      "chosenMode": "3d",
      "status": "conflict",
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を仮採用しています。"
    }
  ],
  "conflicts": [
    {
      "attribute": "weight_value",
      "mode2dValue": "2.1kg",
      "mode3dValue": 2.08,
      "chosenValue": 2.08,
      "chosenMode": "3d",
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を仮採用しています。"
    }
  ]
}
```

## 8. 創屋への確認事項

- 図面詳細の `tags` / `attributes` の保存先テーブルとAPI名
- `drawing_attributes`, `product_attributes`, `part_attributes` の登録/更新APIの有無
- プロジェクトに属性/タグを保存するAPIまたは詳細表示口の有無
- タグは図面単位だけか、製品・ユニット・部品にも保存できるか
- `drawing_attributes`, `product_attributes`, `part_attributes` はマスタ定義APIに見えるため、個別図面/製品/部品へ属性値を保存する際の payload 形式と更新API名
- 個別図面/製品/部品の属性値 payload で `attribute`, `attribute_option`, `attribute_value` を使う見立てが正しいか
- `attributeName` / `attributeValue` で渡した候補を、創屋側で本番属性マスタIDへ解決できるか。こちら側でマスタIDを事前fixture化する必要があるか
- 図面と文書には `tags` がある一方、製品・部品・プロジェクトのタグ保存口はフロント資産上では未確認のため、タグを属性として代替するか、タグ保存APIを追加するか
- 手動補正履歴をどのテーブルに保持するか
- RAG検索インデックスへ投入できるフィールド名、型、更新タイミング
- 2D/3Dプレビュー詳細APIへ追加項目を渡せるか
- 本番3Dプレビューの `test_000445.gltf` 読み込みエラーの原因
- 材質辞書の `formal` / `unresolved` / `excluded` を本番マスタとして持つか、こちらの抽出モジュール側だけで持つか

## 9. こちら側の残実装

- 3D材質APIの部品単位紐づけは候補生成まで実装済み。材質ID辞書も初期実装済みで、共有39件では要確認材質を `ZZZ`, `CDQ`, `75` まで絞り込めている。次は正式材質マスタとの突合
- 2D図枠欄名辞書の客先横断拡充
- Gemini API低温度JSON分類は2D抽出ジョブへ組み込み済み。APIキー未設定時はスキップし、API失敗時は `title_block_llm_classification_failed` warning として記録する。既存候補値の分類補助に限定し、ルール抽出済みの属性は上書きしない。2026-07-15 に再プローブしたが、実API確認は引き続き `API_KEY_INVALID` で未完了。結果は `output\live_extracts\title_block_llm_probe_2026-07-15\gemini_reprobe_2026-07-15.json` に保存した
- 長穴、穴数、断面、表面粗さ値は PoC で属性化済み。次は実サンプル横断で、円/楕円を穴・長穴として断定できる条件を詰める
- 2D/3D照合結果の採用値、差異、要確認理由は PoC 画面表示まで実装済み。次は本番API/fixture名確定後の項目名合わせ
