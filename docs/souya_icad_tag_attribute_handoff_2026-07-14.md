# 創屋向け ICADタグ・属性連携項目表

- 作成日: 2026-07-14
- 対象: ICAD 2D/3D 抽出結果、タグ候補、属性候補を本番ナレッジシステムへ連携するための受け渡し整理
- 前提: 本番ナレッジシステムへの登録、更新、削除は創屋側で実装する。こちらは抽出、正規化、候補生成、fixture/API契約案を提供する。
- 2026-07-16の編集・紐づけ・根拠・タグ品質・39件監査は `docs/icad_entity_operations_and_quality_handoff_2026-07-16.md` を正とする。

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

## 2. こちらが提供するデータ単位

| 提供単位 | 主なキー | 内容 | 備考 |
| --- | --- | --- | --- |
| `source_file` | `full_path`, `directory_path`, `file_name`, `extension`, `sx_net_input_path`, `sx_net_input_strategy`, `used_sx_net_alternate_path` | 保存フォルダ、ファイル名、拡張子、SXNETへ実際に渡したパス | 原本パスは検索・追跡用属性として保持。SXNETの長パス制限を避けるため短縮パスまたは一時コピーを使った場合も診断できるようにする。ブラウザアップロード由来ICDは内部保存名を `input.icd` に固定し、`temporary_copy_forced` で短い一時パスを使う |
| `raw_extract_2d` | `view_sheets`, `print_frames`, `layers`, `texts`, `dimensions`, `geometry_primitives`, `referenced_parts` | SXNETから取得した2D証拠 | 図枠外/印刷枠外は削除せず `inside_print_area` で判定 |
| `raw_2d_sections` | `title_block`, `drawing_body`, `dimensions`, `notes`, `balloons`, `manufacturing_symbols` | 2D証拠を画面/fixture向けに6区画へ整理した要約 | `raw_2d_sections.v1`。印刷枠がある図面では `inside_print_area=true` の要素だけを自動利用数へ含める |
| `raw_extract_3d` | `top_part`, `parts`, `mass_properties`, `mass_probe_status`, `materials`, `material_probe_status` | SXNETから取得した3D証拠 | パーツ付加情報は `ex_info_fields` として保持 |
| `canonical_attributes` | 下表参照 | 2D/3D横断の正規化属性 | 本番DB/APIへ渡す属性候補 |
| `derived_tags` | `tag`, `source`, `confidence`, `manual_flag`, `tag_rule_version` | 自動タグ候補 | 採用前にレビュー可能 |

### 2.1 抽出失敗診断

`GET /api/v1/drawing-metadata/handoff-summary` の `recentFailedJobs[]` は、SXNETの生エラーだけでなく以下を返す。

| 項目 | 内容 |
| --- | --- |
| `errorClass` | `sxnet_rejected_as_not_drawing_file`, `path_length_limit`, `source_file_not_found`, `extractor_timeout`, `sxnet_open_failure` などの分類 |
| `sourcePreflight.sourcePathLength` | 登録されている原本ICADパスの文字数 |
| `sourcePreflight.sourcePathWithinSxnetLegacyLimit` | SXNETへ直接渡すには安全な長さか |
| `sourcePreflight.requiresSxnetStagedInput` | 抽出時に短い一時パスへ退避すべきか |
| `sourcePreflight.sourceExistsFromCurrentMachine` | 現在のworker実行環境から原本ICADへアクセスできるか |
| `reextractCondition` | 再抽出前に確認する条件。長パス退避、ICAD対応版、外部参照不足、ファイル破損、ネットワークパス未接続などを切り分ける |

SXNETの `指定したファイルは図面ファイルではありません。` は、ICD拡張子そのものを否定する意味に固定しない。原本パス、長パス退避、ICAD/SXNET対応版、外部参照不足、2D/3Dデータ有無を分けて確認する。

