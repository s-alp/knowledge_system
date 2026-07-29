# CADタグ・属性抽出 抽出元カタログと具体例（創屋様向け）

- 作成日: 2026-07-28
- 版: r2（創屋様への供給仕様確定版）
- 作成: 株式会社アルパイン設計事務所
- 文書状態: 確定

---

## 0. この資料が答えること

本資料は、当社が供給する「CADからのタグ・属性抽出および自動タグ付与」の確定仕様を示します。

| 確定事項 | 記載箇所 |
|---|---|
| どこから何を抜き出すか | 2章（抽出元カタログ）、3章（正規化後の属性） |
| 文字列・属性からどのタグを付与するか | 4章（タグ生成ルール・辞書） |
| 実データで何が得られたか | 5章（実ICAD 39件・共有DXF 38件の実測） |
| どのソースを切り出して供給するか | 6章（モジュール境界・JSON入出力） |
| STEP/DXF経路の情報差 | 7章（変換実測と限界） |

---

## 1. 全体像

### 1.1 処理の流れ

```
[抽出] → [正規化] → [タグ生成] → [レビュー] → [ナレッジシステムへ連携]
  C#      Python      Python       画面        創屋様側で実装
```

- 抽出器は意味付けをせず、生の値（`raw_extract`）だけを出します。
- 正規化層（Python）が `canonical_attributes` へ整形します。
- タグ生成層（Python）が `derived_tags` を作ります。
- 抽出不能な項目は空配列または `null` にし、推測値は入れません。

### 1.2 3つの入力経路

| 経路 | 入力 | 抽出器 | ICAD本体 | 取得できる情報量 |
|---|---|---|---|---|
| A | ICAD `.icd` 正本 | C# + SXNET | 必要 | 最大（材質・質量・部品階層・2D注記まで） |
| B | ICADから変換したSTEP / DXF | Python汎用抽出器 | 変換時のみ必要 | 中（部品名・階層・レイヤー・文字） |
| C | 客先支給などの既存STEP / DXF | Python汎用抽出器 | 不要 | 中 |

経路Bと経路Cは同じ抽出器を使います。経路B・Cでは**ICAD本体がなくても抽出処理そのものは動きます**。

### 1.3 「タグ付与」の定義と担当境界

本資料における「タグ付与」は、抽出結果を正規化し、検索・分類用のタグを `derived_tags` として生成して、取得元・根拠・信頼度・採用理由を添えたJSONへ格納するところまでを指します。

| 処理 | 担当 | 成果物 |
|---|---|---|
| ICAD / STEP / DXFからの生データ抽出 | 当社供給モジュール | `raw_extract` |
| 共通属性への正規化 | 当社供給モジュール | `canonical_attributes` |
| 文字列・属性・辞書によるタグ自動付与 | 当社供給モジュール | `derived_tags` |
| 創屋様ナレッジシステムのDB/APIへの登録 | 創屋様 | 本番タグ・属性レコード |

したがって、当社の供給範囲は**抽出だけではなく、自動タグ付与済みJSONの生成まで**です。本番ナレッジシステムへの登録処理は、創屋様のAPI・DB仕様へ接続する実装として分離します。

---

## 2. 抽出元カタログ（どこから何を抜くか）

### 2.0 全経路共通のファイル出所

ファイル出所はCAD内部から推測するのではなく、抽出ジョブへ渡された入力ファイルを正として保持します。ICAD、STEP、DXFの全経路で同じ扱いです。

| 取得対象 | raw_extract / 入力 | 正規化先 | 主な用途 |
|---|---|---|---|
| フルパス・格納フォルダ | `source_file.*` | `source_full_path`, `source_directory_path` | 出所表示、監査証跡、パス辞書照合 |
| ファイル名・拡張子 | `source_file.*` | `source_file_name`, `source_file_stem`, `source_extension` | 図面識別、形式判定、検索トークン生成 |
| 入力形式・図面種別 | `source_file.*` | `source_format`, `source_kind` | ICAD / STEP / DXF、2D / 3Dの処理経路選択 |
| パス分解トークン | 上記のパス・フォルダ・ファイル名を分解 | `source_path_tokens` | 客先・案件・装置辞書の照合候補 |

`source_path_tokens` は、モデル情報、図面内文字、DXFレイヤー、パーツ付加情報等と合わせて検索トークン列（`part_keywords`）へ入れます。パス文字列を無条件にタグ化するのではなく、登録済み辞書と一致し、採用条件を満たした場合だけ `客先:`、`案件:`、`装置:` タグ候補へ上げます。

### 2.1 ICAD 3D（経路A）

