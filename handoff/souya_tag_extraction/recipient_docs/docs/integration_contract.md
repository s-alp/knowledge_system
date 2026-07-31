# Python組み込み・入出力契約

## 1. Pythonパッケージ

Python 3.11以上で動作します。Djangoへの依存はありません。

```powershell
python -m pip install ".\python"
```

## 2. CLI

```powershell
icad-tag-extraction `
  --input "<C# raw JSON、STEP、またはDXF>" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output "<出力JSON>"
```

入力と出力に同じパスは指定できません。入力ファイルが存在しない場合、不正JSON、未対応拡張子、辞書形式不正の場合は終了コード`0`以外で停止します。

## 3. Python API

```python
from icad_tag_extraction import (
    ExtractionConfig,
    MappingDictionaryProvider,
    process_extraction,
)

config = ExtractionConfig(
    schema_version="1.0.0",
    normalizer_version="1.1.0",
    tag_rule_version="1.1.0",
)
provider = MappingDictionaryProvider(dictionary_payload)

result = process_extraction(
    csharp_raw_payload,
    config=config,
    dictionary_provider=provider,
)
```

`process_extraction()`は入力objectを処理し、結果objectを返します。DB、ファイル、外部APIは更新しません。

## 4. 処理結果

処理結果は次のキーを持ちます。

| キー | 内容 |
|---|---|
| `schema_version` | 入出力契約のバージョン |
| `normalizer_version` | 正規化処理のバージョン |
| `tag_rule_version` | タグ生成規則のバージョン |
| `source_file` | 入力ファイルの出所 |
| `source_format` | `icad`、`step`、`dxf` |
| `source_kind` | `2d`または`3d` |
| `raw_extract` | 入力形式ごとの抽出結果 |
| `canonical_attributes` | 共通キーへ正規化した属性 |
| `derived_tags` | 根拠付きタグの配列 |
| `warnings` | 抽出・正規化時の警告 |

結果全体は`schemas\icad-tag-extraction-result.v1.schema.json`で検証できます。

## 5. JSON Schema

| ファイル | 用途 |
|---|---|
| `icad-csharp-raw-extraction.v1.schema.json` | C#または汎用抽出処理が返すraw JSON |
| `icad-canonical-attributes.v1.schema.json` | 共通属性 |
| `icad-derived-tags.v1.schema.json` | 根拠付きタグ |
| `icad-tag-extraction-result.v1.schema.json` | Python処理結果全体 |

JSON SchemaはDraft 2020-12です。外部契約として利用する場合は、ファイル名だけでなく`schema_version`も保存してください。

JSONのキー、型、必須条件を変更する場合は、既存データとの互換性を確認し、必要に応じてSchemaのバージョンを更新してください。`normalizer_version`と`tag_rule_version`は、再処理時に結果差分を判定するために保存してください。

## 6. 辞書

辞書JSONは次の7種別をobjectとして持つ必要があります。

- `customer`
- `equipment_category`
- `project`
- `maker`
- `spec`
- `heat_treatment`
- `part_name`

形式は`正規名: [別名...]`です。

```json
{
  "customer": {
    "顧客A": ["customer-a", "customer a"]
  },
  "equipment_category": {},
  "project": {},
  "maker": {},
  "spec": {},
  "heat_treatment": {},
  "part_name": {}
}
```

組み込み先のDBで辞書を管理する場合は、同じ形式のmappingを`MappingDictionaryProvider`へ渡してください。

## 7. 保存時の推奨項目

最低限、次を同じ処理単位で保存すると、後から抽出根拠と規則バージョンを追跡できます。

- 入力ファイルの識別子
- `source_file`
- `raw_extract`
- `canonical_attributes`
- `derived_tags`
- `warnings`
- `schema_version`
- `normalizer_version`
- `tag_rule_version`
- 処理日時

手動補正を追加する場合は、自動抽出結果を直接書き換えず、手動値と自動値を別に保持してください。

## 8. 含まれない統合処理

次の処理は、組み込み先の要件に合わせて実装してください。

- DBへの保存
- APIの認証と認可
- 非同期ジョブと再実行
- 2D／3D結果の統合
- 手動補正の履歴
- 検索インデックスまたはRAGへの登録
- 画面表示とレビュー
