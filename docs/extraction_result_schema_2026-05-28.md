# 抽出結果スキーマ（現行保存・正規化契約）

- 作成日: 2026-05-28
- 最終更新日: 2026-07-30
- 文書状態: **独立Python処理結果・Django保存・canonical・タグ・手動補正の正本**
- 目的: C# 抽出コアの出力 JSON、独立Pythonコアの処理結果、Django 側で保存するタグ・属性データの形を固定する。

> **現行契約について:** Windows agentの起動設定、HTTP API、C#入出力JSONの正本は
> `docs/windows_extraction_agent_api_design_2026-07-29.md` とする。
> 本資料は独立Pythonコアの入出力、Django保存スキーマ、正規化属性、派生タグ、手動補正の詳細資料として使用する。
> 全体の処理順序、タグ一覧、UI、運用コマンドは
> [`tag_extraction_and_assignment_current_spec_2026-07-29.md`](tag_extraction_and_assignment_current_spec_2026-07-29.md) を参照する。

## 1. スキーマの考え方

- C# 側は「意味付け前の生抽出」を返す。
- Django非依存の `backend/icad_tag_extraction` は、その結果を `canonical_attributes` と `derived_tags` に変換する。
- Django 側はDB辞書を独立コアへ注入し、raw、canonical、tags、手動補正を保存する。
- 1 回の抽出で以下 4 層を持つ。
  - `raw_extract`
  - `canonical_attributes`
  - `derived_tags`
  - `manual_overrides`

## 2. C# 抽出コアの出力 JSON

```json
{
  "input_path": "string",
  "source_file": {
    "full_path": "string",
    "directory_path": "string|null",
    "file_name": "string",
    "file_name_without_extension": "string",
    "extension": "string",
    "sx_net_input_path": "string",
    "sx_net_input_strategy": "original|windows_short_path|temporary_copy|temporary_copy_forced",
    "used_sx_net_alternate_path": false,
    "original_path_length": 0,
    "sx_net_input_path_length": 0
  },
  "source_format": "icad",
  "source_kind": "2d|3d",
  "extractor_name": "icad-csharp-extractor",
  "extractor_version": "string",
  "elapsed_ms": 0,
  "warnings": [],
  "raw_extract": {}
}
```

### 2026-05-28 実装反映

- 実装では `extractor_name=icad-csharp-extractor`
- `extractor_version=1.0.0`
- JSON 出力は `SnakeCaseNamingStrategy` で統一
- `input_path` と `source_file.full_path` は原本ICADパスを保持する
- SXNETへ渡すパスは `source_file.sx_net_input_path` に保持する
- Django側の登録・起票では原本パス全体が長いことだけを理由に拒否しない。長パスは抽出Runnerで短いSXNET入力へ退避し、原本パスは検索・追跡用属性として残す
- 長パスなどでSXNETが開けない可能性がある場合、Runnerは `windows_short_path` を優先し、それでも短くならない場合だけ `temporary_copy` を使う
- ブラウザアップロード由来のICADは、保存先パスが深くなりSXNETの開けない条件に寄りやすいため、Djangoから `temporary_copy_forced` を指定して短い一時パスで開く
- `temporary_copy` は外部参照解決に影響し得るため、`warnings[].code=sxnet_input_path_staged` を出す
- `warnings` は以下の形を基本にする

```json
[
  {
    "code": "geometry_layer_count_mismatch",
    "message": "2D geometry count and layer count did not match in a view. Layer numbers were omitted for this view."
  }
]
```

### 必須項目

- `input_path`
- `source_file`
- `source_format`
- `source_kind`
- `extractor_name`
- `extractor_version`
- `elapsed_ms`
- `warnings`
- `raw_extract`

### 機械可読な境界契約

`schemas/tag_extraction/`のJSON Schema Draft 2020-12を機械検証の正本とする。

| ファイル | 検証対象 |
|---|---|
| `icad-csharp-raw-extraction.v1.schema.json` | C#およびgeneric抽出器が返すrawエンベロープ |
| `icad-canonical-attributes.v1.schema.json` | 独立Pythonコアが返すcanonical属性 |
| `icad-derived-tags.v1.schema.json` | 独立Pythonコアが返す派生タグ |
| `icad-tag-extraction-result.v1.schema.json` | raw、canonical、タグを含む単体処理結果 |