既存DBに失敗ジョブが残っている場合は、`python manage.py backfill_drawing_metadata_failure_diagnostics` で過去分の `diagnostics_json.failure` を補完する。事前確認だけ行う場合は `--dry-run` を付ける。納品監査では `scripts/audit_drawing_metadata_job_state.py` が失敗ジョブの `failure diagnostics` 欠落をブロックする。
| `reconciledAttributes` | `attribute`, `value2d`, `value3d`, `chosenValue`, `chosenMode`, `status`, `reason` | 2D/3D照合結果 | 一致、片側のみ、統合、手動上書き、競合を全属性単位で保持 |
| `conflicts` | `attribute`, `mode2dValue`, `mode3dValue`, `chosenValue`, `chosenMode`, `reason` | 2D/3D差異のうち設計レビュー対象だけ | 材質、重量、図番、図面名など、採用値を人が見るべき差異に限定する |
| `diagnosticConflicts` | `attribute`, `mode2dValue`, `mode3dValue`, `chosenValue`, `chosenMode`, `reason` | 内部品質・件数・抽出元などの診断差分 | `source_kind`、`confidence_summary`、`*_count`、`*_exists` など。JSON証跡には残すがRAG投入前レビュー対象からは外す |
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
| 2D訂正内容 | 訂正、改訂、変更、修正、REV系の注記/表文字 | `revision_note_candidates`, `revision_note_count` | 図面属性、改訂履歴確認 | 改訂番号とは別に、根拠文字・座標・印刷枠内外を保持。本文や存在フラグはタグ化しない |
| 2D特徴 | ハッチング、表面粗さ、切断線、データム、幾何公差、長穴候補、穴候補 | `geometry_feature_candidates` | 図面証拠候補 | 自動タグには採用しない。根拠ジオメトリ、件数、概要、採用除外理由を保持 |
| 2D形状・記号属性 | 表面粗さ記号数/値、断面・切断表現数、仕上げ記号数/種別、長穴/楕円候補数、穴/円候補数、候補径 | `surface_roughness_*`, `section_feature_count`, `finish_mark_*`, `slot_candidate_*`, `hole_candidate_*` | 図面属性、類似検索フィルター補助 | 印刷枠外は除外。記号や円/楕円は形状候補として保持し、用途断定はしない |
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

この fixture には、図面詳細API相当の `detailApiPayload`、2D/3Dビューワー初期表示用の `viewerBootstrap`、RAG投入用の `ragPayload`、本番タグ・属性連携候補の `knowledgeSystemPayloadPreview` を同梱する。登録、変更、削除は行わない読み取り専用の受け渡しJSONである。`viewerBootstrap.metadata.knowledgeDetail` には、固定モックではなく、ICAD抽出snapshot、訂正候補、監査ログ、創屋連携payload候補から作った補助セクション用データを含める。

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

さらに、共有済み抽出JSONをそのまま全部取り込まず、客先差と2D/3Dペアを優先して代表を選ぶ `scripts\build_icad_extract_import_manifest.py` を追加した。

```powershell
python scripts\build_icad_extract_import_manifest.py `
  --input-root output\live_extracts\shared_icad_probe_2026-07-14 `
  --input-root output\live_extracts\part_material_probe_2026-07-14 `
  --input-root output\live_extracts\mass_probe_2026-07-14 `
  --max-drawings 24 `
  --output output\souya_handoff\icad_extract_import_manifest_2026-07-15.json
```

manifestは112 JSONを確認し、24図面/43ファイルを選定した。選定後の分布は、2D/3Dペア19図面、3Dのみ5図面。客先ヒントは、ライズ5、ラップマスターウォルターズジャパン5、シブヤパッケージングシステム2、その他は SBY / NKS / ZCSET / DNPE / 宮本工業所 / 不二越などを1件ずつ含む。

manifest経由でローカルDBへ取り込み、fixtureを再生成した。ローカルDB上は35図面が登録済みだが、創屋へ渡すfixtureは実際に抽出snapshotがある図面だけを標準対象とする。抽出snapshotが無い10図面は、登録済みファイルの管理記録としては残すが、detail/viewer/RAG連携の実データ確認には使えないため除外した。

- 登録図面数: 35図面
- 創屋引き渡しfixture出力件数: 25図面
- 抽出snapshotなし除外: 10図面
- `knowledgeSystemPayloadPreview` 候補あり: 25図面
- 2D/3D両方あり: 20図面
- 契約検証: `output\souya_handoff\drawing_metadata_fixture_contract_validation_2026-07-15.json` で `valid=true`、issue 0件
- 検証内訳: 2D snapshot 20件、3D snapshot 25件、図面/製品・装置・ユニット/部品/プロジェクト各25件の読み取り専用payload
- 2D構造化セクション: 2D snapshot 20件すべてに `raw_2d_sections.v1` の6区画が揃う。契約検証スクリプトでも2D snapshotでは同セクションを必須チェックする
- 2D/3D照合: `reconciledAttributes` は全差分を保持する。`conflicts` は設計レビュー対象だけに絞り、内部品質・件数・抽出元差分は `diagnosticConflicts` へ分離する。2026-07-15 再生成fixtureではレビュー競合0件、診断差分93件。契約検証スクリプトでも診断専用キーが `conflicts` へ混入しないことをチェックする
- 代表候補数:
  - `03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd`: 図面 attrs=5/tags=2、製品 attrs=1、部品 attrs=5/tags=1、プロジェクト attrs=1
  - `217008-41J-3004.icd`: 図面 attrs=4/tags=2、製品 attrs=1、部品 attrs=7/tags=2、プロジェクト attrs=1
  - `474300AC219.icd`: 図面 attrs=5/tags=20、製品 attrs=1、部品 attrs=38/tags=20、プロジェクト attrs=1
  - `CAA5012-02434000K1R1.icd`: 図面 attrs=5/tags=9、製品 attrs=1、部品 attrs=27/tags=9、プロジェクト attrs=1

同日にローカルDjangoを `http://127.0.0.1:8001` で起動し、実HTTPでも確認した。なお、2026-07-16 時点ではユーザーが触る画面は `http://127.0.0.1:5173/` の2D・3Dビューワー統合フロントへ統一し、Django HTML は `/internal/drawing-metadata/` の内部確認画面へ退避している。

