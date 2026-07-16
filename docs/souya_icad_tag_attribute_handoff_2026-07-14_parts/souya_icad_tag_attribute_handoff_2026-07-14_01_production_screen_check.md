# 創屋向け ICADタグ・属性連携項目表 - 1. 本番実画面の確認結果

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

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

同日に、Chrome実画面を再度読み取り専用で確認し、現在表示される主要画面を追加保存した。登録、変更、削除は行っていない。

- プロジェクト一覧: `output\knowledge_ui_screenshots_2026-07-15\41-production-project-list-current.png`
- 製品・装置・ユニット一覧: `output\knowledge_ui_screenshots_2026-07-15\42-production-product-unit-list-current.png`
- 部品詳細: `output\knowledge_ui_screenshots_2026-07-15\40-production-part-detail-current.png`
- 部品一覧: `output\knowledge_ui_screenshots_2026-07-15\47-production-part-list-current-retry-wait.png`
- 図面一覧: `output\knowledge_ui_screenshots_2026-07-15\49-production-drawing-list-current-retry-wait.png`
- AI検索: `output\knowledge_ui_screenshots_2026-07-15\45-production-ai-search-current.png`
- 類似検索: `output\knowledge_ui_screenshots_2026-07-15\50-production-similar-search-current.png`

追加確認結果:

- プロジェクト一覧、製品・装置・ユニット一覧、部品一覧、図面一覧の検索結果テーブルには、タグ列や属性列は見えない。
- 部品詳細には `属性情報` 欄があり、サンプルでは属性情報なし表示だった。部品へはタグそのものより、材質・PRFX・メーカー・規格などを属性候補として渡すのが現実的。
- 図面一覧には `紐づき概要` が見える。図面タグ・属性は一覧列ではなく、詳細画面、検索条件、または裏側のRAG/類似検索用信号として使う想定にする。
- AI検索画面はチャット入力と履歴が中心で、タグ編集口は見えない。タグはRAG投入payload、検索前フィルタ、ランキング信号に使う。
- 類似検索画面は2D/3Dチェック、検索ファイル、類似度、図面名、用途、規格、重要度フィルタが見える。ICAD抽出タグは類似検索のフィルタや重みづけ補助に展開しやすい。

2026-07-15 に本番実画面の詳細ページを再度読み取り専用で確認し、現在表示の証跡を追加保存した。登録、変更、削除は行っていない。

- 図面詳細: `output\knowledge_ui_screenshots_2026-07-15\production-drawing-detail-current-2026-07-15.png`
- 製品・装置・ユニット詳細: `output\knowledge_ui_screenshots_2026-07-15\production-product-unit-detail-current-2026-07-15.png`
- 部品詳細: `output\knowledge_ui_screenshots_2026-07-15\production-part-detail-current-2026-07-15.png`
- プロジェクト詳細: `output\knowledge_ui_screenshots_2026-07-15\production-project-detail-current-2026-07-15.png`

現在表示の再確認結果:

- 図面詳細は `タグ` と `属性情報` の表示口があり、同一画面に `2D` / `3D` 切替がある。関連情報タブは `プロジェクト`、`製品・装置・ユニット`、`部品`、`会話ログ`。
- 製品・装置・ユニット詳細は `属性情報` の表示口があるが、タグ欄は見えない。関連情報タブは `プロジェクト`、`親製品・装置・ユニット`、`子製品・装置・ユニット`、`部品`、`図面`、`文書`、`会話ログ`。
- 部品詳細は `属性情報` の表示口があるが、タグ欄は見えない。関連情報タブは `製品・装置・ユニット`、`図面`、`文書`、`会話ログ`。備考に ICAD 参照元パスが入っている例があり、保存フォルダとファイル名を抽出属性として渡す方針と整合する。
- プロジェクト詳細はタグ/属性の表示口が見えない。関連情報タブは `製品・装置・ユニット`、`図面`、`文書`、`会話ログ`。プロジェクトへ直接タグを載せるには、創屋側で表示/API追加または関連図面由来の集約表示が必要。

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