Schemaは`scripts/generate_tag_extraction_schemas.py`で生成し、C# raw部分は`src/IcadExtraction.Contracts/Models.cs`のDTOから導出する。変更時は`python scripts\generate_tag_extraction_schemas.py --check`を実行し、2D/3D例とPython処理結果を`jsonschema`で検証する。

## 3. `raw_extract` の 3D 形

```json
{
  "top_part": {
    "name": "string|null",
    "comment": "string|null",
    "ex_info": "string|null"
  },
  "parts": [
    {
      "tree_path": ["Top", "Sub1", "PartA"],
      "name": "string|null",
      "comment": "string|null",
      "ex_info": "string|null",
      "ex_info_fields": {
        "User_WBZAI1": "string"
      },
      "ref_model_name": "string|null",
      "ref_model_path": "string|null",
      "is_external": true,
      "is_mirror": false,
      "is_read_only": false,
      "is_unloaded": false,
      "materials": [
        {
          "matid": "SUS304",
          "name": "SUS304",
          "specific_gravity": 7.93,
          "element_count": 2,
          "raw_fields": {
            "matid": "SUS304",
            "name": "SUS304",
            "spe_grav": "7.93"
          }
        }
      ]
    }
  ],
  "material_probe_status": "available|not_attempted|failed",
  "materials": [
    {
      "matid": "SUS304",
      "name": "SUS304",
      "specific_gravity": 7.93,
      "element_count": 2
    }
  ]
}
```

`parts[].materials` は `SxInfPartTree.entpart` から得た `SxEntPart.getInfMaterialList()` の結果である。SXNET資料上、このメソッドは子パーツ内の要素を含まないため、親子を合算せず各部品ノードの根拠として保持する。部品別APIが失敗した場合は `warnings[].code=part_material_probe_failed` に部品パス付きで記録し、抽出全体は継続する。

## 4. `raw_extract` の 2D 形

```json
{
  "texts": [
    {
      "text_lines": ["string"],
      "line_count": 1,
      "position": { "x": 0, "y": 0 },
      "source_type": "text|label"
    }
  ],
  "dimensions": [
    {
      "value_1": "string|null",
      "value_2": "string|null",
      "front_word": "string|null",
      "back_word": "string|null",
      "upper_tol": "string|null",
      "lower_tol": "string|null",
      "mark_2": "string|null",
      "mark_3": "string|null"
    }
  ],
  "tolerances": [
    {
      "text": "string"
    }
  ],
  "geometry_primitives": [
    {
      "geometry_type": "SxGeomFinishMark",
      "position_x": 0,
      "position_y": 0,
      "inside_print_area": true,
      "mark_type": 0,
      "side_length": 0,
      "width": 0,
      "color": 0,
      "summary": "string"
    }
  ],
  "weld_notes": [
    {
      "text": "string"
    }
  ],
  "balloons": [
    {
      "text": "string|null"
    }
  ],
  "referenced_parts": [
    {
      "entity_type": "rpart|refer",
      "view_name": "string|null",
      "layer_no": 0,
      "position_x": 0,
      "position_y": 0,
      "inside_print_area": true,
      "name": "string|null",
      "comment": "string|null",
      "part3d_name": "string|null",
      "ref_model_name": "string|null",
      "ref_vs_name": "string|null",
      "kind": 0,
      "is_empty": false,
      "is_mirror": false,
      "scale": 1.0,
      "angle": 0.0,
      "summary": "string"
    }
  ]
}
```

## 5. Django 保存スキーマ

```json
{
  "raw_extract": {},
  "canonical_attributes": {},
  "derived_tags": [],
  "manual_overrides": {}
}
```

## 6. `canonical_attributes` の最小定義