- `GET /internal/drawing-metadata/`: HTTP 200
- `GET /drawing-metadata/`: 現行通常導線では使用しない
- `GET /api/v1/drawing-metadata/registrations/`: 11件取得
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/`: `viewerBootstrap` あり
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/rag-payload/`: `schemaVersion=drawing_metadata_rag_payload.v1`
- 末尾スラッシュあり/なしの両方をAPIルーティングで受ける。フロント実装差で404にならないようにするため。

提出済みの 2D/3D ビューワー側では、初期表示情報を `GET /api/v1/drawings/{drawingId}/bootstrap` で取得する契約になっている。こちらの detail API に含めている `viewerBootstrap` と同一形状で返せるよう、読み取り専用の互換APIを追加した。

- `GET /api/v1/drawings/{drawingId}/bootstrap`: 2D/3Dビューワー互換の `DrawingBootstrapResponse`
- `GET /api/v1/drawings/{drawingId}/bootstrap/`: 末尾スラッシュありも許容
- 返却項目: `drawingId`, `title`, `version`, `defaultMode`, `availability.has2d`, `availability.has3d`, `metadata.drawingNumber`, `metadata.drawingName`, `metadata.drawingType`, `metadata.paperSize`, `metadata.status`, `metadata.owner`, `metadata.designPurpose`, `metadata.tags`
- 方針: 本番データ登録は行わず、既存ビューワーが図面詳細から起動されたときの初期表示だけを支える。2D/3Dファイルオープン処理そのものは、創屋側の既存 viewer 連携口と接続する。

2026-07-15 にローカル詳細画面へ `創屋連携・viewer/RAG 受け渡し確認` 欄を追加した。初心者でも確認できるよう、詳細API、RAG投入payload API、タグレビュー画面へのリンク、viewer初期化情報、RAG事前フィルタ、RAGランキング信号、投入前レビューを表形式で表示する。

同欄へ `本番タグ・属性 payload プレビュー` を追加した。図面、製品・装置・ユニット、部品、プロジェクトの各対象について、既存受け口、タグAPI状態、タグ候補、属性候補数、payloadキー、候補endpointを表示する。`attribute` / `attribute_option` は本番マスタIDが必要なため、プレビューでは `null` とし、`bindingStatus=needs_attribute_master_binding` として創屋確認待ちを明示する。

同じ検証用画面群の入口として、現行では `GET /internal/drawing-metadata/handoff/` を使う。これは本番ナレッジシステムへ組み込む完成UIではなく、こちら側で抽出・正規化・タグ生成・payload受け渡しを横断確認するためのローカル検証画面である。登録済み図面数、抽出済み図面数、2D/3D両方あり、payload候補あり、レビュー競合、診断差分を集計し、図面別に詳細画面、タグレビュー、viewer bootstrap API、RAG payload APIへ遷移できる。

