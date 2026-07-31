# CADタグ・属性抽出 抽出元カタログと具体例（創屋様向け）

- 作成日: 2026-07-28
- 最終更新日: 2026-07-31
- 版: r6（本文の実図面・社内パスは匿名化し、配布承認済み初期辞書を同梱）
- 作成: 株式会社アルパイン設計事務所
- 文書状態: 確定（抽出・正規化・自動タグ付与済みJSONまで）
- 配布範囲と実行手順の正本: [`souya_tag_extraction_minimal_handoff_2026-07-30.md`](souya_tag_extraction_minimal_handoff_2026-07-30.md)

---

## 0. この資料が答えること

本資料は、当社が供給する「CADからのタグ・属性抽出および自動タグ付与」の確定仕様を示します。

2026-07-31版では、図面名称・図面番号の抽出改善に加え、Python正規化・辞書・タグ生成のDjango非依存化、C#/Python境界のJSON Schema固定、再生成可能な創屋向け最小パッケージ、配布承認済み初期辞書を反映しました。

| 確定事項 | 記載箇所 |
|---|---|
| どこから何を抜き出すか | 2章（抽出元カタログ）、3章（正規化後の属性） |
| 文字列・属性からどのタグを付与するか | 4章（タグ生成ルール・辞書） |
| 出力がどのような形になるか | 5章（説明用の架空例） |
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
| パーツ名・コメント | `SxInfPart.name/comment` | `parts[].name/comment` | 全体の`part_*`に加え、`internal_part_*`と`external_part_*`へ分離 |
| 外部参照・ミラー・未解決参照 | `SxInfPart.is_external/is_mirror/is_unloaded` | `parts[].is_*` | `external_part_exists` ほか |
| 参照図面名・パス | `SxInfPart.ref_model_name/path` | `parts[].ref_model_*` | `ref_model_names`, `ref_model_paths` |
| 材質（全体・部品単位） | `SxEnt.getInfMaterialList()`, `SxEntPart.getInfMaterialList()` | `materials[]`, `parts[].materials[]` | `material_ids`, `material_names`, `part_material_candidates`, `external_part_material_candidates` |
| 質量・重量・体積・面積・密度 | `SxEnt.getMass()` → `SxInfMass` | `mass_properties.*` | `mass_value`, `weight_value`, `volume_value`, `area_value`, `density_value` |
| 重心・慣性モーメント | `SxInfMass.pos`, `inf_global_moment` ほか | `mass_properties.*_moment` | `center_of_gravity`, `global_moment`, `inertia_moment_candidates` |
| トップパーツ付加情報 | `SxWF.getInfExTopPart()`, ルートの `SxInfPartTree.ex_inf` | `top_part.ex_info`, `top_part.ex_info_fields` | `top_part_ex_info`, `part_ex_info_fields`, `part_ex_info_tokens` |
| 各構成パーツの付加情報 | 各ノードの `SxInfPartTree.ex_inf` | `parts[].ex_info`, `parts[].ex_info_fields` | パーツ階層別の `part_ex_info_fields`, `part_ex_info_tokens` |

パーツ付加情報はトップパーツだけに限定しません。パーツツリーを再帰走査し、各構成パーツの付加情報を階層パスと対応付けて保持します。キー・値に分解できた項目は、PRFX、ユニット番号、材質、熱処理、硬度の候補抽出に使用し、分解できない生文字列も検索・監査用トークンとして残します。

アセンブリ本体と外部参照パーツは別の情報源として扱います。`internal_part_*`は本体側、`external_part_*`は外部側です。外部パーツの名称・材質・付加情報は検索・構成証跡として保持しますが、本体の正式名称・正式材質へ昇格させません。

### 2.2 ICAD 2D（経路A）