| 抽出元 | SXNET根拠 | raw_extract | 正規化先 |
|---|---|---|---|
| モデル名・格納フォルダ・コメント | `SxModel.getInf()` → `SxInfModel.name/path/comment` | `model_info.*` | `model_name`, `model_path`, `model_comment` |
| パーツ階層 | `SxWF.getInfPartTree()` | `parts[].tree_path` | `part_tree_paths` |
| パーツ名・コメント | `SxInfPart.name/comment` | `parts[].name/comment` | `part_names`, `part_comments` |
| 外部参照・ミラー・未解決参照 | `SxInfPart.is_external/is_mirror/is_unloaded` | `parts[].is_*` | `external_part_exists` ほか |
| 参照図面名・パス | `SxInfPart.ref_model_name/path` | `parts[].ref_model_*` | `ref_model_names`, `ref_model_paths` |
| 材質（全体・部品単位） | `SxEnt.getInfMaterialList()`, `SxEntPart.getInfMaterialList()` | `materials[]`, `parts[].materials[]` | `material_ids`, `material_names`, `material_keywords`, `part_material_candidates` |
| 質量・重量・体積・面積・密度 | `SxEnt.getMass()` → `SxInfMass` | `mass_properties.*` | `mass_value`, `weight_value`, `volume_value`, `area_value`, `density_value` |
| 重心・慣性モーメント | `SxInfMass.pos`, `inf_global_moment` ほか | `mass_properties.*_moment` | `center_of_gravity`, `global_moment`, `inertia_moment_candidates` |
| トップパーツ付加情報 | `SxWF.getInfExTopPart()`, ルートの `SxInfPartTree.ex_inf` | `top_part.ex_info`, `top_part.ex_info_fields` | `top_part_ex_info`, `part_ex_info_fields`, `part_ex_info_tokens` |
| 各構成パーツの付加情報 | 各ノードの `SxInfPartTree.ex_inf` | `parts[].ex_info`, `parts[].ex_info_fields` | パーツ階層別の `part_ex_info_fields`, `part_ex_info_tokens` |

パーツ付加情報はトップパーツだけに限定しません。パーツツリーを再帰走査し、各構成パーツの付加情報を階層パスと対応付けて保持します。キー・値に分解できた項目は、PRFX、ユニット番号、材質、熱処理、硬度の候補抽出に使用し、分解できない生文字列も検索・監査用トークンとして残します。

### 2.2 ICAD 2D（経路A）

| 抽出元 | SXNET根拠 | raw_extract | 正規化先 |
|---|---|---|---|
| ビューシート名・尺度・種別 | `SxModel.getGlobalVS()`, `SxInfVS` | `view_sheets[]` | `model_view_sheet_count`, `scale_candidates` |
| 出図範囲枠・用紙サイズ | `SxInfPrint` | `print_frames[]` | `paper_size`, 印刷枠内外判定 |
| 文字・注記 | 文字要素 | `texts[]` | `text_tokens`, `label_texts` |
| 図枠のラベルと値 | 同一文字要素の同じ行／次行で判定（座標は証跡のみ） | `texts[]` | `title_block_candidates` → `title_block_fields` |
| 寸法 | 寸法要素 | `dimensions[]` | `dimension_values`, `dimension_symbols` |
| 公差・幾何公差 | 公差要素 | `tolerances[]` | `tolerance_candidates` |
| 溶接記号・注記 | 溶接要素 | `weld_notes[]` | `weld_note_candidates` |
| バルーン | バルーン要素 | `balloons[]` | `balloon_candidates` |
| 面粗さ・仕上げ記号 | シンボル要素 | `geometry_primitives[]` | `surface_roughness_values`, `finish_mark_types` |
| 切断線・矢視・ハッチング | 図形要素 | `geometry_primitives[]` | `curve_section_candidates`, `cut_line_count`, `hatch_or_section_count` |
| 穴・長穴候補 | 図形要素 | `geometry_primitives[]` | `hole_candidate_count`, `slot_candidate_count` |
| レイヤー | レイヤー情報 | `layers[]` | 判定の補助 |

別文字要素間の汎用的な座標ペアリングは行いません。客先・図枠ごとの差による誤対応を避けるため、座標は表示・候補レビュー・監査証跡として保持し、自動属性確定には使用しません。

**重要**: 図番・図面名・担当者・承認者・日付・材質・重量・表面処理・塗装指示・PRFX・ユニット番号は、SXNETの固定フィールドとしては存在しません。文字・注記・図枠解析で抽出する対象です。会社ごとの図枠差が大きいため、`title_block_fields` は固定列ではなく key-value 候補として持ち、採用条件を通ったものだけを確定値に上げます。

### 2.3 STEP（経路B・C）

| 抽出元 | raw_extract | 正規化先 |
|---|---|---|
| ファイルパス・ファイル名 | `source_file.*` | `source_path_tokens`, `source_file_name` |
| ヘッダ（`FILE_NAME`, `FILE_DESCRIPTION`） | `model_info.name/comment` | `model_name`, `model_comment` |
| `PRODUCT` / `PRODUCT_DEFINITION` | `step_products[]` | `step_product_names` |
| `NEXT_ASSEMBLY_USAGE_OCCURRENCE` | `step_assembly_relationships[]` | `step_assembly_relationship_count`, `parts[].tree_path` |
| 文字列中の材質パターン | `materials[]` | `material_keywords` |

#### STEP部品階層の扱い

