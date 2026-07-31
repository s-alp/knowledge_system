# CADタグ・属性抽出パッケージ 利用ガイド

このパッケージには、ICAD・STEP・DXFから属性を抽出し、共通形式へ正規化してタグを生成するためのソースコードと実行例が含まれています。

## 1. 含まれる機能

- ICAD 2D／3DをSXNETで読み取るC#抽出処理
- ICADからDXF／STEPへ変換するC#処理
- C#の抽出結果、STEP、DXFを共通属性へ正規化するPython処理
- 文字列・属性・辞書から、根拠付きタグを生成するPython処理
- C#とPythonの入出力を定義するJSON Schema
- 初期辞書、2D／3Dサンプル、単体テスト
- Python処理を確認するDocker構成

DBへの保存、Web API、画面、RAG、ビューワーは含まれていません。Pythonの処理結果を組み込み先のDBやAPIへ保存してください。

## 2. 処理の流れ

```text
ICADファイル
  └─ Windows／C#／SXNETで抽出
       └─ C# raw JSON

STEP・DXF
  └─ Pythonで直接解析

C# raw JSON・STEP・DXF
  └─ Pythonで共通属性へ正規化
       └─ 初期辞書または運用辞書を照合
            └─ canonical_attributes + derived_tags
```

ICADから取得できる項目と、STEP／DXFへ変換した場合の差は、[`docs/extraction_reference.md`](docs/extraction_reference.md)を参照してください。

## 3. フォルダー構成

```text
├─ README.md
├─ manifest.json
├─ csharp/
│  ├─ IcadExtraction.sln
│  ├─ src/
│  └─ tests/
├─ python/
│  ├─ pyproject.toml
│  ├─ requirements-dev.txt
│  └─ icad_tag_extraction/
├─ tests/python/
├─ schemas/
├─ dictionaries/
│  └─ initial-dictionaries.json
├─ examples/
│  ├─ raw/
│  └─ results/
├─ scripts/
├─ docker/
└─ docs/
```

`manifest.json`には、同梱ファイルの相対パス、サイズ、SHA-256が記録されています。

## 4. Pythonを使った最短の動作確認

### 4.1 前提

- Python 3.11以上
- PowerShell 7以上
- Djangoは不要

パッケージのルートで次を実行します。

```powershell
python -m pip install ".\python"
```

C# 2Dサンプルを処理します。

```powershell
icad-tag-extraction `
  --input ".\examples\raw\csharp_raw_2d.v1.json" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\tagged_result.json"
```

正常終了すると、`tagged_result.json`へ`canonical_attributes`と`derived_tags`が出力されます。

### 4.2 同梱テスト

```powershell
python -m pip install -r ".\python\requirements-dev.txt"
python -m pytest ".\tests\python"
```

このテストでは、Djangoに依存せず処理できること、JSON Schemaが有効であること、2D／3Dサンプルが期待結果と一致することを確認します。

## 5. STEP／DXFの処理

```powershell
icad-tag-extraction `
  --input "C:\CAD\sample.step" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\step_tagged_result.json"
```

```powershell
icad-tag-extraction `
  --input "C:\CAD\sample.dxf" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\dxf_tagged_result.json"
```

入力と出力には異なるパスを指定してください。不正なJSON、未対応形式、不正な辞書形式を検出した場合は処理を中断します。

## 6. Dockerによる動作確認

DockerはPython処理だけを実行します。ICAD、SXNET、C# RunnerはWindows上で実行してください。

```powershell
docker compose -f ".\docker\docker-compose.yml" run --rm tag-extraction
```

`docker\data\input.json`を読み、`docker\data\output.json`へ結果を保存します。

## 7. Python APIへの組み込み

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

`process_extraction()`はDB、ファイル、外部APIを更新しません。返されたJSONの保存方法は[`docs/integration_contract.md`](docs/integration_contract.md)を参照してください。

## 8. 初期辞書

`dictionaries\initial-dictionaries.json`は次の7種別を持ちます。

- `customer`
- `equipment_category`
- `project`
- `maker`
- `spec`
- `heat_treatment`
- `part_name`

各種別は`正規名: [別名...]`形式です。正規名も照合候補へ自動追加されます。

```json
{
  "customer": {
    "顧客A": ["customer-a"]
  },
  "project": {}
}
```

辞書ファイルが存在しない場合や形式が不正な場合、自動的に別の辞書へ切り替えず、エラーとして処理を中断します。

## 9. ICADを使用する処理

ICADの抽出、DXF／STEP変換、Windows agentの起動には、Windows、ICAD、対応する`sxnet.dll`、.NET Framework 4.8が必要です。

ビルド方法と実行例は[`docs/icad_windows_operations.md`](docs/icad_windows_operations.md)を参照してください。

## 10. 関連資料

- [`docs/extraction_reference.md`](docs/extraction_reference.md): 入力形式ごとの抽出項目と制約
- [`docs/integration_contract.md`](docs/integration_contract.md): Python入出力、JSON Schema、辞書の組み込み契約
- [`docs/icad_windows_operations.md`](docs/icad_windows_operations.md): ICAD抽出、DXF／STEP変換、Windows agent
- `docs/CADタグ属性抽出_創屋様向け利用ガイド.pdf`: 本READMEと技術文書をまとめたPDF版
