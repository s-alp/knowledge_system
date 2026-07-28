# CADタグ・属性抽出 抽出元カタログと具体例（創屋様向け）

- 作成日: 2026-07-28
- 版: r1（`cad_tag_extraction_sources_for_souya_2026-07-23.md` の後継。STEP/DXF中心だった前版に、ICAD正本からの抽出・実データ具体例・ソース切り出し範囲・ライセンス論点を統合）
- 作成: 株式会社アルパイン設計事務所

---

## 0. この資料が答えること

創屋様からいただいた4点に、この資料で回答します。

| ご質問 | 回答箇所 |
|---|---|
| どこからどういったものを抜き出すのかが事前に分かるとありがたい | 2章（抽出元カタログ）、3章（正規化後の属性）、4章（タグ生成ルール） |
| どういったものが抜き出されるのか、具体例が欲しい | 5章（実ICAD 39件の実測結果と実ファイル5例） |
| 完成後はタグ・属性抽出の部分のソースだけ頂けるとありがたい | 6章（切り出し範囲とモジュール境界） |
| ICAD→STEP変換／ICADライセンスの用意 | 7章（変換の実測と限界）、8章（ライセンス論点） |

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

経路Bと経路Cは同じ抽出器を使います。経路B・Cでは**ICAD本体がなくても抽出処理そのものは動きます**（8章のライセンス論点に直結します）。

---

## 2. 抽出元カタログ（どこから何を抜くか）

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
| トップパーツ付加情報 | `SxWF.getInfExTopPart()`, `SxInfPartTree.ex_inf` | `top_part.ex_info` | `top_part_ex_info`, `part_ex_info_fields` |

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

### 2.4 DXF（経路B・C）

| 抽出元 | raw_extract | 正規化先 |
|---|---|---|
| `TEXT` / `MTEXT` / `ATTRIB` / `ATTDEF` | `texts[]` | `text_tokens`, `title_block_candidates` |
| `INSERT` + `ATTRIB` のブロック参照 | `block_references[].attributes[]` | `dxf_block_references`, `dxf_block_attribute_tokens` |
| `DIMENSION` の表示値候補 | `dimensions[]` | `dimension_values` |
| `LINE` / `CIRCLE` / `ARC` / `ELLIPSE` / `LWPOLYLINE` / `POLYLINE` / `SPLINE` / `HATCH` | `geometry_primitives[]` | 形状特徴候補 |
| レイヤー一覧 | `layers[]` | `dxf_layers` |

---

## 3. 正規化後の属性キー（canonical_attributes）

正規化後は固定スキーマの辞書になります。**2D snapshot で 133 キー、3D snapshot で 97 キー**です。値が取れなかったキーは `null` または空配列のまま残ります（「取れなかった」ことも情報として残す方針）。

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

`canonical_attributes` から、以下の11種類のタグを生成します。

| タグ接頭辞 | 生成元の属性キー | 確度 |
|---|---|---|
| `客先:` | `customer_name` | high |
| `案件:` | `project_name` | high |
| `装置:` | `equipment_category` | high |
| `メーカー:` | `maker_keywords` | medium |
| `材質:` | `material_keywords`, `title_block_fields.material` | medium |
| `表面処理:` | `surface_treatment_tokens`, `title_block_fields.surface_treatment` | medium |
| `塗装:` | `paint_instruction_tokens`, `title_block_fields.coating_instruction` | medium |
| `熱処理:` | `heat_treatment_keywords` | medium |
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

**タグ化する**: 客先、案件、装置カテゴリ、メーカー、正式材質、表面処理、塗装、熱処理、PRFX、ユニット番号、明確な規格識別子

**属性として保持し、原則タグ化しない**: 寸法値、公差値、溶接記号、バルーン、穴・長穴・切断線・ハッチング等の形状特徴、質量・体積・重心・慣性モーメント

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

創屋様のご要望「タグ・属性抽出の部分のソースだけ頂ければ、その部分だけ切り出しできると考えております」について、**切り出せる構成になっています**。現時点の境界は以下です。

### 6.1 C#側（ICAD抽出コア）

独立ソリューション（`IcadExtraction.sln`、約4,700行）としてそのまま渡せます。ナレッジシステム本体への依存はありません。

| プロジェクト | 役割 |
|---|---|
| `IcadExtraction.Contracts` | 入出力のデータ契約（JSONスキーマ相当） |
| `IcadExtraction.SxNet` | SXNET経由の2D/3D抽出、材質・質量プローブ、STL/STEP/DXF出力 |
| `IcadExtraction.Runner` | CLIエントリ。`extract` / `extract-batch` / `detect` / `probe-2d-print` / `convert-cad` / `probe-cad-export-types` / `cancel` / `clear-command` / `shutdown-icad` / `self-check` の10コマンド |

インターフェースは **`1図面 = 1回のプロセス呼び出し`、入出力はJSONファイル**です。呼び出し側の言語を選びません。

### 6.2 Python側（正規化・タグ生成コア）

以下6ファイル（約2,800行）が正規化・タグ生成の本体です。