- STEPの部品階層は、STEP内に保存されたアセンブリ、構成要素、配置の親子関係を表す。ICADでの「内部パーツ」「外部参照パーツ」という作成元の区分を表すものではない。
- したがって、STEPの `PRODUCT` / `NEXT_ASSEMBLY_USAGE_OCCURRENCE` だけから `external_part_count`、`internal_part_count`、BOM相当の部品数を算出しない。製品・アセンブリ・部品の登録先判定にも使用しない。
- 内部／外部の区分を取得できない場合は、外部パーツ数を `0` とせず `null`（不明）とする。`0` は「外部パーツが存在しない」と確認できた場合にだけ使用する。
- STEP階層は、3Dビューワーのツリー表示、親子関係を使った検索補助、同一構成要素の配置数確認、構成単位での材質・質量特性の集計に限って利用する。件数を保持する場合は、BOM部品数と混同しない `step_component_occurrence_count` 等のSTEP専用項目とする。
- 複数ファイルSTEP等で外部ファイル参照を検出できる場合も、ICADの外部参照パーツと同義とは断定しない。`step_external_reference_count` 等の別項目に保持し、`external_part_count` へ自動変換しない。
- 製品名・部品名が `Assembly` や `prt0` のような変換時の汎用名になっている場合、階層は表示・監査用の低信頼情報として扱い、案件名・装置名・部品名の確定根拠にはしない。

### 2.4 DXF（経路B・C）

| 抽出元 | raw_extract | 正規化先 |
|---|---|---|
| `TEXT` / `MTEXT` / `ATTRIB` / `ATTDEF` | `texts[]` | `text_tokens`, `title_block_candidates` |
| `INSERT` + `ATTRIB` のブロック参照 | `block_references[].attributes[]` | `dxf_block_references`, `dxf_block_attribute_tokens` |
| `DIMENSION` の表示値候補 | `dimensions[]` | `dimension_count`, `dimension_values` |
| `DIMSTYLE` / `ACAD:DSTYLE` / 寸法文字の公差信号 | `dimensions[].has_tolerance`, `upper_tol`, `lower_tol` | `dimension_tolerance_count`, `dimension_tolerance_values` |
| `TOLERANCE` | `tolerances[]` | `geometric_tolerance_count`, `tolerance_candidates` |
| 溶接キーワードを含む `TEXT` / `MTEXT` | `weld_notes[]` | `weld_instruction_count`, `weld_types`, `weld_note_candidates` |
| `LINE` / `CIRCLE` / `ARC` / `ELLIPSE` / `LWPOLYLINE` / `POLYLINE` / `SPLINE` / `HATCH` | `geometry_primitives[]` | 形状特徴候補 |
| 対応要素で使用されたレイヤー | `layers[]` | `dxf_layers` |

### 2.5 主要な取得値とタグ・属性への接続

| 取得元 | 正規化・候補化 | タグへ上げるもの | 属性・証跡として保持するもの |
|---|---|---|---|
| ファイルパス・フォルダ・ファイル名 | `source_path_tokens` → `part_keywords` | 辞書一致した客先・案件・装置 | フルパス、フォルダ、ファイル名、拡張子、形式 |
| モデル名・コメント・参照モデル名 | モデル／部品の検索トークン | 辞書一致した客先・案件・装置・部品名 | モデル情報、参照モデル名・参照パス |
| トップ＋各パーツの付加情報 | `part_ex_info_fields`, `part_ex_info_tokens` | PRFX、ユニット番号、正式材質、熱処理、硬度尺度、辞書一致した客先・案件・装置 | パーツ階層別のキー・値、生文字列、採用根拠 |
| 3D材質・質量API | 材質候補、質量特性 | 正式材質 | 材質ID、比重、質量、体積、面積、密度、重心、慣性モーメント |
| 2D文字・図枠・DXFブロック属性 | 図枠候補、製造指示候補 | 客先、案件、装置、メーカー、表面処理、塗装、熱処理、硬度尺度、規格 | 図番、図面名、担当者、承認者、日付、座標、印刷枠内外 |
| 寸法・公差・幾何公差・溶接 | 種別判定、存在判定 | 寸法／公差／幾何公差／溶接の有無、明示判定できた種別 | 寸法値、公差値、記号の生値、候補座標 |
| 穴・長穴・切断線・ハッチング等 | 形状特徴候補 | 原則タグ化しない | 件数、寸法候補、レイヤー、ビュー／断面参照 |

---

## 3. 正規化後の属性キー（canonical_attributes）

正規化後は固定スキーマの辞書になります。値が取れなかったキーは `null`、`0`、空配列のまま残します（「取れなかった」ことも情報として残す方針）。

主なキーを分類して示します。

**図面識別**
`drawing_number`, `drawing_name`, `revision`, `drawing_size`, `paper_size`, `scale`, `document_kind`

**担当・日付**
`designer`, `checker`, `approver`, `drawing_date`, `created_date`, `checked_date`, `approved_date`, `revision_date`

**分類**
`customer_name`, `project_name`, `equipment_name`, `equipment_category`, `module_name`, `prfx`, `unit_number`, `owner`, `status`

**ファイル出所**
`source_full_path`, `source_directory_path`, `source_file_name`, `source_file_stem`, `source_extension`, `source_path_tokens`, `source_format`, `source_kind`

**モデル情報**
`model_name`, `model_comment`, `model_path`, `model_is_read_only`, `model_view_sheet_count`, `model_work_plane_count`

**質量特性（3D）**
`mass_value`, `weight_value`, `volume_value`, `area_value`, `density_value`, `center_of_gravity`, `global_moment`, `gravity_moment`, `main_moment`, `inertia_moment_candidates`, `mass_probe_status`, `mass_unit_name`, `mass_element_count`

