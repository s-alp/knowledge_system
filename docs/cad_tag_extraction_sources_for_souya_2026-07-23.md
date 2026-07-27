# STEP/DXFタグ取得・自動付与の抽出元整理

- 作成日: 2026-07-23
- 目的: 創屋側でSTEP/DXFデータから何を抽出すれば、ナレッジシステム側のタグ・属性自動付与へつながるかを具体化する。

## 基本方針

- ICADと同じく、抽出器は意味付け前の `raw_extract` を出す。
- Django側で `canonical_attributes` へ正規化し、既存の `derived_tags` 生成ルールでタグ化する。
- STEPは3D CADとして `source_format=step`, `source_kind=3d` を使う。
- DXFは2D CADとして `source_format=dxf`, `source_kind=2d` を使う。
- 抽出不能な項目は空配列または `null` とし、推測値は入れない。
- 現行Django側には、外部ライブラリなしでSTEP/DXFファイルを直接読む暫定抽出器を入れている。STEPはヘッダ/文字列リテラル/PRODUCT系エンティティ/アセンブリ関係候補、DXFはTEXT/MTEXT/INSERT+ATTRIB/DIMENSION/基本図形を対象にする。
- ICADから検証用のDXF/STEPを作る経路として、C# runnerの `convert-cad` コマンドを追加している。変換自体はSXNET `SxModel.export` を使うためC#側、変換後ファイルの抽出・正規化・タグ化はDjango/Python側で行う。
- Django側には `convert_icad_cad_formats` 管理コマンドを追加している。登録済みICADをDXF/STEPへ変換し、変換後ファイルを `RegisteredDrawing` に登録し、`--extract` 指定時はその場で汎用CAD抽出とsnapshot保存まで実行する。SXNETの出力形式定数が環境差で異なる場合は、`--step-export-file-type` と `--dxf-export-file-type` で形式別に数値指定できる。
- C# runnerには `probe-cad-export-types` コマンドを追加している。実機SXNET DLLの `sxnet.SxOptExport` に存在するpublic static int定数をJSON出力し、STEP/DXF変換に使える定数名を確認する。Django側からは `probe_icad_cad_export_types` 管理コマンドで同じ確認を実行できる。
- 変換後の抽出結果は、STEPの `step_product_names` / `step_assembly_relationships`、DXFの `dxf_layers` / `dxf_block_references` / `dxf_block_attribute_tokens` としてcanonicalにも保持する。`audit_converted_cad_extractions` 管理コマンドで、元ICAD snapshotと変換後STEP/DXF snapshotの材質、部品名、図枠項目、ブロック属性の重なりをJSONで確認できる。
- 正確な形状階層、BOM、材質属性、質量特性などはSTEP/DXFファイルだけから常に取れるとは限らないため、創屋側で利用可能なCAD APIや変換器がある場合は同じ `raw_extract` 形でより詳細な値を返す。

## STEPから抜き出したい項目

| 抽出元 | raw_extract例 | 正規化先 | 自動タグ例 |
|---|---|---|---|
| ファイルパス・ファイル名 | `source_file.full_path`, `source_file.file_name_without_extension` | `source_path_tokens`, `source_file_name` | `客先:コマツ小山`, `案件:...`, `装置:ガントリー` |
| STEP製品名・モデル名 | `model_info.name`, `top_part.name` | `model_name`, `top_part_name`, `part_keywords` | 辞書一致時に案件・装置タグ |
| STEPヘッダコメント・説明 | `model_info.comment`, `top_part.comment` | `model_comment`, `top_part_comment`, `part_keywords` | `メーカー:SMC`, `熱処理:浸炭焼入れ` |
| 構成部品名 | `parts[].name`, `parts[].tree_path` | `part_names`, `part_tree_paths` | 部品名辞書一致時の分類属性 |
| 部品材質 | `parts[].materials[]`, `materials[]` | `material_keywords`, `part_material_candidates` | `材質:SUS304`, `材質:S45C` |
| 参照先モデル名 | `parts[].ref_model_name`, `parts[].ref_model_path` | `ref_model_names`, `ref_model_paths` | 辞書一致時に案件・装置タグ |
| 質量・体積・表面積 | `mass_properties.mass`, `volume`, `area` | `mass_value`, `volume_value`, `area_value` | タグ化せず属性保持 |
| 重心・慣性モーメント | `mass_properties.center_of_gravity_*`, `global_moment` | `center_of_gravity`, `inertia_moment_candidates` | タグ化せず属性保持 |

### STEP raw_extract具体例