| ファイル | 行数 | 役割 | 外部依存 |
|---|---|---|---|
| `services/normalization.py` | 1,860 | `raw_extract` → `canonical_attributes` | `settings` 1定数、`TagDictionaryEntry`（定数参照のみ） |
| `services/generic_cad_extractor.py` | 519 | STEP/DXFの抽出（外部CADライブラリ不要） | `settings` 1定数 |
| `services/seed_dictionaries.py` | 222 | 初期辞書（純Python、依存なし） | なし |
| `services/tag_builder.py` | 112 | `canonical_attributes` → `derived_tags` | `settings` 1定数 |
| `services/dictionaries.py` | 54 | 辞書ロード（DB + 初期辞書のマージ） | `TagDictionaryEntry`（ORMクエリあり） |
| `services/source_formats.py` | 41 | 拡張子→フォーマット判定（純Python） | なし |

**Djangoへの結合はごく浅く、実質2点だけです。**

1. `settings` のバージョン文字列3個（`DRAWING_METADATA_NORMALIZER_VERSION`, `DRAWING_METADATA_TAG_RULE_VERSION`, `DRAWING_METADATA_SCHEMA_VERSION`）
2. `TagDictionaryEntry` モデル（辞書のDB読み出し）

1はコンストラクタ引数や設定オブジェクトへ置き換えるだけです。2はDBアクセスを伴いますが、DBアクセスは `dictionaries.load_keyword_mapping` の1箇所に集約されており（`normalization.py` は `TagDictionaryEntry.KIND_*` を定数として参照しているだけ）、辞書ロード関数をインターフェース化すれば分離できます。したがってDjangoなしの純Pythonパッケージとして切り出せます。ご希望であれば、その形（`icad_tag_extraction` 単体パッケージ + サンプル入出力JSON + 単体テスト）で納品できます。

### 6.3 切り出し対象に含めないもの

以下はナレッジシステム本体の設計に依存するため、参考実装として渡すことはできますが、そのまま組み込む前提では作っていません。

- Djangoモデル（`RegisteredDrawing`, `DrawingMetadataSnapshot`, `DrawingMetadataExtractionJob`, `DrawingMetadataAuditLog`, `TagDictionaryEntry`）
- ジョブ管理・リトライ・タイムアウト制御・監査ログ
- 画面（タグ辞書管理、抽出管理、レビューUI）

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
- 今回のDXFサンプルではブロック属性は0件でした。図枠情報がブロック属性で入っているかは客先の図枠仕様に依存します。
- STEPはSXNETが `.stp` 拡張子で出力したため、`.step` / `.stp` の両方をSTEP成果物として検出しています。
- DXF変換時、SXNETのexport自体は成功しても、runnerの終了待ちが長くなるケースがありました。結果JSONが存在する場合は成功済み成果物として読む実装にしています。
- 変換後にICADの保存確認ダイアログが出ることがありますが、保存は不要です。`IcadExtraction.Runner.exe shutdown-icad` で保存なし終了できます。

### 7.3 変換に関する所見

「ICAD→STEP変換を機能として用意する」ことは技術的には成立します。ただし**変換したSTEPから取れる情報は、ICAD正本から直接抜いた情報より確実に少ない**という実測結果があります。変換を経由するのは「ICADライセンスのない環境でも最低限の情報を取りたい」場合の代替経路であって、上位互換ではありません。

---

## 8. ICADライセンスの論点

創屋様のご懸念「ナレッジシステム専用として150万円程のICADを販売先が用意してくれるか」「専用である必要はあるのか、兼用は難しいか」について、まず**技術的な事実**を整理し、そのうえで選択肢を示します。