```json
{
  "drawing_number": null,
  "drawing_number_candidates": [],
  "drawing_name": null,
  "part_name": null,
  "product_name": null,
  "equipment_name": null,
  "unit_name": null,
  "revision": null,
  "source_format": "icad",
  "source_kind": "2d",
  "document_kind": null,
  "customer_name": null,
  "project_name": null,
  "equipment_category": null,
  "module_name": null,
  "status": null,
  "owner": null,
  "design_purpose": null,
  "paper_size": null,
  "extraction_status": "success|partial|failed",
  "ocr_used": false,
  "confidence_summary": "high|medium|low",
  "top_part_name": null,
  "top_part_comment": null,
  "top_part_ex_info": null,
  "part_names": [],
  "part_comments": [],
  "part_tree_paths": [],
  "ref_model_names": [],
  "ref_model_paths": [],
  "external_part_exists": false,
  "mirror_part_exists": false,
  "unresolved_part_exists": false,
  "global_moment": { "x": 1.1, "y": 2.2, "z": 3.3 },
  "gravity_moment": { "ix": 4.4, "iy": 5.5, "iz": 6.6 },
  "main_moment": { "Ixx": 7.7, "Iyy": 8.8 },
  "inertia_moment_candidates": [
    {
      "kind": "global",
      "label": "全体座標系慣性モーメント",
      "values": { "x": 1.1, "y": 2.2, "z": 3.3 },
      "unit_name": "mm-kg",
      "source": "3d_mass_properties.global_moment",
      "confidence": "medium",
      "reason": "SXNETのSxInfMassから慣性モーメント値を取得できたため、検索タグではなく3D解析属性として保持します。"
    }
  ],
  "inertia_moment_candidate_count": 1,
  "text_tokens": [],
  "label_texts": [],
  "title_block_fields": {},
  "dimension_count": 1,
  "dimension_values": [],
  "dimension_symbols": [],
  "dimension_tolerance_count": 1,
  "dimension_tolerance_values": ["+0.1", "-0.1"],
  "geometric_tolerance_count": 1,
  "tolerance_texts": [],
  "tolerance_candidates": [
    {
      "value": "±0.1",
      "evidence_text": "±0.1",
      "view_name": "SHEET1",
      "layer_no": 1,
      "position_x": 100.0,
      "position_y": 50.0,
      "position_z": 0.0,
      "inside_print_area": true,
      "print_frame_no": 1,
      "source": "2d_tolerance",
      "confidence": "medium",
      "reason": "2D図面要素から値と位置情報を取得できたため、検索タグではなく図面レビュー用の属性候補として保持します。"
    }
  ],
  "tolerance_candidate_count": 1,
  "weld_instruction_count": 1,
  "weld_types": ["すみ肉"],
  "weld_note_texts": [],
  "weld_note_candidates": [],
  "weld_note_candidate_count": 0,
  "balloon_keys": [],
  "balloon_candidates": [],
  "balloon_candidate_count": 0,
  "surface_treatment_tokens": [],
  "view_reference_candidates": [
    {
      "kind": "arrow_view",
      "label": "矢視候補",
      "geometry_type": "SxGeomArrowView",
      "evidence_text": "A矢視",
      "view_name": "SHEET1",
      "layer_no": 2,
      "position_x": 21.0,
      "position_y": 22.0,
      "position_z": 0.0,
      "end_x": null,
      "end_y": null,
      "end_z": null,
      "inside_print_area": true,
      "print_frame_no": 1,
      "source": "2d_view_reference_geometry",
      "confidence": "medium",
      "reason": "2D図面の矢視・切断線・シンボル要素から、別ビューや詳細図へつながる可能性があるためレビュー用候補として保持します。"
    }
  ],
  "view_reference_candidate_count": 1,
  "curve_section_candidates": [
    {
      "kind": "spline_curve",
      "label": "スプライン曲線候補",
      "geometry_type": "SxGeomSpline2D",
      "evidence_text": "spline outer curve",
      "view_name": "SHEET1",
      "layer_no": 3,
      "position_x": 31.0,
      "position_y": 32.0,
      "position_z": 0.0,
      "point_count": 4,
      "inside_print_area": true,
      "print_frame_no": 1,
      "source": "2d_spline_geometry",
      "confidence": "medium",
      "searchable_tag": false,
      "tag_adoption_status": "excluded",
      "reason": "2D図形のスプライン要素から曲線外形の可能性を確認できるため、検索タグではなく図面レビュー用候補として保持します。"
    }
  ],
  "curve_section_candidate_count": 1,
  "spec_tokens": [],
  "part_keywords": [],
  "material_keywords": [],
  "unresolved_material_keywords": [],
  "part_material_candidates": [
    {
      "part_path": "Top.Sub1.PartA",
      "part_name": "PartA",
      "material_id": "SUS304",
      "material_name": "SUS304",
      "canonical_material": "SUS304",
      "material_status": "formal",
      "specific_gravity": 7.93,
      "source": "3d_part_material",
      "confidence": "high",
      "reason": "ICAD部品ツリーのSxEntPartから材質一覧を取得できたため、当該部品の材質候補として採用しました。"
    }
  ],
  "part_material_candidate_count": 1,
  "maker_keywords": [],
  "process_keywords": [],
  "heat_treatment_keywords": [],
  "inspection_keywords": [],
  "change_keywords": [],
  "issue_keywords": []
}
```

