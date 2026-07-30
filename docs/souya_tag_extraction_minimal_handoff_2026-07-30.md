# 創屋向け CADタグ・属性抽出 最小ソース引き渡し手順

- 文書状態: **現行最小パッケージ仕様**
- 基準日: 2026-07-30
- 対象:
  - `src/IcadExtraction.*`
  - `backend/icad_tag_extraction`
  - `schemas/tag_extraction`
  - `scripts/build_souya_tag_extraction_package.py`

## 1. 目的と供給範囲

本パッケージは、創屋側から依頼された次の範囲だけを切り出して渡す。

1. ICAD 2D/3Dから意味付け前の事実を抽出するC#ソース
2. C# raw JSON、STEP、DXFを共通属性へ正規化するPythonソース
3. 文字列・属性・辞書から根拠付きタグを生成するPythonソース
4. C#とPythonの境界を固定するJSON Schema
5. 初期辞書、サンプルJSON、単体テスト、組み込み手順
6. ICADからDXF/STEPへ変換するC#機能と単独実行スクリプト

本番ナレッジシステムのDB/APIへの登録、画面、RAG、ビューワー、Django管理画面は供給本体に含めない。
Django adapterは本リポジトリ内で現行挙動の同等性を確認するために残すが、最小パッケージには含めない。

## 2. 責務境界

```text
ICAD .icd
  ↓ Windows / C# + SXNET
C# raw extraction JSON
  ↓ JSON Schema: icad-csharp-raw-extraction.v1
Python icad_tag_extraction
  ├─ normalization
  ├─ dictionary provider
  └─ tag builder
  ↓
canonical_attributes + derived_tags
  ↓ 創屋側で実装
本番DB / API / 検索インデックス
```

- C#はICAD内の事実を`raw_extract`へ出力し、客先・案件等の意味付けを行わない。
- Pythonはrawを正規化し、注入された辞書と規則からタグを生成する。
- PythonコアはDjangoをimportせず、DB・外部APIへアクセスしない。
- 創屋側の保存処理は、Pythonの処理結果JSONを受け取って実装する。

どこから何を抽出するかの完全な一覧は
`docs/cad_tag_extraction_sources_for_souya_2026-07-28.md`を参照する。

## 3. 最小パッケージ構成

```text
souya_tag_extraction_minimal_2026-07-30/
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
├─ tests/
│  └─ python/
│     └─ test_distribution.py
├─ schemas/
├─ dictionaries/
│  └─ initial-dictionaries.json
├─ examples/
│  ├─ raw/
│  └─ results/
├─ scripts/
│  └─ convert_icad_standalone.ps1
├─ docker/
│  ├─ Dockerfile
│  └─ docker-compose.yml
└─ docs/
```

`manifest.json`には全ファイルの相対パス、サイズ、SHA-256を記録する。
同名出力先が既に存在する場合、生成スクリプトは上書きせず停止する。

## 4. Python単独実行

### 4.1 前提

- Python 3.12
- Django不要
- STEP/DXF解析、正規化、タグ生成のruntime外部依存なし

開発・Schema検証時だけ`requirements-dev.txt`の`pytest`と`jsonschema`を使用する。

### 4.2 インストール

```powershell
python -m pip install ".\python"
```

### 4.3 C# raw JSONから処理

```powershell
icad-tag-extraction `
  --input ".\examples\raw\csharp_raw_2d.v1.json" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\tagged_result.json"
```

### 4.4 STEP/DXFから処理

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

入力と出力に同じパスは指定できない。不正JSON、未対応形式、辞書形式不正は処理を中断する。

## 5. Python API組み込み

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

`process_extraction()`はファイル、DB、外部APIを更新しない。
返された`canonical_attributes`と`derived_tags`の保存先は創屋側で決定する。

## 6. 辞書契約

辞書JSONの最上位キーは次の7種別である。

- `customer`
- `equipment_category`
- `project`
- `maker`
- `spec`
- `heat_treatment`
- `part_name`

各種別は`正規名: [別名...]`形式とする。正規名自体も照合候補へ自動追加される。

```json
{
  "customer": {
    "コマツ小山": ["komatsu koyama"]
  },
  "project": {}
}
```

不明な辞書種別、空の正規名、文字列配列でない別名はエラーにする。
辞書ファイルの不存在・不正をseedへ自動フォールバックしない。

## 7. JSON Schema

| ファイル | 契約 |
|---|---|
| `icad-csharp-raw-extraction.v1.schema.json` | C# RunnerからPythonへ渡すraw抽出 |
| `icad-canonical-attributes.v1.schema.json` | Python正規化後の全キー |
| `icad-derived-tags.v1.schema.json` | 根拠付きタグ配列 |
| `icad-tag-extraction-result.v1.schema.json` | Python処理結果全体 |

SchemaはJSON Schema Draft 2020-12である。
元リポジトリの`scripts/generate_tag_extraction_schemas.py --check`により、`Models.cs`とPython canonicalキーからの
生成結果が保存済みSchemaと一致するか確認する。最小パッケージでは生成済みSchemaと配布専用テストを正とする。

## 8. C#実行とICAD→DXF/STEP変換

C#のビルド・SXNET配置・ICAD実行条件は
`docs/windows_extraction_agent_api_design_2026-07-29.md`を参照する。

ICAD→DXF/STEP変換は`IcadExtraction.Runner convert-cad`または
`scripts/convert_icad_standalone.ps1`を使用する。詳細は
`docs/icad_dxf_step_standalone_conversion_guide_2026-07-29.md`を参照する。

変換後STEP/DXFはICAD正本と同等ではない。材質、質量、内部・外部パーツ区分、
正式な部品名が必要な場合はICAD正本からSXNETで直接抽出する。

## 9. Docker

DockerはPythonコアの再現実行用であり、ICAD/SXNET/C# Runnerは実行しない。
ICAD処理はWindowsホストまたはWindows agentで行う。

```powershell
docker compose -f ".\docker\docker-compose.yml" run --rm tag-extraction
```

`data/input.json`を読み、`data/output.json`へ結果を保存する例である。

## 10. 受入確認

リポジトリ側では次を確認してからパッケージを生成する。

1. 独立Pythonコアのテスト
2. Django adapterと独立コアの2D/3D完全一致
3. C# solutionテスト
4. JSON Schema自己検証と現行コードからの再生成一致
5. サンプルrawと処理結果のSchema検証
6. 最小パッケージ内でDjangoなしのCLI実行
7. コメント監査とタグ関連ドキュメント監査

受領した最小パッケージ単体では、次を実行する。

```powershell
python -m pip install ".\python"
python -m pip install -r ".\python\requirements-dev.txt"
python -m pytest ".\tests\python"
```

このテストはDjangoを読み込まないこと、JSON Schema自体の妥当性、C# 2D/3D入力例の妥当性、同梱済み期待結果との完全一致を確認する。

生成コマンド:

```powershell
python ".\scripts\build_souya_tag_extraction_package.py"
```

## 11. 既知の境界

- 創屋本番DB/APIへの書き込みは未接続であり、納品コアも書き込まない。
- ICAD/SXNETの実抽出とDXF/STEP変換はWindows＋ICAD環境が必要である。
- DockerはPython側だけを対象とする。
- 手動補正、2D/3D合成、レビュー画面、RAG payloadは最小パッケージの対象外である。
- 辞書の運用値は創屋側で追加・管理し、同梱seedは開始点として扱う。