| 抽出元 | SXNET根拠 | raw_extract | 正規化先 |
|---|---|---|---|
| ビューシート名・尺度・種別 | `SxModel.getGlobalVS()`, `SxInfVS` | `view_sheets[]` | `model_view_sheet_count`, `scale_candidates` |
| 出図範囲枠・用紙サイズ | `SxInfPrint` | `print_frames[]` | `paper_size`, 印刷枠内外判定 |
| 文字・注記 | 文字要素 | `texts[]` | `text_tokens`, `label_texts` |
| 図枠のラベルと値 | 同一文字要素の同じ行／次行。名称欄だけ同一ビュー・同一レイヤー・近接整列を限定採用 | `texts[]` | `title_block_candidates` → `title_block_fields` |
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
`material`, `material_ids`, `material_names`, `material_specific_gravities`, `material_keywords`, `unresolved_material_keywords`, `part_material_candidates`, `external_part_material_candidates`, `internal_part_material_keywords`, `external_part_material_keywords`, `material_probe_status`

**部品構成**
`part_names`, `part_comments`, `part_tree_paths`, `part_name_candidates`, `part_ex_info_fields`, `part_ex_info_tokens`, `internal_part_names`, `internal_part_comments`, `internal_part_tree_paths`, `internal_part_ex_info_fields`, `external_part_names`, `external_part_comments`, `external_part_tree_paths`, `external_part_ex_info_fields`, `external_part_name_candidates`, `ref_model_names`, `ref_model_paths`, `external_part_exists`, `mirror_part_exists`, `unresolved_part_exists`, `referenced_2d_part_count`, `referenced_2d_trusted_part_count`

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
| `塗装:` | `title_block_fields.coating_instruction`。`paint_instruction_tokens`が連携された場合も対応 | medium |
| `熱処理:` | `heat_treatment_keywords` | medium |
| `硬度:HRC` / `硬度:HV` | `hardness_spec_values` | medium |
| `PRFX:` | `prfx_candidates`, `title_block_fields.prfx` | medium |
| `ユニット:` | `unit_number_candidates`, `title_block_fields.unit_number` | medium |
| `規格:` | `spec_tokens` のうち注入辞書に一致した規格識別子 | medium |

各タグには `source`（生成元キー）、`evidence`（根拠パス）、`confidence`、`reason`（日本語の採用理由）、`tag_rule_version` が付きます。根拠なしのタグは作りません。

現行バージョンはスキーマ`1.0.0`、正規化`1.1.0`、タグ規則`1.1.0`です。

なお `spec_tokens` は、2Dでは図面内の文字トークンと公差テキストを辞書照合して得た規格識別子です。文字列の集合を無条件にタグへせず、注入辞書と一致した正規名だけを`規格:`タグにします。

### 4.2 辞書

タグ変換の辞書はDB化済みで、画面（システム設定 > タグ辞書管理）と `/admin` から編集できます。初期辞書の規模は以下です。

| 辞書 | 初期エントリ数 | 例 |
|---|---|---|
| 客先 | 3 | コマツ小山、広島アルミ、澁谷工業 |
| 装置カテゴリ | 30 | ガントリー、治具、ロボット、コンベア、シュート、架台、制御盤 ほか |
| メーカー | 40 | SMC、ミスミ、オムロン、キーエンス、THK、NSK、NTN ほか |
| 材質分類 | 68 | SS400、SUS304、S45C、A5052P、FC300 ほか（正式63、未解決3、除外2） |
| 熱処理 | 20 | 焼入れ、調質、浸炭、窒化、高周波焼入れ ほか |
| 規格 | 7 | SES、JIS、ISO、DIN、ANSI、幾何公差、溶接記号 |
| 部品名 | 23 | PLATE、COVER、BRACKET、SHAFT、GUIDE ほか |

上表の件数は `backend/icad_tag_extraction/seed_dictionaries.py` を数え直した実数である（2026-07-30時点）。

客先辞書3件と顧客固有規格`SES`は配布承認済みの初期値として同梱します。案件辞書は初期エントリ0件です。照合対象はファイルパスのトークンだけでなく、モデル情報・図面内文字・DXFレイヤー等を合成した検索トークン列（`part_keywords`）です。同梱値以外の客先名・案件名・別名は、共有範囲の承認後に創屋様のDBまたは辞書JSONへ登録してください。

### 4.3 タグ化するもの／属性保持に留めるもの

**タグ化する**: 客先、案件、装置カテゴリ、寸法の有無、寸法公差の有無、幾何公差の有無、溶接指示の有無、明示判定できた溶接種別（すみ肉・全周）、メーカー、正式材質、表面処理、塗装、熱処理、硬度尺度（HRC・HV）、PRFX、ユニット番号、明確な規格識別子