### 2026-07-29 名称・図面番号契約

- `drawing_number` は部品、製品、装置、ユニットの共通図面番号である。
- `drawing_number_candidates` は値、取得元、信頼度、根拠を保持する。採用順は、2D図枠の明示値、図面文字とファイル名の一致候補、ファイル名の図面番号候補とする。
- `drawing_name`、`part_name`、`product_name`、`equipment_name`、`unit_name` は同一項目ではない。明示ラベルごとに分けて保存する。
- 2Dと3Dが競合した場合、名称と図面番号は図面上の2D明示値を優先し、競合値は消さずに監査情報へ残す。
- `top_part_name` は3Dモデルの最上位識別子であり、製品・装置・ユニット名または部品名として使用しない。
- `top_part_comment` は、図番だけ、変更説明、参照説明、私用領域文字、置換文字を除外した場合だけ名称候補にできる。
- 3D子部品の `part_names` は構成証跡であり、図面全体やユニット全体の名称へ昇格させない。
- ICAD文字の印刷範囲は、枠内外判定が1件以上ある場合だけ `inside=true` を信頼する。全文字がunknownの場合は、判定材料がないため文字を全件除外せず、名称ラベル解析へ渡す。
- `SFF-424 L=1572`等の型式・寸法トークンだけの値と、`型式`等の図枠見出しは名称として確定しない。候補原文は監査・手動確認用に保持する。
- 名称・図枠候補はICAD原文、印刷枠、ビュー、レイヤー、文字座標、明示ラベル、タグ辞書だけで分類し、外部AIは使用しない。
- `★`、`※`等の先頭注記記号はraw原文に残し、表示名称からだけ除去する。

### アセンブリ本体と外部パーツの分離

- `internal_part_names` / `internal_part_tree_paths` / `internal_part_ex_info_fields` はアセンブリ本体側だけを保持する。
- `external_part_names` / `external_part_tree_paths` / `external_part_ex_info_fields` は外部参照パーツ側だけを保持する。
- `internal_part_material_keywords` と `external_part_material_keywords` を別々に保持する。
- `part_name_candidates` は本体候補、`external_part_name_candidates` は外部パーツ候補とする。
- `part_material_candidates` は本体候補、`external_part_material_candidates` は外部パーツ候補とする。
- 外部パーツの名称、材質、図番、付加情報は検索・構成証跡として保存できるが、アセンブリ本体の正式名称・正式材質・正式図番へ昇格させない。
- 2D/3Dビューワー詳細では、`本体材質`、`外部パーツ名称`、`外部パーツ材質`、本体／外部の付加情報件数を別行で表示する。

画面向け製品・部品payloadは `icad_knowledge_entities.v4` とし、共通で次を返す。

```json
{
  "schemaVersion": "icad_knowledge_entities.v4",
  "items": [
    {
      "entityKind": "product|part",
      "name": "string|名称未抽出",
      "drawingNumber": "string|null",
      "partNumber": "string|null",
      "directPartCount": "integer|null",
      "childAssemblyCount": "integer|null",
      "childPartCount": "integer|null",
      "descendantPartCount": "integer|null",
      "partCountByDepth": {
        "1": 12,
        "2": 37
      }
    }
  ]
}
```