- ローカル確認URL: `http://127.0.0.1:8001/internal/drawing-metadata/7d47aa93-de58-467d-a145-4a584cd6c52b/`
- 画面確認画像: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-metadata-handoff-viewport.png`
- DOM確認: `創屋連携・viewer/RAG 受け渡し確認`, `詳細API`, `RAG投入payload API`, `viewer 初期化情報`, `RAG 事前フィルタ`, `RAG ランキング信号`, `投入前レビュー`, `本番タグ・属性 payload プレビュー` が表示されることを確認

manifest取込後の代表図面として、2D/3D両方があり、かつpayload候補が多い `CAA5012-02434000K1R1.icd` をローカル詳細画面で見た目確認した。

- ローカル確認URL: `http://127.0.0.1:8001/internal/drawing-metadata/0e04246b-e8a2-4b46-a485-9312f6112d33/`
- 画面上部: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-top-caa5012.png`
- payloadプレビュー: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-payload-preview-caa5012.png`
- DOM/寸法確認: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-payload-preview-caa5012.metrics.json`
- 確認結果: 図面、製品・装置・ユニット、部品、プロジェクトの4対象が表示される。`登録・変更・削除は行わず` の注意文も表示される。payload表は横長の保存パス、endpoint、候補タグを扱うため、専用の横スクロール枠と折り返しを付けた。Chrome実画面ではpayloadセルの文字あふれ0件を確認した。
- 代表候補数: 図面 attrs=5/tags=9、製品 attrs=1、部品 attrs=27/tags=9、プロジェクト attrs=1。

2026-07-15 に 2D の全ビュー、レイヤー、印刷枠内外判定を確認するため、詳細画面へ `ビュー別取得状況` と `レイヤー別取得状況` を追加した。文字、寸法、図形をまとめて、ビュー別/レイヤー別に何件取れているか、印刷枠内/外/不明が何件あるかを表示する。

同日に `scripts\summarize_2d_extraction_coverage.py` を追加し、共有済み2D抽出JSONを集計した。

```powershell
python scripts\summarize_2d_extraction_coverage.py `
  --manifest output\souya_handoff\icad_extract_import_manifest_2026-07-15.json `
  --output output\souya_handoff\icad_2d_extraction_coverage_manifest_2026-07-15.json
