# 抽出結果スキーマ定義案

- 作成日: 2026-05-28
- 目的: C# 抽出コアの出力 JSON と、Django 側で保存するタグ・属性データの形を固定する。

## 1. スキーマの考え方

- C# 側は「意味付け前の生抽出」を返す。
- Django 側は、その結果を `canonical_attributes` と `derived_tags` に変換して保存する。
- 1 回の抽出で以下 4 層を持つ。
  - `raw_extract`
  - `canonical_attributes`
  - `derived_tags`
  - `manual_overrides`

## 2. C# 抽出コアの出力 JSON

```json
{
  "input_path": "string",
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
- `warnings` は以下の形を基本にする

```json
[
  {
    "code": "unsupported_geometry",
    "message": "Unhandled geometry type: SxGeomFoo"
  }
]
```

### 必須項目

- `input_path`
- `source_format`
- `source_kind`
- `extractor_name`
- `extractor_version`
- `elapsed_ms`
- `warnings`
- `raw_extract`

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
  "weld_notes": [
    {
      "text": "string"
    }
  ],
  "balloons": [
    {
      "text": "string|null"
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
  "drawing_name": null,
  "revision": null,
  "source_format": "icad",
  "source_kind": "2d",
  "document_kind": null,
  "customer_name": null,
  "project_name": null,
  "equipment_name": null,
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
  "text_tokens": [],
  "label_texts": [],
  "title_block_fields": {},
  "dimension_values": [],
  "dimension_symbols": [],
  "tolerance_texts": [],
  "weld_note_texts": [],
  "balloon_keys": [],
  "surface_treatment_tokens": [],
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

`material_keywords` は通常の材質タグに使う値、`unresolved_material_keywords` は `ZZZ`, `75`, `CDQ` など客先固有または意味未解決の材質コードを保持する。未解決材質は捨てず、`材質要確認:<値>` の低信頼タグとしてレビュー対象にする。

## 7. `derived_tags` の形

```json
[
  {
    "tag": "装置:ガントリー",
    "source": "equipment_category",
    "confidence": "high",
    "manual_flag": false
  }
]
```

### ルール

- `tag` は表示値
- `source` は元属性
- `confidence` は `high|medium|low`
- `manual_flag` は手動で追加・修正したか

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
- C# は `raw_extract` まで、Django は `canonical_attributes` 以降を主担当にする。
- この形にすると、抽出ロジック改善とタグ付与ルール改善を独立して回せる。
- 2D の未検証 geometry は warning で明示し、黙って捨てない。