**材質**
`material`, `material_ids`, `material_names`, `material_specific_gravities`, `material_keywords`, `unresolved_material_keywords`, `part_material_candidates`, `material_probe_status`

**部品構成**
`part_names`, `part_comments`, `part_tree_paths`, `part_name_candidates`, `part_ex_info_fields`, `part_ex_info_tokens`, `ref_model_names`, `ref_model_paths`, `external_part_exists`, `mirror_part_exists`, `unresolved_part_exists`, `referenced_2d_part_count`, `referenced_2d_trusted_part_count`

**2D注記・図枠**
`title_block_fields`, `title_block_candidates`, `revision_note_candidates`, `text_tokens`, `label_texts`, `raw_2d_sections`

**2D寸法・記号**
`dimension_values`, `dimension_symbols`, `tolerance_candidates`, `weld_note_candidates`, `balloon_candidates`, `surface_roughness_values`, `finish_mark_types`, `geometry_feature_candidates`, `view_reference_candidates`, `curve_section_candidates`, `hole_candidate_count`, `hole_candidate_diameters`, `slot_candidate_count`, `slot_candidate_dimensions`, `cut_line_count`, `hatch_or_section_count`, `section_feature_count`

**加工・処理**
`surface_treatment`, `surface_treatment_tokens`, `paint`, `heat_treatment_keywords`, `heat_treatment_evidence`, `hardness_spec_candidates`, `hardness_spec_values`, `process_keywords`

**キーワード**
`part_keywords`, `maker_keywords`, `spec_tokens`, `inspection_keywords`, `change_keywords`, `issue_keywords`

**STEP/DXF固有**
`step_products`, `step_product_names`, `step_assembly_relationships`, `step_assembly_relationship_count`, `dxf_layers`, `dxf_block_references`, `dxf_block_attribute_count`, `dxf_block_attribute_tokens`

**抽出メタ**
`extraction_status`, `ocr_used`, `confidence_summary`, `normalizer_version`

---

## 4. 自動タグの生成ルール

### 4.1 タグの種類

`canonical_attributes` から、以下のタグを生成します。

| タグ接頭辞 | 生成元の属性キー | 確度 |
|---|---|---|
| `客先:` | `customer_name` | high |
| `案件:` | `project_name` | high |
| `装置:` | `equipment_category` | high |
| `寸法あり` | `dimension_count` | high |
| `寸法公差あり` | `dimension_tolerance_count` | high |
| `幾何公差あり` | `geometric_tolerance_count` | high |
| `溶接指示あり` | `weld_instruction_count` | high |
| `溶接:すみ肉` / `溶接:全周` | `weld_types` | medium |
| `メーカー:` | `maker_keywords` | medium |
| `材質:` | `material_keywords`, `title_block_fields.material` | medium |
| `表面処理:` | `surface_treatment_tokens`, `title_block_fields.surface_treatment` | medium |
| `塗装:` | `paint_instruction_tokens`, `title_block_fields.coating_instruction` | medium |
| `熱処理:` | `heat_treatment_keywords` | medium |
| `硬度:HRC` / `硬度:HV` | `hardness_spec_values` | medium |
| `PRFX:` | `prfx_candidates`, `title_block_fields.prfx` | medium |
| `ユニット:` | `unit_number_candidates`, `title_block_fields.unit_number` | medium |
| `規格:` | `spec_tokens` のうち辞書一致語（現状 `SES` のみタグ化） | medium |

各タグには `source`（生成元キー）、`evidence`（根拠パス）、`confidence`、`reason`（日本語の採用理由）、`tag_rule_version` が付きます。根拠なしのタグは作りません。

なお `spec_tokens` は、2Dでは図面内の文字トークンと公差テキストをまとめた生の集合です（実例では1図面で112件）。この集合そのものをタグにするのではなく、その中の辞書一致語（現状は `SES` のみ）だけを `規格:` タグにしています。

### 4.2 辞書

タグ変換の辞書はDB化済みで、画面（システム設定 > タグ辞書管理）と `/admin` から編集できます。初期辞書の規模は以下です。

| 辞書 | 初期エントリ数 | 例 |
|---|---|---|
| 客先 | 3 | コマツ小山、広島アルミ、澁谷工業 |
| 装置カテゴリ | 30 | ガントリー、治具、ロボット、コンベア、シュート、架台、制御盤 ほか |
| メーカー | 40 | SMC、ミスミ、オムロン、キーエンス、THK、NSK、NTN ほか |
| 材質分類 | 68 | SS400、SUS304、S45C、A5052P、FC300 ほか |
| 熱処理 | 20 | 焼入れ、調質、浸炭、窒化、高周波焼入れ ほか |
| 規格 | 7 | SES、JIS、ISO、DIN、ANSI、幾何公差、溶接記号 |
| 部品名 | 22 | PLATE、COVER、BRACKET、SHAFT、GUIDE ほか |

案件辞書は初期エントリ0件で、画面／`/admin` からの登録が正本です。照合対象はファイルパスのトークンだけでなく、モデル情報・図面内文字・DXFレイヤー等を合成した検索トークン列（`part_keywords`）です。客先辞書が3件と少ないのは検証優先で絞っているためで、運用開始時には実運用の客先を登録して増やす想定です。