```

代表manifest対象の集計結果:

- 2D対象: 19ファイル
- ビュー/用紙数: 12
- 印刷枠数: 2
- レイヤー数: 510
- 取得対象要素: 1,967件
- 文字: 581件
- 寸法: 63件
- 図形primitive: 1,312件
- 印刷枠内: 235件
- 印刷枠外: 344件
- 印刷枠判定不明: 1,388件
- ビュー情報なし: 17ファイル
- 印刷枠情報なし: 17ファイル
- レイヤー情報なし: 17ファイル

全量ディレクトリ確認の結果は `output\souya_handoff\icad_2d_extraction_coverage_summary_2026-07-15.json` に保存した。全量側は古い途中抽出JSONも含むため、品質判断ではなく、再抽出対象の洗い出しに使う。代表manifestでも2D情報の薄いファイルが多いため、次工程では最新抽出器で代表2Dファイルを再抽出し、`view_sheets` / `print_frames` / `layers` / `inside_print_area` が入ったJSONへ置き換える。

2026-07-15 に代表manifestの2D対象19件を最新runnerで再抽出し、旧manifestの2D JSONを置き換えた。

- 実行スクリプト: `scripts\run_manifest_2d_reextract_2026_07_15.ps1`
- 再抽出出力先: `output\live_extracts\manifest_2d_reextract_2026-07-15`
- 再抽出manifest: `output\souya_handoff\icad_extract_import_manifest_reextract_2026-07-15.json`
- 2Dカバレッジ: `output\souya_handoff\icad_2d_reextract_coverage_selected_manifest_2026-07-15.json`
- fixture: `output\souya_handoff\drawing_metadata_fixture_reextract_2026-07-15.json`

再抽出後の代表manifest対象の集計結果:

- 2D対象: 19ファイル
- ビュー/用紙数: 121
- 印刷枠数: 22
- レイヤー数: 4,845
- 取得対象要素: 23,300件
- 文字: 1,310件
- 寸法: 1,492件
- 図形primitive: 20,477件
- 印刷枠内: 3,212件
- 印刷枠外: 19,600件
- 印刷枠判定不明: 488件
- ビュー情報なし: 0件
- レイヤー未設定要素: 741件
- 印刷枠なし: 1ファイル

旧manifestでは `ビュー情報なし17ファイル`、`印刷枠情報なし17ファイル`、`レイヤー情報なし17ファイル` だったため、最新抽出器で全ビュー・印刷枠・レイヤー取得は大きく改善した。

同日さらに `SxGeomLine2D` の座標取得を見直し、scalar の `x1/y1/x2/y2` が無い線分でも `pnt1/pnt2`、`pos1/pos2`、`sp/ep`、`start/end` から開始点・終点を拾うようにした。改善前は `SxGeomLine2D` が印刷枠判定不明の大半を占めていたが、再抽出後は `unknownPrintArea=488` まで低下した。内訳分析は `output\souya_handoff\icad_2d_print_area_unknown_analysis_2026-07-15.json` に保存した。

- 分析対象要素: 23,279件
- 判定不明: 481件
- 座標欠落による不明: 481件
- 座標ありだが判定失敗: 0件
- 不明primitive型: `SxGeomHatch` 169件
- 残りは主に `SxGeomHatch` と、`Ｙ` など座標なし文字である

SXNET の `SxGeomHatch` 公開フィールドは `pattern`、`angle`、`dist`、`pitch`、`ex_name`、`ex_scale`、`type` が中心で、直接の座標または外接矩形は確認できなかった。そのため、ハッチング座標は捏造しない。raw extract には証跡として保持し、印刷枠が取得できている図面では `inside_print_area=true` と判定できた要素だけを自動タグ・検索候補へ使う。

2026-07-15 に正規化層へ上記制御を追加した。印刷枠がある図面では、`inside_print_area=null` の文字、寸法記号、溶接注記、バルーン、幾何primitiveを `part_keywords`、`spec_tokens`、図枠候補、訂正内容候補、形状特徴候補から除外する。raw の `text_tokens` や `geometry_primitives` は削除せず、後から人が確認できる証跡として残す。印刷枠が取れない図面では従来どおり `null` を保持して、情報欠落で一律に捨てない。

比較結果は `output\souya_handoff\drawing_metadata_fixture_tag_diff_unknown_filter_2026-07-15.json` に保存した。旧fixture比で、2D/3D snapshot数は45件のまま、自動タグ9件、`part_keywords` 1,031件、`spec_tokens` 1,014件、ハッチング/断面カウント169件を削減した。削除されたタグは、座標不明ハッチング由来の `図面特徴:ハッチング` と、枠外/枠不明テキスト由来のユニット・装置タグであり、図枠外データの誤反映抑止として妥当である。

同日に本番ナレッジシステムの実画面もChromeで再確認した。登録、変更、削除は行っていない。

- プロジェクト一覧: `output\knowledge_ui_screenshots_2026-07-15\30-project-list-settled.png`
- 製品・装置・ユニット一覧: `output\knowledge_ui_screenshots_2026-07-15\31-product-unit-list-settled.png`
- 部品一覧: `output\knowledge_ui_screenshots_2026-07-15\32-part-list-settled.png`
- 部品詳細: `output\knowledge_ui_screenshots_2026-07-15\01-part-detail-start-viewport.png`
- 図面一覧: `output\knowledge_ui_screenshots_2026-07-15\33-drawing-list-settled.png`
- AI検索: `output\knowledge_ui_screenshots_2026-07-15\34-ai-search-settled.png`
- 類似検索: `output\knowledge_ui_screenshots_2026-07-15\35-similar-search-settled.png`
- 図面詳細2D: `output\knowledge_ui_screenshots_2026-07-15\03-drawing-detail-2d.png`
- 図面詳細3Dエラー: `output\knowledge_ui_screenshots_2026-07-15\04-drawing-detail-3d-error.png`
- ローカル詳細: `output\knowledge_ui_screenshots_2026-07-15\05-local-detail.png`
- ローカルタグレビュー: `output\knowledge_ui_screenshots_2026-07-15\06-local-tag-review.png`

確認結果:

- 本番部品詳細には `属性情報` 欄があり、サンプルでは空表示だった。部品タグ・属性の受け口として重要。
- 本番図面一覧には、検索条件、図面タイプ、ステータス、紐づき概要が見える。タグ列は未表示。
- 本番プロジェクト一覧、製品・装置・ユニット一覧、部品一覧にもタグ列は見えない。タグを活用するなら、一覧条件・詳細属性・関連情報のどこへ反映するかを創屋と確認する。製品・装置・ユニットは実メニュー遷移で `/web/product` を確認した
- 本番AI検索はチャット履歴と質問欄が中心で、タグを直接編集する場所ではない。タグは検索前フィルタ、RAG投入payload、ランキング信号として裏側で使うのが自然。
- 本番類似検索は2D/3Dチェック、検索ファイル、類似度、図面名、用途、規格、重要度フィルタが見える。ICAD抽出タグは類似検索フィルタや重みづけ補助にも使える。
- 本番図面詳細には `タグ` と `属性情報` 欄、2D/3D切替、2Dプレビューが見える。初期連携先は引き続き図面詳細を最優先にする。
- 本番図面詳細の3D切替では `/web/public/models/test_000445.gltf` がHTMLを返し、GLTFとして読めずアプリ全体がエラー画面になった。抽出器の問題ではないが、創屋への2D/3Dプレビュー連携確認事項に含める。
- ローカル詳細画面では `CAA5012-02434000K1R1.icd` について `2Dあり`、`3Dあり`、viewerタグ、保存フォルダ、パーツ付加情報数が表示される。
- ローカルタグレビュー画面では、図面/製品・装置・ユニット/部品/プロジェクトの適用先候補、統合タグ、2Dタグ、3Dタグ、競合が確認できる。
- ローカル詳細画面の `2D構造化セクション` では、図枠、中央図面、寸法、注記、バルーン、製造記号の6行が表示される。`schema=raw_2d_sections.v1`、印刷枠内/外/判定不明、自動利用件数、短いサンプルを確認できる。証跡は `output\knowledge_ui_screenshots_2026-07-15\68-local-drawing-detail-2d-structured-sections.png`

2026-07-15 にさらに本番実画面をChromeで読み取り専用確認した。登録、変更、削除は行っていない。メニュー遷移で、統合検索の実URLは `/web/integrated_search`、類似検索の実URLは `/web/drawing/similar_search` と確認した。プロジェクト詳細はタグ/属性欄なし、製品・装置・ユニット詳細と部品詳細は `属性情報` 欄あり、図面詳細は `タグ` と `属性情報` 欄あり。

- 本番トップ: `output\knowledge_ui_screenshots_2026-07-15\70-production-home-screen.png`
- 本番統合検索: `output\knowledge_ui_screenshots_2026-07-15\78-production-integrated-search-menu-screen.png`
- 本番類似検索: `output\knowledge_ui_screenshots_2026-07-15\79-production-similar-search-menu-screen.png`
- 本番プロジェクト詳細: `output\knowledge_ui_screenshots_2026-07-15\84-production-project-detail-screen.png`
- 本番製品・装置・ユニット詳細: `output\knowledge_ui_screenshots_2026-07-15\85-production-product-detail-screen.png`
- 本番部品詳細: `output\knowledge_ui_screenshots_2026-07-15\86-production-part-detail-screen.png`
- 本番図面詳細: `output\knowledge_ui_screenshots_2026-07-15\87-production-drawing-detail-screen.png`
- ローカル診断差分表示: `output\knowledge_ui_screenshots_2026-07-15\88-local-diagnostic-conflicts-detail.jpg`

同じタグレビュー画面へ、`knowledgeSystemPayloadPreview` の対象別サマリを追加した。これにより、図面、製品・装置・ユニット、部品、プロジェクトごとに、既存受け口、タグAPI状態、タグ数、属性数、候補endpoint、属性候補、タグ候補を1画面で確認できる。創屋へ渡すJSONの見せる側の確認画面であり、本番保存操作は行わない。

- ローカルタグレビューpayload確認: `output\knowledge_ui_screenshots_2026-07-15\89-local-tag-review-payload-targets.jpg`

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
        "label": "表面粗さ",
        "classification_label": "表面粗さ記号あり",
        "searchable_tag": false,
        "tag_adoption_status": "excluded",
        "tag_adoption_reason": "製造記号や形状候補の存在だけでは検索・分類タグとして粗いため、図面証拠として保持し、自動タグには採用しません。",
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
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を採用候補として示し、確定値にはしません。"
    }
  ],
  "conflicts": [
    {
      "attribute": "weight_value",
      "mode2dValue": "2.1kg",
      "mode3dValue": 2.08,
      "chosenValue": 2.08,
      "chosenMode": "3d",
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を採用候補として示し、確定値にはしません。"
    }
  ],
  "diagnosticConflicts": [
    {
      "attribute": "confidence_summary",
      "mode2dValue": "medium",
      "mode3dValue": "high",
      "chosenValue": "high",
      "chosenMode": "3d",
      "reason": "内部品質・件数・抽出元差分のため、自動タグ/RAG投入前レビュー対象からは除外しました。"
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
- Gemini API低温度JSON分類は2D抽出ジョブへ組み込み済み。APIキー未設定時はスキップし、API失敗時は `title_block_llm_classification_failed` warning として記録する。既存候補値の欄名分類補助に限定し、ルール抽出済みの属性は上書きしない。2026-07-15 に `backend\.env` よりOS環境変数が優先されて古いキーを読んでいた問題を修正し、実API疎通を確認した。`gemini-flash-latest` を主モデル、`gemini-3.1-flash-lite` / `gemini-3.5-flash` をフォールバックにして、代表manifest上位5件すべてで分類応答を取得した。結果は `output\live_extracts\title_block_llm_probe_2026-07-14\gemini_probe_after_parse_fallback_2026-07-15.json` に保存し、評価JSONでは classification precision 1.0000、positive recall 0.5000、guardrail safety rate 1.0000、accepted uplift 0 を確認した。運用監査は `scripts/audit_llm_title_block_guardrails.py` で行い、印刷枠外候補をGemini分類で属性採用していないことを確認する
- 長穴、穴数、断面、表面粗さ値は PoC で属性化済み。次は実サンプル横断で、円/楕円を穴・長穴として断定できる条件を詰める
- 2D/3D照合結果の採用値、差異、要確認理由は PoC 画面表示まで実装済み。次は本番API/fixture名確定後の項目名合わせ

## 10. 共有39件の最終受け渡し状況

2026-07-15 に、ユーザーから共有された客先横断39件を固定manifestとして再整理し、ローカルDB、fixture、製品・装置・ユニット／部品画面へ反映した。本番ナレッジシステムへの登録、変更、削除は行っていない。

### 10.1 固定manifestとfixture

- manifest: `output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json`
- fixture: `output\souya_handoff\drawing_metadata_fixture_all_shared_2026-07-15.json`
- fixture検証: `output\souya_handoff\drawing_metadata_fixture_all_shared_validation_2026-07-15.json`
- サンプル完了台帳: `output\souya_handoff\icad_shared_sample_completion_2026-07-15.json`
- 対象: 39図面、抽出JSON 78件（各図面に2D/3D各1件）
- 3D snapshot: 39/39
- 2D snapshot: 39/39
- 契約検証: `valid=true`、issue 0件
- 読み取り専用payload: 図面、製品・装置・ユニット、部品、プロジェクトを各39件
- 属性候補数: 図面158、部品370、製品・装置・ユニット43、プロジェクト43
- タグ候補数: 図面168、部品116、製品・装置・ユニット2、プロジェクト2

### 10.2 3D構成からの実エンティティ生成

3D構成ノードに `nodeId`、`parentNodeId`、`depth`、`childCount`、`entityKind` を付ける。ただし、子を持つだけではサブアセンブリとは判定しない。`subassembly` は `is_external`、`ref_model_name`、`ref_model_path` など外部参照の根拠がある中間ノード、または手動確定がある場合だけ扱う。末端ノードは内部構成診断上の部品として集計するが、ナレッジシステムへの登録単位は1 ICD = 1件である。

| API | 用途 |
| --- | --- |
| `GET /api/v1/knowledge-entities?target=product` | アセンブリ／サブアセンブリ一覧 |
| `GET /api/v1/knowledge-entities?target=part` | 末端部品一覧 |
| `GET /api/v1/knowledge-entities/{entityId}` | 属性、タグ、根拠、競合、関連情報、レビュー状態を含む詳細 |

エンティティIDは図面IDと3DノードIDから安定生成する。同名部品が複数箇所に存在しても、階層位置の異なるノードとして扱う。

### 10.3 レビューと確定状態

抽出候補は表示しただけで確定扱いにしない。2D/3D snapshot単位に `pending`、`confirmed`、`needs_correction` を保持し、再抽出または手動上書き時は `pending` に戻す。レビュー操作はローカル監査ログへ記録する。

| API | 用途 |
| --- | --- |
| `PATCH /api/v1/drawing-metadata/registrations/{drawingId}/review` | 2Dまたは3D候補を確定／要手直しへ変更 |
| `GET /api/v1/drawing-metadata/settings/tag-automation` | AI、抽出対象、採用ルールの管理設定を取得 |
| `PUT /api/v1/drawing-metadata/settings/tag-automation` | ローカル管理設定を更新 |

Gemini APIキーは設定値そのものを返さず、設定済みかどうかだけを返す。本番DB向けendpointは実装せず、創屋へはfixtureとAPI契約を渡す。

### 10.4 2D再抽出の状態と理由

39件を同一条件で再抽出した。途中で終了コード1が連続した際は、Runnerの例外チェーンとstack traceを出すようにして、`SxFileModel` 生成時の `sxnet.SxException: コマンド実行中の為処理できません` まで原因を特定した。SXNET HTMLの `SxSys.cancel()` と `SxSys.getCommand()` を確認し、診断用の `cancel` / `clear-command` コマンドも追加したが、孤立したコマンド状態は解消しなかった。

ICADへ通常の終了要求を送り、旧V8L2形式からV8L3形式への保存確認には「いいえ」を選んで原本を変更せず終了した。その後クリーンに起動し直して全39件を再実行した結果は次のとおりである。強制終了、原本保存、創屋本番DB操作は行っていない。

抽出器の自動起動leaseも同じ安全終了へ統一した。通常終了できない場合に `Process.Kill()` していた処理は廃止し、保存確認の「いいえ」を特定できた場合だけ押す。安全終了を完了できない場合は、強制終了せずICADを起動状態のまま残してエラーを出す。明示的な保守確認には次のコマンドを使用できる。

```powershell
src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe `
  shutdown-icad `
  --timeout-seconds 20