- `drawingNumber` は製品・装置・ユニットと部品の両方に返す。
- `partNumber` は部品だけに返す互換項目で、値は必ず `drawingNumber` と同一にする。
- `directPartCount` は深さ1の全パーツ出現数であり、一覧の「部品数」に使用する。
- `childAssemblyCount` / `childPartCount` は深さ1を子構造の有無で分けた内訳とする。
- `descendantPartCount` は深さ1以上の全パーツ出現数、`partCountByDepth` は深さ別の出現数とする。
- 階層を復元できない場合は外部参照数などで代用せず、件数と階層別集計を `null` にする。
- 名称を確定できない場合、`top_part_name` やファイル名全体を代入せず `名称未抽出` を返す。
- 2D/3Dビューワーは、製品・装置・ユニット一覧にも図面番号を表示し、部品一覧の従来「部品番号」表示は「図面番号」とする。

`material_keywords` は正式材質辞書で `formal` に分類できた値だけを通常の材質タグに使う。`unresolved_material_keywords` は `ZZZ`, `75`, `CDQ` など客先固有または意味未解決の材質コードを保持する。`RM` のように材質欄ではなく区分値として扱う値、重量文字列、U+FFFDを含む文字化け済み文字列は `excluded` として材質タグから除外する。未解決材質は捨てず、検索・分類タグにはせず、レビュー属性とRAG投入時の `reviewFlags` に残す。

## 7. `derived_tags` の形

```json
[
  {
    "tag": "装置:ガントリー",
    "source": "equipment_category",
    "confidence": "high",
    "manual_flag": false
  },
  {
    "tag": "寸法公差あり",
    "source": "dimension_tolerance_count",
    "confidence": "high",
    "manual_flag": false
  },
  {
    "tag": "硬度:HRC",
    "source": "hardness_spec_values",
    "confidence": "medium",
    "manual_flag": false
  }
]
```

### ルール

- `tag` は表示値
- `source` は元属性
- `confidence` は `high|medium|low`
- `manual_flag` は手動で追加・修正したか
- 寸法・公差・溶接は存在または明示分類をタグ化し、具体値は `canonical_attributes` に保持する
- 硬度は `HRC` / `HV` の尺度をタグ化し、`HRC58-62` 等の具体値は `hardness_spec_values` に保持する

## 8. `manual_overrides` の形

```json
{
  "canonical_attributes": {
    "equipment_category": {
      "value": "ガントリー",
      "updated_by": "user_id",
      "updated_at": "2026-05-28T00:00:00+09:00"
    }
  },
  "derived_tags": {
    "added": ["装置:ガントリー"],
    "removed": ["装置:ロボット"]
  }
}
```

## 9. 信頼度ルールの初期案

### 高

- ICAD ネイティブで明示的に取れた
- top part や part name など、型が明確

### 中

- 2D 文字列から辞書一致で推定できた
- PDF テキストから見出し/本文一致で取れた

### 低

- OCR 起点
- 曖昧一致
- 複数候補から優先順位で仮採用

## 10. バージョニング

- `extractor_version`
- `schema_version`
- `normalizer_version`
- `tag_rule_version`

を持たせ、再抽出時に差分比較できるようにする。

## 11. 検証時の必須確認

- 3D サンプルで `raw_extract.parts` が階層付きで取れる
- 2D サンプルで `texts`, `dimensions`, `weld_notes` が分離できる
- `canonical_attributes` へ正規化した時に、案件系と規格系が混ざらない
- `derived_tags` が属性から再生成できる
- `manual_overrides` を後から適用しても元抽出値が残る

## 12. 結論

- スキーマは `生抽出` と `意味付け済みデータ` を必ず分ける。
- C# は `raw_extract` まで、独立Pythonコアは `canonical_attributes` と `derived_tags` の生成を担当する。
- Djangoは辞書DB、保存、非同期ジョブ、補正、APIを担う任意の統合アダプターとし、正規化・タグ生成の必須依存にはしない。
- この形にすると、抽出ロジック改善とタグ付与ルール改善を独立して回せる。
- 2D の未検証 geometry は warning で明示し、黙って捨てない。