### 4.3 タグ化するもの／属性保持に留めるもの

**タグ化する**: 客先、案件、装置カテゴリ、寸法の有無、寸法公差の有無、幾何公差の有無、溶接指示の有無、明示判定できた溶接種別（すみ肉・全周）、メーカー、正式材質、表面処理、塗装、熱処理、硬度尺度（HRC・HV）、PRFX、ユニット番号、明確な規格識別子

**属性として保持し、原則タグ化しない**: 寸法値、公差値、溶接記号の生値、硬度の数値、バルーン、穴・長穴・切断線・ハッチング等の形状特徴、質量・体積・重心・慣性モーメント

理由は、存在するだけでタグにすると検索ノイズが大きくなるためです。これらは図面レビューやRAG投入時の属性・根拠として保持します。

---

## 5. 具体例（実ICADでの実測）

### 5.1 全体の実測

共有いただいた実ICAD **39件**を抽出・正規化・タグ生成まで通した結果です（2026-07-17 時点、`output/souya_handoff/drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json`）。

- 39件すべてで 2D snapshot / 3D snapshot の両方を保存済み、未抽出0件。
- 部品名（`part_names`）は 39/39 件で取得。
- 質量・重量（`mass_value` / `weight_value`）は 38/39 件で取得。
- 材質（`material_keywords`）は 33/39 件で取得。
- 生成されたタグの内訳（上位）:

| タグ | 件数 |
|---|---|
| `材質:SS400` | 13 |
| `材質:SUS` | 13 |
| `材質:SUS304` | 12 |
| `メーカー:SMC` | 4 |
| `材質:ねずみ鋳鉄` | 4 |
| `材質:SUS304B` / `材質:SUS316` / `材質:SPCC` / `材質:A5052P` / `材質:S45C` / `材質:FC300` | 各3 |
| `規格:SES` | 2 |
| `客先:澁谷工業` | 1 |
| `装置:治具` | 1 |
| `塗装:ﾊ仕様書ﾆﾖﾙ` | 1 |

材質タグは安定して出ますが、`客先` / `装置` タグが少ないのは、この測定時点の客先辞書が3件しか入っていなかったためです（辞書のDB化は2026-07-17）。辞書を実運用の語彙で拡充すれば増える性質のもので、抽出ロジックの限界ではありません。

### 5.2 実ファイル別の具体例

以下は実ICADファイルに対する実際の出力です（値は加工していません）。

**例1: 客先タグがパスから確定したケース**

```
ファイル : U8105111315.icd
パス     : J:\SBY\アイソレータ\210126_エーザイ_アイソレータ_RAA4844\作業フォルダ\開閉扉\U8105111315.icd
タグ     : 客先:澁谷工業 / 材質:SUS304 / 材質:SUS / 規格:SES
属性     : customer_name="澁谷工業", mass_value=0.18021418, weight_value=1.7672974,
           material_keywords=["SUS304","SUS"], part_names=["U81051113150"]
```

**例2: 装置カテゴリが確定し、購入品メーカーも拾えたケース**

```
ファイル : XH30-A08001-R03-JP_ロードカップ部改造.icd
パス     : J:\ZCSET\300P_210312\作業\2_ロードカップ部\XH30-A08001-R03-JP_ロードカップ部改造.icd
タグ     : 装置:治具 / メーカー:SMC / 材質:SUS316 / 材質:PVC / 材質:PPS / 材質:PTFE /
           材質:A5052P / 材質:SUS304 / 材質:SUS / 材質:NBR / 材質:POM
属性     : equipment_category="治具", mass_value=4.75944799, weight_value=46.67424068,
           part_names 108件（"＠リフト部", "CSP300R-8012-00_ノズルブラケット-1", "Oリング(S190)" ほか）
           unresolved_material_keywords=["75"]  ← 材質と断定できなかった値は別枠に隔離
```

**例3: 大規模アセンブリ（部品189件）**

```
ファイル : 474300AC219.icd
パス     : \\HONSYA-FILE01\data_cad3d\SBY\CAP\260527_AAM6351_アイリスオーヤマ_宮本様\474300AC219.icd
タグ     : メーカー:SMC / 材質:SUS304 / 材質:PET / 材質:H-PVC / 材質:NBR / 材質:EPDM /
           材質:PP / 材質:AU / 材質:SUS316 ほか計19タグ
属性     : mass_value=17.7113085, weight_value=173.68860346,
           material_keywords 18種、part_names 189件
           unresolved_material_keywords=["ZZZ"]
```

**例4: 規格タグと面粗さ・公差が拾えたケース**

```
ファイル : TR1D9K99027.icd
パス     : J:\シブヤパッケージングシステム\25_9R_膨潤パレットアキューム部\...\部品図(新規、訂正)\9K\TR1D9K99027.icd
タグ     : 材質:A5000 / 材質:SUS304 / 材質:A1000 / 材質:SUS / 規格:SES
属性     : mass_value=2.15703985, weight_value=21.15333481
           spec_tokens 112件（"Ra 6.3", "粗級", "中級", "±4", "±8", "±2" ほか）
```