```

- 最新2D抽出成功: 39/39
- 2D要素あり: 31件
- 2Dコンテナ／ビュー／レイヤーはあるが検査可能な2D要素なし: 8件
- 最新3D抽出利用可能: 39/39
- 共有元ファイル欠落: 0件
- 未解決: 0件

「2D要素なし」8件は抽出失敗ではない。VS/ビューとレイヤー情報は取得できた一方、文字・寸法・図形primitive・印刷枠が0件だったため、内容を捏造せずその状態を記録している。

全39件の2Dカバレッジは `output\souya_handoff\icad_2d_extraction_coverage_all_shared_2026-07-15.json` に保存した。全ビュー210、印刷枠32、レイヤー9,945、検査可能要素30,055、文字1,752、寸法2,404、図形primitive 25,853を取得した。要素のビュー未所属は0件、印刷枠内5,088、枠外23,849、判定不明1,118である。判定不明とレイヤー未所属は証拠として保持し、自動タグ採用では印刷枠内を優先する。

当初の参照先で見つからなかった `36555211A01.icd` と `32791729A01.icd` は、同じ共有案件内の移動後パスを特定した。manifestとローカルDBの保存パスを更新し、最終台帳では共有元ファイル欠落0件である。

移動後パスの再紐付けには、同名図面がローカルDBに1件だけ存在する場合に限って使える明示オプションを追加した。同名図面が複数ある場合は処理を中断し、推測で付け替えない。

```powershell
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --filename 32791729A01.icd `
  --filename 36555211A01.icd `
  --rebind-moved-source
```

全件再取込時は、manifestの2D/3Dを分けて再現できる。移動元再紐付けは同名図面が一意の場合だけ許可し、曖昧なら中断する。

```powershell
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --manifest-mode 2d
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --manifest-mode 3d
```

### 10.5 創屋との責任境界

| 領域 | こちら | 創屋 |
| --- | --- | --- |
| ICAD 2D/3D/パーツ付加情報抽出 | 実装・検証 | 対象外 |
| 正規化、照合、候補生成、根拠・競合・信頼度 | 実装・fixture提供 | 受入確認 |
| 図面管理の抽出・レビュー導線 | ローカル統合版を提供 | 本番ナレッジシステムへ移植 |
| 図面／製品・装置・ユニット／部品への表示 | ローカル統合版とAPI契約を提供 | 本番UI・本番マスタIDへ接続 |
| 本番DB登録・更新・削除 | 実施しない | 創屋が仕様合意後に実装 |
| 本番画面・フロント資産確認 | 読み取り専用のみ | 変更管理 |