**属性として保持し、原則タグ化しない**: 寸法値、公差値、溶接記号の生値、硬度の数値、バルーン、穴・長穴・切断線・ハッチング等の形状特徴、質量・体積・重心・慣性モーメント

理由は、存在するだけでタグにすると検索ノイズが大きくなるためです。これらは図面レビューやRAG投入時の属性・根拠として保持します。

---

## 5. 具体例（説明用の架空データ）

この章のファイル名、パス、客先名、案件名、値は、入出力の読み方を示すための架空データです。当社の顧客資料、社内ファイルサーバー、実図面の値は含めていません。

### 5.1 客先・装置・材質を抽出する例

前提として、創屋様側の辞書へ `顧客A` と別名 `customer-a` を登録します。

```text
ファイル : SAMPLE-ASSY-001.icd
パス     : C:\sample\customer-a\gantry\SAMPLE-ASSY-001.icd
抽出属性 : customer_name="顧客A", equipment_category="ガントリー",
           material_keywords=["SUS304", "SUS"], part_names=["SAMPLE-PART-001"]
自動タグ : 客先:顧客A / 装置:ガントリー / 材質:SUS304 / 材質:SUS
```

`customer_name`はパス中の`customer-a`と注入辞書の一致、`equipment_category`はパス中の`gantry`と装置辞書の一致、材質はICAD 3Dの材質情報を根拠とします。

### 5.2 2D文字列から指示タグを抽出する例

```text
図面文字 : "SUS304  焼入れ HRC50  全周溶接"
抽出属性 : material_keywords=["SUS304", "SUS"],
           heat_treatment_keywords=["焼入れ"],
           hardness_scale_candidates=["HRC"],
           weld_type_candidates=["全周"]
自動タグ : 材質:SUS304 / 材質:SUS / 熱処理:焼入れ / 硬度:HRC /
           溶接指示あり / 溶接:全周
```

硬度の数値`50`や溶接記号の生値は検索ノイズを避けるため属性・根拠として保持し、タグにはしません。

### 5.3 例から読み取れる特性

- 客先・案件・装置は、ファイルパス、モデル情報、図面内文字を合成したトークン列と注入辞書を照合します。
- 材質と断定できない文字列は`unresolved_material_keywords`へ隔離し、自動タグには採用しません。
- 3Dの質量・重量は属性として保持しますが、存在するだけでは自動タグにしません。
- 半角カナ・機種依存文字を含む運用データは、創屋様の検索要件に合わせて表示・検索正規化方針を決める必要があります。

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

`backend/icad_tag_extraction`へDjango非依存の単体Pythonパッケージとして切り出し済みです。Djangoをインストールしない環境で、CLIまたはPython APIから実行できます。

| ファイル | 役割 | Django依存 |
|---|---|---|
| `pipeline.py` | 入力検査、正規化、タグ生成を1回で実行 | なし |
| `normalization.py` | `raw_extract` → `canonical_attributes` | なし |
| `generic_cad_extractor.py` | STEP/DXFのraw抽出 | なし |
| `tag_builder.py` | `canonical_attributes` → `derived_tags` | なし |
| `dictionary_provider.py` | seed、JSON、mapping辞書の統一インターフェース | なし |
| `seed_dictionaries.py` | 初期辞書 | なし |
| `configuration.py` | Schema・正規化・タグ規則の版設定 | なし |
| `cli.py` | ファイル入出力CLI | なし |

Django側の`services/core_adapter.py`と`services/dictionaries.py`は、DB辞書と保存処理をこの独立コアへ接続するアダプターです。創屋向け最小パッケージにはDjangoモデルや設定を持ち込みません。

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
    "full_path": "C:\\sample\\drawing.icd",
    "file_name": "drawing.icd"
  },
  "source_format": "icad",
  "source_kind": "2d",
  "warnings": [],
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

`canonical_attributes` の全キー、型、必須・任意区分は、`schemas/tag_extraction/*.schema.json`で定義します。本資料では分類と代表項目だけを示します。

