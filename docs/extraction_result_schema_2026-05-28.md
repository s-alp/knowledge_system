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
      "ref_model_name": "string|null",
      "ref_model_path": "string|null",
      "is_external": true,
      "is_mirror": false,
      "is_read_only": false,
      "is_unloaded": false
    }
  ]
}
```

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
  "maker_keywords": [],
  "process_keywords": [],
  "heat_treatment_keywords": [],
  "inspection_keywords": [],
  "change_keywords": [],
  "issue_keywords": []
}
```

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

## 12. 2026-07-17 実装改訂

`docs/tagging_system_improvement_backlog_2026-07-17.md` の対応で、以下がこの文書の記述から変わった。
実装が正であり、以降はこの節を優先する。

### 12.1 `canonical_attributes` の追加キー

```json
{
  "customer_name_candidates": [],
  "equipment_category_candidates": [],
  "parts": [
    {
      "name": null,
      "comment": null,
      "tree_path": [],
      "ref_model_name": null,
      "ref_model_path": null,
      "is_external": false,
      "is_mirror": false,
      "is_unloaded": false
    }
  ],
  "spec_names": [],
  "match_evidence": {
    "customer_name": [{ "value": "コマツ小山", "field": "top_part_ex_info", "token": "...", "alias": "コマツ小山" }],
    "equipment_category": [],
    "maker_keywords": [],
    "spec_names": []
  }
}
```

- `spec_tokens` は生トークンのみ。辞書一致した正規規格名は `spec_names` に分離した。
- `parts` は部品単位の対応関係(名前・コメント・階層・参照)を構造のまま保持する。
- 照合は NFKC 正規化 + casefold 後に行い、ASCII 候補は語境界一致(`ses` が `hoses` に一致しない)。
- `extraction_status` は warnings があると `partial` になる。
- 複数客先/装置候補がある場合は `confidence_summary` を1段階下げる。

### 12.2 `derived_tags` の形(改訂)

```json
[
  {
    "tag": "装置:ガントリー",
    "namespace": "装置",
    "value": "ガントリー",
    "source": "equipment_category",
    "confidence": "high",
    "manual_flag": false,
    "tag_rule_version": "1.1.0",
    "evidence": [{ "value": "ガントリー", "field": "part_comments", "token": "...", "alias": "gantry" }]
  }
]
```

- 2D/3D 競合属性由来のタグは除外せず `confidence=low` で残す。

### 12.3 `manual_overrides` の形(実装準拠)

キーは実装どおり camelCase とする(§8 の snake_case 表記は旧案)。

```json
{
  "canonicalAttributes": {
    "equipment_category": { "value": "ガントリー" }
  },
  "derivedTags": {
    "added": ["工程:熱処理"],
    "removed": ["装置:ロボット"]
  }
}
```

- 補正保存はキー単位マージ。値に `null` を渡した項目だけ補正解除される。
- `derivedTags.added` / `removed` は累積集合で、追加→削除・削除→再追加は相殺される。
- 確定値は常に `自動抽出値 + manual_overrides` の合成として再計算されるため、再抽出・再正規化後も手動補正は消えない。

### 12.4 統合結果の永続化

- `DrawingComposedMetadata`(drawing 1:1)に統合済みの属性・タグ・競合を保存する。
- 更新契機: 抽出成功時、手動補正保存時、`re_normalize_snapshots` 実行時。
- 一覧フィルタと RAG 投入はこの保存値を読む。

### 12.5 辞書と再正規化

- 辞書は `TagDictionaryEntry`(kind: customer / equipment_category / maker / spec)が正本。DB が空の kind は seed 定数へフォールバックする。
- `python manage.py seed_tag_dictionaries` で seed を投入できる。
- `python manage.py re_normalize_snapshots [--stale-only] [--drawing-id ID] [--mode 2d|3d]` で、ICAD 再抽出なしに保存済み raw_extract から正規化・タグ生成をやり直せる。

### 12.6 一覧 API の契約

`GET /api/v1/drawing-metadata/registrations` は envelope 形式で返す。

```json
{ "items": [], "page": 1, "pageSize": 50, "total": 0 }
```

クエリ: `customer`, `equipmentCategory`, `tag`(部分一致), `mode`, `jobStatus`, `page`, `pageSize`。
同一 `sourcePath` の再登録は 400 で拒否する。

## 13. 結論

- スキーマは `生抽出` と `意味付け済みデータ` を必ず分ける。
- C# は `raw_extract` まで、Django は `canonical_attributes` 以降を主担当にする。
- この形にすると、抽出ロジック改善とタグ付与ルール改善を独立して回せる。
- 2D の未検証 geometry は warning で明示し、黙って捨てない。