```json
{
  "source_format": "step",
  "source_kind": "3d",
  "source_file": {
    "full_path": "J:\\コマツ小山\\ガントリー\\HAND.step",
    "directory_path": "J:\\コマツ小山\\ガントリー",
    "file_name": "HAND.step",
    "file_name_without_extension": "HAND",
    "extension": ".step"
  },
  "raw_extract": {
    "model_info": {
      "name": "ガントリーハンド",
      "comment": "SMC CYLINDER"
    },
    "top_part": {
      "name": "HAND",
      "comment": "浸炭焼入れ HRC58-62"
    },
    "parts": [
      {
        "tree_path": ["HAND", "PLATE"],
        "name": "PLATE",
        "materials": ["SUS304"]
      }
    ],
    "materials": ["S45C"],
    "mass_properties": {
      "unit_name": "mm-kg",
      "mass": 1.2,
      "volume": 3500.0,
      "area": 12000.0
    }
  }
}
```

この例からは、`客先:コマツ小山`、`装置:ガントリー`、`メーカー:SMC`、`材質:S45C`、`材質:SUS304`、`熱処理:浸炭焼入れ` が候補になる。

### 現行Django暫定抽出器で取得できるSTEPの範囲

- `FILE_NAME`, `FILE_DESCRIPTION` などのヘッダ文字列。
- `PRODUCT`, `PRODUCT_DEFINITION`, `NEXT_ASSEMBLY_USAGE_OCCURRENCE`, `MANIFOLD_SOLID_BREP` などに含まれる文字列。
- `PRODUCT` を `step_products` に保持し、`NEXT_ASSEMBLY_USAGE_OCCURRENCE` の親子候補を `step_assembly_relationships` と階層付き `parts[].tree_path` に保持する。
- 文字列中の材質パターン。例: `SUS304`, `S45C`, `SS400`, `A5052`。
- ファイルパス・ファイル名からの客先/案件/装置カテゴリ辞書一致。

暫定抽出器では、STEPの幾何形状そのものを解析した体積・質量までは確定しない。部品階層はSTEP内の明示的なPRODUCT/NAUO関係から候補化するが、CAD APIで得る正確なBOMと完全同等とは断定しない。これらはICAD変換サンプルで抽出結果を照合し、必要なら詳細抽出器の追加対象にする。

## DXFから抜き出したい項目

| 抽出元 | raw_extract例 | 正規化先 | 自動タグ例 |
|---|---|---|---|
| ファイルパス・ファイル名 | `source_file.full_path`, `source_file.file_name_without_extension` | `source_path_tokens`, `source_file_name` | `客先:澁谷工業`, `装置:ロボット` |
| TEXT/MTEXT文字列 | `texts[].text_lines`, `texts[].text`, `texts[].value` | `text_tokens`, `title_block_candidates` | `規格:SES`, `材質:SS400` |
| 図枠ラベルと値 | `texts[]` の「図番」「図名」「材質」「尺度」「PRFX」「ユニット」等 | `title_block_fields` | `PRFX:RAA4844`, `ユニット:U01` |
| 寸法値・寸法記号 | `dimensions[]` | `dimension_values`, `dimension_symbols` | 原則タグ化せず属性保持 |
| 公差・幾何公差文字 | `tolerances[]` | `tolerance_candidates` | 原則タグ化せず属性保持 |
| 溶接記号・注記 | `weld_notes[]` | `weld_note_candidates` | 原則タグ化せず属性保持 |
| バルーン | `balloons[]` | `balloon_candidates` | 原則タグ化せず属性保持 |
| レイヤー名・ブロック名 | `texts[]` や `geometry_primitives[]` の補助情報 | `part_keywords` への候補 | 辞書一致時のみタグ |

### DXF raw_extract具体例

```json
{
  "source_format": "dxf",
  "source_kind": "2d",
  "source_file": {
    "full_path": "J:\\澁谷工業\\ロボット\\layout.dxf",
    "directory_path": "J:\\澁谷工業\\ロボット",
    "file_name": "layout.dxf",
    "file_name_without_extension": "layout",
    "extension": ".dxf"
  },
  "raw_extract": {
    "texts": [
      "図番 DXF-001",
      {"text": "図名 ロボット架台"},
      {"value": "材質 SS400", "inside_print_area": true},
      {"text_lines": ["PRFX", "RAA4844"], "inside_print_area": true},
      {"joined_text": "ユニット U01", "inside_print_area": true},
      {"text": "SES", "inside_print_area": true}
    ],
    "dimensions": [],
    "tolerances": [],
    "weld_notes": [],
    "balloons": [],
    "geometry_primitives": []
  }
}
```

この例からは、`客先:澁谷工業`、`装置:ロボット`、`材質:SS400`、`PRFX:RAA4844`、`ユニット:U01`、`規格:SES` が候補になる。

### 現行Django暫定抽出器で取得できるDXFの範囲