**例5: 塗装指示が図枠から拾えたケース**

```
ファイル : 03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd
パス     : J:\アースエンジニアリング\251216_ツネイシカムテックス\...\AR05-A05-B04_No.2 F-FスクリーンスクリーンSシュート組立図\...
タグ     : 材質:SS400 / 塗装:ﾊ仕様書ﾆﾖﾙ
属性     : mass_value=11.66198417, weight_value=114.36499708,
           material_keywords=["SS400"], part_names=["03_20K03379P00_...", "溝形鋼_100*50*5*7.5"]
```

### 5.3 具体例から読み取れる特性

- **パスは強力な情報源**です。客先・案件・装置は図面内の文字よりフォルダ構成から確定できるケースが多く、`source_path_tokens` を含む検索トークン列（`part_keywords`）を辞書照合しています。
- **材質は3Dの材質APIから安定して取れます**。ただし `ZZZ` `CDQ` `75` のような、材質と断定できない値が混ざります。これらは `unresolved_material_keywords` に隔離し、タグにはしません。
- **質量・重量は3Dからほぼ確実に取れます**（38/39）。
- **半角カナ・機種依存文字がそのまま入ります**（`ｼｭｰﾄﾍﾞｰｽ`, `ﾊ仕様書ﾆﾖﾙ`）。表示・検索の正規化方針は要すり合わせです。

---

## 6. タグ・属性抽出ソースの切り出し範囲

タグ・属性抽出から自動タグ付与までを、ナレッジシステム本体から独立して供給します。モジュール境界は以下で確定します。

### 6.1 C#側（ICAD抽出コア）

独立ソリューション（`IcadExtraction.sln`、約4,700行）としてそのまま渡せます。ナレッジシステム本体への依存はありません。

| プロジェクト | 役割 |
|---|---|
| `IcadExtraction.Contracts` | 入出力のデータ契約（JSONスキーマ相当） |
| `IcadExtraction.SxNet` | SXNET経由の2D/3D抽出、材質・質量プローブ、STL/STEP/DXF出力 |
| `IcadExtraction.Runner` | CLIエントリ。`extract` / `extract-batch` / `detect` / `probe-2d-print` / `convert-cad` / `probe-cad-export-types` / `cancel` / `clear-command` / `shutdown-icad` / `self-check` の10コマンド |

インターフェースは **`1図面 = 1回のプロセス呼び出し`、入出力はJSONファイル**です。呼び出し側の言語を選びません。

### 6.2 Python側（正規化・タグ生成コア）

以下6ファイルが正規化・タグ生成の本体です。納品時はDjango依存を除去し、単体Pythonパッケージへ再配置します。

| ファイル | 行数 | 役割 | 外部依存 |
|---|---|---|---|
| `services/normalization.py` | 2,020 | `raw_extract` → `canonical_attributes` | `settings` 1定数、`TagDictionaryEntry`（定数参照のみ） |
| `services/generic_cad_extractor.py` | 633 | STEP/DXFの抽出（外部CADライブラリ不要） | `settings` 1定数 |
| `services/seed_dictionaries.py` | 222 | 初期辞書（純Python、依存なし） | なし |
| `services/tag_builder.py` | 159 | `canonical_attributes` → `derived_tags` | `settings` 1定数 |
| `services/dictionaries.py` | 54 | 辞書ロード（DB + 初期辞書のマージ） | `TagDictionaryEntry`（ORMクエリあり） |
| `services/source_formats.py` | 41 | 拡張子→フォーマット判定（純Python） | なし |

**Djangoへの結合はごく浅く、実質2点だけです。**

1. `settings` のバージョン文字列3個（`DRAWING_METADATA_NORMALIZER_VERSION`, `DRAWING_METADATA_TAG_RULE_VERSION`, `DRAWING_METADATA_SCHEMA_VERSION`）
2. `TagDictionaryEntry` モデル（辞書のDB読み出し）

1は設定オブジェクトへ置き換え、2は辞書プロバイダーのインターフェースへ置き換えます。DBアクセスは `dictionaries.load_keyword_mapping` の1箇所に集約されているため、Djangoモデルを納品パッケージへ持ち込みません。納品形態は `icad_tag_extraction` 単体パッケージ、サンプル入出力JSON、単体テスト、初期辞書、スキーマ定義です。

### 6.3 切り出し対象に含めないもの

以下はナレッジシステム本体の設計に依存するため、参考実装として渡すことはできますが、そのまま組み込む前提では作っていません。

- Djangoモデル（`RegisteredDrawing`, `DrawingMetadataSnapshot`, `DrawingMetadataExtractionJob`, `DrawingMetadataAuditLog`, `TagDictionaryEntry`）
- ジョブ管理・リトライ・タイムアウト制御・監査ログ
- 画面（タグ辞書管理、抽出管理、レビューUI）

### 6.4 JSONインターフェース

呼び出し単位は `1図面 = 1回` です。ファイルまたは標準入出力でJSONを受け渡し、呼び出し側の言語・フレームワークには依存しません。

**入力**

```json
{
  "source_file": {
    "full_path": "J:\\sample\\drawing.icd",
    "file_name": "drawing.icd",
    "source_format": "icad"
  },
  "source_kind": "2d",
  "raw_extract": {}
}
```