### 8.1 技術的な事実（コード上で確認済み）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | 経路A（ICAD正本から抽出）は、SXNET経由でICAD SX本体プロセスを必要とする | `IcadProcessStarter` がICAD実行体を起動、または起動済みプロセスへ接続 |
| 2 | ICADセッションは**1つずつ排他利用**される。並列に複数の抽出を走らせない | `Local\KnowledgeSystem.IcadExtraction.IcadSession` の Mutex で直列化。`Local\` のため排他範囲はWindowsのログオンセッション単位で、別ユーザーセッション・別マシンには効かない |
| 3 | ICADが必要なのは**登録・抽出のタイミングだけ**。検索・閲覧・タグ表示・RAG回答にICADは不要 | 抽出結果はsnapshotとしてDBに保存され、以降は参照されない |
| 4 | 経路B・C（STEP/DXFからの抽出）は**ICADなしで動く**。外部CADライブラリも不要 | `generic_cad_extractor.py` は外部CADライブラリに依存せず、Python標準の文字列処理だけでSTEP/DXFを解析（ezdxf・OCC等の依存なし） |
| 5 | ICAD→STEP/DXF変換の**その瞬間だけ**ICADが要る | `IcadCadFormatExporter`（SXNET `SxModel.export`） |

**したがって「ナレッジシステム専用のICADライセンス」が技術的に必須という結論にはなりません。** 必要なのは「抽出処理を実行している間、そのICADセッションを占有できること」だけです。

### 8.2 販売を前提にした場合の選択肢

自社導入だけでなく外販を考えると、「顧客が150万円のICADを追加購入する」を前提にした製品は売りにくくなります。前提を分けて設計すべきと考えます。

| 案 | 内容 | 顧客の追加ICAD費用 | 取得できる情報 | 主な制約 |
|---|---|---|---|---|
| **① 既存ライセンス兼用（夜間バッチ）** | 顧客が既に持つICADを、設計者が使わない夜間・休日に抽出用として使う | 0円 | 最大 | ライセンス条項の可否確認が必須。抽出中はその座席を占有 |
| **② 既存ライセンス兼用（専用PC1台）** | 顧客の空き座席1本を抽出専用PCへ割り当て | 0円（座席の振替） | 最大 | 空き座席がある顧客に限る |
| **③ ICAD不要構成** | 顧客側でSTEP/DXF/PDFへ出力済みのデータを取り込む。経路B・Cのみ | 0円 | 中（材質・質量は落ちる） | 顧客に出力運用を依頼する必要あり |
| **④ 変換代行** | 当社の余剰ライセンス＋当社サーバーでICAD→STEP/中間データ変換を代行 | 0円 | 最大〜中 | 図面データを社外（当社）へ出すことへの顧客同意が必要 |
| **⑤ 専用ライセンス新規購入** | 顧客がナレッジシステム用にICADを1本追加 | 約150万円 | 最大 | 費用が導入判断のボトルネックになりやすい |

当社には余剰ライセンスがあるため、④は当社が担げる現実的な選択肢です。また、対象顧客はICADユーザーであることが多く、①②が成立する可能性は相応にあると見ています。

### 8.3 要確認事項（当社→富士通／ICAD販売元）

以下はライセンス条項の問題であり、当社もまだ確認できていません。断定せずに確認事項として残します。

- 設計者向けライセンスを、無人のバッチ処理（サーバー常駐・自動起動）で使うことが許諾範囲か。
- ライセンス形態（ノードロック／フローティング等）と、フローティングの場合の借用可否。
- 「同時使用」の定義。1座席を夜間だけ別PCで使う運用が可能か。
- 当社の余剰ライセンスを使って他社図面の変換を受託することが許諾範囲か（④の前提）。

### 8.4 創屋様へのご相談

上記を踏まえ、**製品としては「ICADがある構成」と「ICADがない構成」の両方を成立させる**方向で設計を進めたいと考えています。具体的には、経路Aで取れる情報と経路B・Cで取れる情報の差を仕様として明示し、顧客の環境に応じて構成を選べる形です。この方針で問題ないか、ご意見をいただきたいところです。

---

## 9. 創屋様への確認事項

### 9.1 抽出まわり

1. STEPから製品名・部品名・部品階層・材質・質量特性を取得できるライブラリ／APIを、創屋様側でお持ちか。
2. DXFからTEXT/MTEXT、ブロック属性、レイヤー名、寸法、公差、溶接記号を分離取得できるか。
3. 図枠のラベルと値を、可能な限り同一TEXT/MTEXT要素またはDXFブロック属性として取得できるか。別要素間の座標ペアリングは対象外とする。
4. 材質が色・レイヤー・ブロック名にしか入っていないケースがあるか。
5. 抽出値に推測を混ぜず、取得元フィールドと信頼度を添えて返せるか。

### 9.2 受け渡しまわり

6. 6.2に書いた「Django非依存の純Pythonパッケージ」形での納品でよいか。それとも現状のDjango app のまま渡す方が組み込みやすいか。
7. 納品時に一緒に欲しい成果物（サンプル入出力JSON、単体テスト、辞書の初期データ、スキーマ定義）の優先順位。
8. タグ・属性の書き込み先API（`drawing_attributes` / `product_attributes` / `part_attributes` 相当）の確定仕様。

### 9.3 ライセンス・構成

9. 8.4の「ICADあり／なし両構成」の方針で問題ないか。
10. ICAD→STEP変換を創屋様側の機能として実装される場合、当社のC# `convert-cad` 実装をそのまま使うか、創屋様側で作り直すか。

---

## 10. 参考ドキュメント

| ドキュメント | 内容 |
|---|---|
| `icad_2d_3d_extraction_capability_matrix_2026-07-14.md` | SXNET一次資料に基づく取得可能性マトリクス（A〜D判定） |
| `icad_shared_sample_extraction_findings_2026-07-14.md` | 共有サンプルでの抽出検証詳細 |
| `icad_cad_tag_attribute_redesign_2026-07-14.md` | タグ・属性設計の考え方 |
| `extraction_result_schema_2026-05-28.md` | 抽出結果スキーマ定義 |
| `icad_csharp_python_architecture_2026-05-27.md` | C#／Python分担設計 |
| `souya_icad_tag_attribute_handoff_2026-07-14.md` | 連携項目表（分冊） |
| `cad_tag_extraction_sources_for_souya_2026-07-23.md` | 本資料の前版（STEP/DXF中心） |