- `TEXT`, `MTEXT`, `ATTRIB`, `ATTDEF` の文字列、レイヤー名、挿入座標。
- `INSERT` に続く `ATTRIB` をブロック参照としてまとめ、`block_references[].attributes[]` と個別 `texts[]` の両方に保持する。
- `DIMENSION` の表示値候補。
- `LINE`, `CIRCLE`, `ARC`, `ELLIPSE`, `LWPOLYLINE`, `POLYLINE`, `SPLINE`, `HATCH` の基本図形種別、レイヤー名、代表座標。
- レイヤー一覧、溶接注記候補、公差注記候補。
- ファイルパス・ファイル名と文字列からの客先/案件/装置カテゴリ/材質/PRFX/ユニット/規格辞書一致。

暫定抽出器では、図枠の印刷枠内外判定やラベル・値の高度な座標ペアリングは行わない。DXF側で図枠ブロック属性が取れる場合は、`block_references[]` と `texts[]` に保持し、Django側の正規化・図枠候補抽出へ渡す。

## タグ化するもの、属性保持に留めるもの

### 自動タグ化する

- 客先、案件、装置カテゴリ
- メーカー名
- 正式材質
- 表面処理、塗装
- 熱処理
- PRFX、ユニット番号
- SESなどの明確な規格識別子

### 属性候補として保持し、原則タグ化しない

- 寸法値
- 公差値
- 溶接記号
- バルーン
- 穴、長穴、切断線、ハッチングなどの形状特徴
- 質量、体積、重心、慣性モーメント

理由は、存在だけをタグにすると検索ノイズが大きくなるため。これらは図面レビューやRAG投入時の属性・根拠として保持する。

## 創屋への確認事項

1. STEPから製品名、部品名、部品階層、材質、質量特性をどのライブラリ/APIで取得できるか。
2. DXFからTEXT/MTEXT、ブロック属性、レイヤー名、寸法、公差、溶接記号を分離して取得できるか。
3. 図枠のラベルと値が別要素の場合、座標ペアリングまで抽出器側で行うか、Django側へ候補として渡すか。
4. 材質が色・レイヤー・ブロック名にしか無いケースがあるか。
5. 抽出値に推測を混ぜず、取得元フィールドと信頼度を添えて返せるか。
6. 実機SXNETで `SxOptExport.FILE_TYPE_STEP` / `FILE_TYPE_STP` / `FILE_TYPE_DXF` が利用できるか。まず `probe_icad_cad_export_types --output ...` またはC# runnerの `probe-cad-export-types` で定数一覧を確認し、定数名が異なる場合は `convert_icad_cad_formats --step-export-file-type ... --dxf-export-file-type ...` で形式別に数値を指定して検証する。
7. `convert_icad_cad_formats --extract` 後に `audit_converted_cad_extractions --drawing-id ... --output ...` を実行し、ICAD本体と変換後STEP/DXFで材質、部品名、図枠項目がどの程度一致するかを確認する。

## 2026-07-26 ローカル実機確認

- `probe_icad_cad_export_types --output C:\Users\s-iwata\Desktop\knowledge_system\output\sxopt_export_probe_2026-07-26.json` で、実機SXNETの `FILE_TYPE_STEP=11`、`FILE_TYPE_DXF=1` を確認した。形式別overrideなしで変換可能。
- `cad_data\9NK452WX90-00-LINER-A3-3D-01.icd` を対象に、ICADからSTEP/DXFへの変換を確認した。STEPはSXNETが `.stp` で出力したため、C#側は `.step` / `.stp` の両方をSTEP成果物として検出する。
- 変換後ファイル:
  - `output\cad_conversions_2026-07-26\53fa78f2-0489-471e-aef7-5edf780583e9\step\9NK452WX90-00-LINER-A3-3D-01.stp`
  - `output\cad_conversions_2026-07-26\53fa78f2-0489-471e-aef7-5edf780583e9\dxf\9NK452WX90-00-LINER-A3-3D-01.dxf`
- 変換後STEPは3D snapshot保存まで成功し、`step_product_names=["Assembly", "9NK452WX90-00-LINER-A3-3D-01-prt0"]`、`step_assembly_relationship_count=1` を確認した。
- 変換後DXFは2D snapshot保存まで成功し、`dxf_layers=["SX_DraftLine", "NoLayerName_001", "0", "NoLayerName_002", "NoLayerName_003"]` を確認した。今回のDXFサンプルではブロック属性は0件。
- 監査結果は `output\converted_cad_audit_2026-07-26.json` に保存した。ICAD本体にある材質/質量はSTEP側では同等に残らないため、STEP/DXFはICAD正本と完全同等ではなく、変換後に取れる情報を補完・比較対象として扱う。
- DXF変換時、SXNET export自体は成功して結果JSONも生成されたが、runner終了待ちが長くなるケースがあった。Django側は、タイムアウト時でも変換結果JSONが存在する場合は成功済み成果物として読み取る。
- 変換後にICADの保存確認が表示された場合、保存は不要。`IcadExtraction.Runner.exe shutdown-icad --timeout-seconds 30` で保存なし終了できることを確認した。