**出力**

```json
{
  "schema_version": "1.x",
  "source_file": {},
  "raw_extract": {},
  "canonical_attributes": {},
  "derived_tags": [
    {
      "tag": "材質:SUS304",
      "source": "material_keywords",
      "evidence": "canonical_attributes.material_keywords",
      "confidence": "medium",
      "reason": "正式材質として分類できたため採用",
      "tag_rule_version": "1.x"
    }
  ],
  "warnings": []
}
```

`canonical_attributes` の全キー、型、必須・任意区分は、別添のJSONスキーマで定義します。本資料では分類と代表項目だけを示します。

### 6.5 供給成果物

| 成果物 | 内容 |
|---|---|
| `IcadExtraction.sln` | ICAD 2D/3D抽出、材質・質量取得、JSON出力 |
| `icad_tag_extraction` | STEP/DXF抽出、正規化、辞書照合、タグ自動付与 |
| JSONスキーマ | 入力、`raw_extract`、`canonical_attributes`、`derived_tags` の型定義 |
| サンプルJSON | ICAD 2D、ICAD 3D、STEP、DXFの正常例・未取得例 |
| 初期辞書 | 客先、装置、メーカー、材質、熱処理、規格、部品名 |
| 単体テスト | 正規化、タグ生成、誤検出防止、空値処理 |
| 組み込み手順 | CLI実行、Python API呼び出し、戻り値処理 |

---

## 7. ICAD → STEP / DXF 変換の実測と限界

2026-07-26 に実機で確認した内容です。

### 7.1 できたこと

- 実機SXNETの出力形式定数を確認: `FILE_TYPE_STEP=11`、`FILE_TYPE_DXF=1`。形式別の数値オーバーライドなしで変換できます。
- `9NK452WX90-00-LINER-A3-3D-01.icd` を STEP / DXF へ変換し、変換後ファイルからの抽出・snapshot保存まで通しました。
- 変換後STEP: `step_product_names=["Assembly", "9NK452WX90-00-LINER-A3-3D-01-prt0"]`、`step_assembly_relationship_count=1`
- 変換後DXF: `dxf_layers=["SX_DraftLine", "NoLayerName_001", "0", "NoLayerName_002", "NoLayerName_003"]`

### 7.2 限界（重要）

- **ICAD本体にある材質・質量は、STEP側に同等には残りません。** 変換後データはICAD正本と等価ではなく、補完・比較の対象として扱う必要があります。監査結果（`output/converted_cad_audit_2026-07-26.json`）では、元ICAD側の材質 `SS400` が変換後STEP側では0件（overlapCount=0）、`sourceMassAvailable=true` に対し `convertedMassAvailable=false` でした。部品名も元 `9NK452WX90-00-LINER-A3-3D-01` に対し変換後は `Assembly` / `...-prt0` で、一致0件でした。
- **STEP側に親子関係が残っていても、ICADの内部／外部パーツ区分は復元できません。** 今回の変換結果も `Assembly` から `...-prt0` への関係が1件あるだけで、BOM相当の外部パーツ数を判断できません。この関係数を部品数としてタグ化・集計せず、STEP構造の表示・検索補助に限定します。
- 共有DXF 38件ではブロック属性を5ファイル・30属性確認しましたが、すべて `SX_DeltaSymbol / デルタ文字` で、図番・材質等の図枠属性ではありませんでした。図枠情報がブロック属性で入るかは客先の図枠仕様に依存します。
- STEPはSXNETが `.stp` 拡張子で出力したため、`.step` / `.stp` の両方をSTEP成果物として検出しています。
- DXF変換時、SXNETのexport自体は成功しても、runnerの終了待ちが長くなるケースがありました。結果JSONが存在する場合は成功済み成果物として読む実装にしています。
- 変換後にICADの保存確認ダイアログが出ることがありますが、保存は不要です。`IcadExtraction.Runner.exe shutdown-icad` で保存なし終了できます。

### 7.3 変換に関する所見

「ICAD→STEP変換を機能として用意する」ことは技術的には成立します。ただし**変換したSTEPから取れる情報は、ICAD正本から直接抜いた情報より確実に少ない**という実測結果があります。変換を経由するのは「ICAD正本を直接処理できない環境でも最低限の情報を取りたい」場合の代替経路であって、上位互換ではありません。

### 7.4 共有DXF 38件での本体タグ生成実測（2026-07-28）

本体の `generic_cad_extractor.py` → `normalization.py` → `tag_builder.py` を通して、ICADから変換した共有DXF 38件を再検証しました。

| タグ | 該当ファイル数 |
|---|---:|
| `寸法あり` | 30 |
| `寸法公差あり` | 7 |
| `幾何公差あり` | 1 |
| `溶接指示あり` | 13 |
| `溶接:すみ肉` | 2 |
| `溶接:全周` | 5 |
| `硬度:HRC` | 2 |
| `硬度:HV` | 0 |

`THV6x4`、`LQHB06` のように英数字識別子へ埋め込まれた文字列は硬度として扱いません。実測JSONは `output/dxf_full_audit_2026-07-28/production_tag_validation.json` に保存しています。