### 6.5 供給成果物

| 成果物 | 内容 |
|---|---|
| `IcadExtraction.sln` | ICAD 2D/3D抽出、材質・質量取得、JSON出力 |
| `backend/icad_tag_extraction` | STEP/DXF抽出、正規化、辞書照合、タグ自動付与 |
| `schemas/tag_extraction` | C# raw入力、canonical、`derived_tags`、処理結果の型定義 |
| `examples/tag_extraction_contract` | Schema検証済みICAD 2D/3D入力例 |
| 初期辞書 | 客先、装置、メーカー、材質、熱処理、規格、部品名 |
| 単体テスト | Django非依存、2D/3D期待値一致、Schema検証 |
| Docker例 | 独立Python CLIを実行するDockerfileとcompose |
| 組み込み手順 | `souya_tag_extraction_minimal_handoff_2026-07-30.md` |

最小パッケージは`python scripts\build_souya_tag_extraction_package.py`で再生成します。生成物は`output/souya_tag_extraction_minimal_2026-07-30/`と同名ZIPで、`manifest.json`に全ファイルのサイズとSHA-256を記録します。

---

## 7. ICAD → STEP / DXF 変換の確認済み仕様と限界

### 7.1 確認済みの処理

- SXNETの出力形式定数は`FILE_TYPE_STEP=11`、`FILE_TYPE_DXF=1`で、形式別の数値オーバーライドなしで変換できます。
- `IcadExtraction.Runner convert-cad`は、ICADを開き、STEPまたはDXFへ出力し、結果JSONを返します。
- STEPは`.step`と`.stp`、DXFは`.dxf`を入力形式として受け付けます。
- 変換後ファイルはPython汎用抽出器へ渡し、同じcanonical属性・タグ結果の契約へ接続できます。

### 7.2 限界（重要）

- **ICAD本体にある材質・質量は、STEP側に同等には残らない場合があります。** 変換後データはICAD正本と等価ではなく、補完・比較の対象です。
- **STEP側に親子関係が残っていても、ICADの内部／外部パーツ区分は復元できません。** `PRODUCT`数や`NEXT_ASSEMBLY_USAGE_OCCURRENCE`数を、BOM部品数・外部パーツ数として使用しません。
- **DXFの図枠属性は客先ごとの作図・出力仕様に依存します。** ブロック属性が存在しても、図番・材質等の業務属性とは限りません。
- DXF変換時、SXNETのexport自体は成功してもrunnerの終了待ちが長くなる場合があります。結果JSONが存在する場合は、生成済み成果物の状態を確認して扱います。
- 変換後にICADの保存確認ダイアログが出る場合は、`IcadExtraction.Runner.exe shutdown-icad`で保存せず終了できます。

### 7.3 受入時に創屋様環境で確認すること

1. 創屋様のICAD・SXNETバージョンとライセンスで、提供サンプルのSTEP/DXF変換が成功すること。
2. 変換後のSTEPで、製品名・部品階層・材質名のうち何が保持されるか。
3. 変換後のDXFで、文字・寸法・公差・溶接記号・レイヤー・ブロック属性のうち何が保持されるか。
4. 元ICADのcanonical属性と変換後結果を比較し、創屋様の検索要件に必要な情報が欠落していないか。
5. 実運用図面の保存確認ダイアログ、タイムアウト、外部参照ファイルを含む場合の運用が成立するか。

変換経路は、ICAD正本を直接処理できない場合の代替・補完手段です。材質、質量、内部／外部パーツ区分、正規の部品名が必要な場合は、ICAD正本からSXNETで直接抽出してください。

---

## 8. 参考ドキュメント

| ドキュメント | 内容 |
|---|---|
| `extraction_result_schema_2026-05-28.md` | 抽出結果スキーマ定義 |
| `windows_extraction_agent_api_design_2026-07-29.md` | Windows agentとC#入出力契約 |
| `icad_dxf_step_standalone_conversion_guide_2026-07-29.md` | ICADからDXF/STEPへ変換する実行手順 |
| `souya_tag_extraction_minimal_handoff_2026-07-30.md` | パッケージ構成、実行方法、組み込み境界 |
