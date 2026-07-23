# STEP/DXFタグ取得・自動付与の抽出元整理

- 作成日: 2026-07-23
- 目的: 創屋側でSTEP/DXFデータから何を抽出すれば、ナレッジシステム側のタグ・属性自動付与へつながるかを具体化する。

## 基本方針

- ICADと同じく、抽出器は意味付け前の `raw_extract` を出す。
- Django側で `canonical_attributes` へ正規化し、既存の `derived_tags` 生成ルールでタグ化する。
- STEPは3D CADとして `source_format=step`, `source_kind=3d` を使う。
- DXFは2D CADとして `source_format=dxf`, `source_kind=2d` を使う。
- 抽出不能な項目は空配列または `null` とし、推測値は入れない。
- 現行Django側には、外部ライブラリなしでSTEP/DXFファイルを直接読む暫定抽出器を入れている。STEPはヘッダ/文字列リテラル/PRODUCT系エンティティ、DXFはTEXT/MTEXT/ATTRIB/DIMENSION/基本図形を対象にする。
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
- 文字列中の材質パターン。例: `SUS304`, `S45C`, `SS400`, `A5052`。
- ファイルパス・ファイル名からの客先/案件/装置カテゴリ辞書一致。

暫定抽出器では、STEPの幾何形状そのものを解析した体積・質量・正確な部品階層までは確定しない。これらは詳細抽出器の追加対象。

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
- `DIMENSION` の表示値候補。
- `LINE`, `CIRCLE`, `ARC`, `ELLIPSE`, `LWPOLYLINE`, `POLYLINE`, `SPLINE`, `HATCH` の基本図形種別、レイヤー名、代表座標。
- ファイルパス・ファイル名と文字列からの客先/案件/装置カテゴリ/材質/PRFX/ユニット/規格辞書一致。

暫定抽出器では、図枠の印刷枠内外判定やラベル・値の高度な座標ペアリングは行わない。DXF側で図枠ブロック属性が取れる場合は、`texts[]` または将来の `title_block_fields` 相当候補として渡す。

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