### 7.5 共有ICAD抽出JSON 39件でのタグ再生成実測（2026-07-28）

保存済みのICAD 2D/3D抽出JSONを、更新後の `normalization.py` → `tag_builder.py` で再検証しました。出図範囲枠がある図面では、枠外要素を自動タグの根拠から除外しています。

| タグ | 該当図面数 |
|---|---:|
| `寸法あり` | 28 |
| `寸法公差あり` | 5 |
| `幾何公差あり` | 2 |
| `溶接指示あり` | 4 |
| `溶接:すみ肉` | 0 |
| `溶接:全周` | 0 |
| `硬度:HRC` | 2 |
| `硬度:HV` | 0 |

ICAD経路でも `SxGeomWeld` または一般文字中の溶接語から `溶接指示あり` を生成します。今回の保存済みICAD抽出JSONには、すみ肉・全周を確定できる文字値がなかったため、種別タグは0件です。実測JSONは `output/icad_feature_tag_validation_2026-07-28.json` に保存しています。

### 7.6 既存テスト用ICAD全50件のSTEP変換・構造監査（2026-07-28）

固定manifestの共有サンプル39件と、ワークスペース内 `cad_data` の11件を合わせ、既存テスト用ICAD 50件を全件対象にしました。全件監査時は保存確認ダイアログによる停止を避けるため変換ごとに終了していましたが、製品実装では同一処理内の変換でICADを再利用し、処理全体の終了時に1回だけ `shutdown-icad` を実行します。処理側が自動起動したICADだけを対象とし、「保存しますか」が出た場合は「いいえ／保存しない／破棄」を選んで保存せず終了します。タイムアウト時も結果JSONの自動起動記録を確認して同じ終了処理を行います。

| 項目 | 結果 |
|---|---:|
| 対象 | 50件 |
| 元ICAD実体あり | 49件 |
| STEP変換・監査成功 | 48件 |
| 形状要素なしで変換不可 | 1件 |
| 元ICAD実体なし | 1件 |
| 元ICAD抽出結果と比較可能 | 39件 |
| STEP内に製品・部品関係あり | 48件 |
| STEP内に外部参照識別信号あり | 0件 |

変換不可の1件は `DFR-CM1-AA0305300011.icd` で、SXNETが `MSG06223 処理対象となる要素がありません` を返しました。実体なしの1件はmanifest No.8の `03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd` です。

元ICAD抽出結果と比較できた39件では、次の結果になりました。

| 比較観点 | 元ICAD側の該当数 | STEP側で同等情報を確認できた数 |
|---|---:|---:|
| 外部パーツあり | 6件 | 0件 |
| 材質あり | 32件 | 0件 |
| 質量あり | 37件 | 0件 |
| 部品名が1件以上一致 | 39件中 | 0件 |
| 外部パーツ名が1件以上一致 | 外部パーツあり6件中 | 0件 |

外部パーツを持つ実データでも、STEPの製品数・関係数とICADの内部／外部パーツ数は一致せず、外部参照を示すSTEPエンティティは0件でした。

| ファイル | ICAD外部 | ICAD内部 | STEP製品 | STEP関係 | STEP外部参照 |
|---|---:|---:|---:|---:|---:|
| `CAA5012-02434000K1R1.icd` | 26 | 334 | 320 | 319 | 0 |
| `XH30-A08001-R03-JP_ロードカップ部改造.icd` | 85 | 490 | 476 | 475 | 0 |
| `PSG011-PA0500_コラム.icd` | 37 | 225 | 30 | 29 | 0 |
| `PSG011-PA1300_ベース.icd` | 14 | 81 | 87 | 86 | 0 |
| `47323200X40c.icd` | 15 | 421 | 746 | 745 | 0 |

したがって、STEPの `PRODUCT` 数や `NEXT_ASSEMBLY_USAGE_OCCURRENCE` 数はBOM部品数・外部パーツ数として使用しません。STEP階層は、ビューワーのツリー表示、親子関係を使った検索補助、配置数確認などのSTEP内構造としてのみ利用します。材質・質量・内部／外部区分・正規の部品名が必要な場合は、ICAD正本からSXNETで直接抽出します。

全件の集計は `output/step_full_audit_2026-07-28/summary.md`、機械可読データは同フォルダの `summary.json` / `summary.csv`、個別結果は `per_file_audit`、変換STEPは `step` に保存しています。

---

## 8. 参考ドキュメント

| ドキュメント | 内容 |
|---|---|
| `icad_2d_3d_extraction_capability_matrix_2026-07-14.md` | SXNET一次資料に基づく取得可能性マトリクス（A〜D判定） |
| `icad_shared_sample_extraction_findings_2026-07-14.md` | 共有サンプルでの抽出検証詳細 |
| `icad_cad_tag_attribute_redesign_2026-07-14.md` | タグ・属性設計の考え方 |
| `extraction_result_schema_2026-05-28.md` | 抽出結果スキーマ定義 |
| `icad_csharp_python_architecture_2026-05-27.md` | C#／Python分担設計 |
| `souya_icad_tag_attribute_handoff_2026-07-14.md` | 連携項目表（分冊） |
| `cad_tag_extraction_sources_for_souya_2026-07-23.md` | 本資料の前版（STEP/DXF中心） |
