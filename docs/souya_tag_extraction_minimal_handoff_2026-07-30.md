# 創屋向け CADタグ・属性抽出 最小ソース引き渡し手順

- 文書状態: **現行最小パッケージ仕様**
- 基準日: 2026-07-30
- 最終更新日: 2026-07-31
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

### 1.1 外部共有区分

- 創屋様へ渡す対象は、生成後に外部共有監査を通した最小パッケージと、そのZIPだけである。説明資料はPPTXではなく、監査・目視確認済みPDFをパッケージ内へ同梱する。
- 本リポジトリ全体、Git履歴、`backend/apps`、`output`配下の内部監査結果、顧客原本は渡さない。
- 配布承認済みの客先辞書3件と顧客固有規格`SES`を`initial-dictionaries.json`へ同梱する。案件辞書は現行seedに初期値がないため空である。
- 辞書以外の文書・PDF・サンプルには、個人名、社内ドライブ、実図面名、実測値を含めない。
- 例示値は`顧客A`、`SAMPLE-*`、`C:\sample`等の架空値に限定する。
- 同梱値以外の運用辞書は、共有範囲の承認後に創屋様のDBまたは辞書JSONから注入する。

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

配布パッケージ内のREADMEと技術文書は、社内向けの設計・生成・監査手順を含めない
`handoff/souya_tag_extraction/recipient_docs`を生成元とする。
本書、納品準備状況、現行仕様、テスト記録は社内管理用であり、配布パッケージへコピーしない。

## 3. 最小パッケージ構成

```text
souya_tag_extraction_minimal_YYYY-MM-DD/
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
│  ├─ convert_icad_standalone.ps1
│  └─ start_windows_extraction_agent.ps1
├─ docker/
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  └─ data/
│     └─ input.json
└─ docs/
   ├─ CADタグ属性抽出_創屋様向け利用ガイド.pdf
   ├─ extraction_reference.md
   ├─ integration_contract.md
   └─ icad_windows_operations.md
```

`manifest.json`には全ファイルの相対パス、サイズ、SHA-256を記録する。
同名出力先が既に存在する場合、生成スクリプトは上書きせず停止する。
PDFは本文監査に加え、全ページを画像化して文字切れ・重なり・社内情報・顧客固有情報がないことを目視確認する。編集元PPTXは中間物であり、配布しない。

READMEとMarkdown技術文書は生成時に社内文書から変換しない。受領者向け専用原稿を固定の許可リストでコピーし、
`リポジトリ`、`Git履歴`、`生成スクリプト`、`受入確認`等の内部工程表現を監査で拒否する。

## 4. Python単独実行

### 4.1 前提

- Python 3.11以上
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
    "顧客A": ["customer-a"]
  },
  "project": {}
}
```

上記は辞書形式を示す架空例である。同梱`initial-dictionaries.json`には配布承認済みの`customer`3件と顧客固有規格`SES`を含み、`project`は現行seedに初期値がないため空である。
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
社内生成工程では`scripts/generate_tag_extraction_schemas.py --check`により、`Models.cs`とPython canonicalキーからの
生成結果が保存済みSchemaと一致するか確認する。配布パッケージでは生成済みSchemaと配布専用テストを利用する。

## 8. C#実行とICAD→DXF/STEP変換

C#のビルド・SXNET配置・ICAD実行条件は
`docs/windows_extraction_agent_api_design_2026-07-29.md`を参照する。

現在はDjangoとICADを同じWindows PCで動かす構成を既定とする。
別PCのICADをWindows agentとして接続する場合は、
`docs/icad_remote_windows_agent_setup_for_souya_2026-07-30.md`を参照する。
Agent PCへはC#ソースやVisual Studioではなく、publish済みRunner一式と
`scripts/start_windows_extraction_agent.ps1`を配置できる。

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
初期状態では、架空データだけを使った2D rawサンプルを`docker/data/input.json`へ同梱している。
コマンド成功後は`docker/data/output.json`が生成される。実データへ差し替える場合も、
入力と出力に同じパスを指定せず、顧客資料の共有・保管ルールを確認する。

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

社内で再生成する場合は、受領者向け専用MarkdownからPDFとパッケージを同時に作る。

```powershell
<reportlabとpypdfを利用できる生成用Python> ".\scripts\prepare_souya_tag_extraction_handoff.py" `
  --output ".\output\souya_tag_extraction_minimal_YYYY-MM-DD"
```

受領済みパッケージ内には生成スクリプトを含めない。創屋様は`manifest.json`を検証し、同梱ソースを組み込む。

## 11. 既知の境界

- 創屋本番DB/APIへの書き込みは未接続であり、納品コアも書き込まない。
- ICAD/SXNETの実抽出とDXF/STEP変換はWindows＋ICAD環境が必要である。
- 別PC Windows agentは実装上対応するが、創屋ネットワークでの実機疎通は受入確認が必要である。
- DockerはPython側だけを対象とする。
- 手動補正、2D/3D合成、レビュー画面、RAG payloadは最小パッケージの対象外である。
- 配布承認済みの客先辞書3件と顧客固有規格`SES`は同梱seedに含む。案件辞書と追加の運用値は創屋側で管理する。
