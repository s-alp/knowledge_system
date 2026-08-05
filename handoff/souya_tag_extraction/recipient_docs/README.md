# CADタグ・属性抽出パッケージ 利用ガイド

このパッケージには、ICAD・STEP・DXFから属性を抽出し、共通形式へ正規化してタグを生成するためのソースコードと実行例が含まれています。

本READMEと`docs`配下の技術文書は、導入・組み込み・保守を担当する方向けです。プログラムやCADの内部処理を扱わない方への説明には、専門用語とコードを使わない[`docs/overview_for_users.md`](docs/overview_for_users.md)（同梱PDF「概要ガイド」と同じ内容）をお使いください。

## 1. 目的別・資料の見方

すべての資料を順番に読む必要はありません。最初に本章で目的に合う資料を確認し、担当する処理に関係する資料だけを参照してください。

### 1.1 最初に読む順序

1. 本READMEの「含まれる機能」「処理の流れ」「フォルダー構成」で、パッケージの範囲を確認します。
2. まず動作を見たい場合は「Pythonを使った最短の動作確認」を実行します。
3. 次の目的別一覧から、担当する処理に合う技術文書を1つ選びます。
4. 実装またはデータ確認を始める段階で、`examples`、`schemas`、`dictionaries`を確認します。
5. パッケージの受領時や別PCへのコピー後は、`manifest.json`でファイルの不足や変更がないことを確認します。

### 1.2 目的別の参照先

| 目的 | 最初に見る場所 | 次に確認する場所 |
|---|---|---|
| 仕組みの概要を非技術者へ説明したい | [`docs/overview_for_users.md`](docs/overview_for_users.md) | 同梱PDF「概要ガイド」 |
| まず動作確認したい | 本README「Pythonを使った最短の動作確認」 | `examples/raw`、`examples/results`、`tests/python` |
| ICAD・STEP・DXFから何を抽出できるか知りたい | [`docs/extraction_reference.md`](docs/extraction_reference.md) | `schemas`、`examples/results` |
| Pythonへ組み込みたい | [`docs/integration_contract.md`](docs/integration_contract.md) | `python`、`schemas`、`examples` |
| 辞書を追加・変更したい | 本README「初期辞書」 | [`docs/integration_contract.md`](docs/integration_contract.md)「辞書」、`dictionaries` |
| ICADから属性を直接抽出したい | [`docs/icad_windows_operations.md`](docs/icad_windows_operations.md)「必要な環境」「C# Runnerのビルド」「ICADの直接抽出」 | `csharp`、`schemas/icad-csharp-raw-extraction.v1.schema.json` |
| ICADからDXF／STEPへ変換したい | [`docs/icad_windows_operations.md`](docs/icad_windows_operations.md)「ICADからDXF／STEPへの変換」 | `scripts/convert_icad_standalone.ps1` |
| Windows agentを接続したい | [`docs/icad_windows_operations.md`](docs/icad_windows_operations.md)「Windows agent」 | `scripts/start_windows_extraction_agent.ps1` |
| ソースを変更・保守したい | [`docs/source_code_guide.md`](docs/source_code_guide.md) | 対象機能のソース、`tests/python`または`csharp/tests` |
| 出力JSONをDBやAPIへ保存したい | [`docs/integration_contract.md`](docs/integration_contract.md)「処理結果」「保存時の推奨項目」 | `schemas/icad-tag-extraction-result.v1.schema.json` |
| ファイルが正しいか確認したい | `manifest.json` | 本README「文書以外の重要なファイル」 |
| エラーや想定外の結果を調べたい | 本README「問題が起きたときの確認先」 | 症状に対応する技術文書、`examples`、`schemas` |

### 1.3 各資料に書かれていること・書かれていないこと

| 資料 | 書かれていること | 書かれていないこと |
|---|---|---|
| [`docs/overview_for_users.md`](docs/overview_for_users.md) | 仕組みの目的、導入前後の違い、取り出せる情報、できないこと、想定質問への回答 | インストール手順、コマンド、JSONのキー、ソースの構成 |
| `README.md` | 全体像、資料の選び方、最短の動作確認、Docker、初期辞書 | 全抽出項目の詳細、JSONの全キー、ICAD環境の詳細設定 |
| [`docs/extraction_reference.md`](docs/extraction_reference.md) | 入力形式ごとの抽出元、抽出項目、正規化、タグ付け、取得できない値の扱い | インストール手順、C#のビルド手順、DBやAPIへの保存方法 |
| [`docs/integration_contract.md`](docs/integration_contract.md) | Python CLI／API、処理結果、JSON Schema、辞書、保存時の推奨項目 | ICADやSXNETの設定、C# Runnerのビルド、Windows agentの運用 |
| [`docs/icad_windows_operations.md`](docs/icad_windows_operations.md) | C# Runnerのビルド、ICAD抽出、DXF／STEP変換、Windows agent | Python結果のDB保存、タグ辞書の設計、画面やRAGへの接続 |
| [`docs/source_code_guide.md`](docs/source_code_guide.md) | 機能別の変更箇所、Python正規化の分担、C#の読み進め方 | 各関数の全仕様、ICAD環境の設定値、DBやAPIの実装 |
| 概要ガイドPDF（同梱PDF） | [`docs/overview_for_users.md`](docs/overview_for_users.md)のPDF版。非技術者への説明用として単独で配れる | コマンド、JSONのキー、ソースの構成 |
| 利用ガイドPDF（同梱PDF） | 概要ガイド、本README、4つの技術文書を続けて読めるPDF版 | 機械処理用のJSON Schema、実行可能なソース、サンプルJSONの実データ |

JSONの正確なキー、型、必須条件はPDFや説明文ではなく、`schemas`内のJSON Schemaで確認してください。

### 1.4 担当外の資料は読み飛ばしてよい

| 担当または目的 | 主に読むもの | 最初は読み飛ばしてよいもの |
|---|---|---|
| 社内やお客様へ仕組みを説明する | [`docs/overview_for_users.md`](docs/overview_for_users.md)、同梱PDF「概要ガイド」 | 本READMEと`docs`配下の技術文書、`schemas`、`examples` |
| 同梱サンプルを動かして概要を確認する | 本README、`examples`、`tests/python` | C#の詳細、Windows agent、DB保存設計 |
| C# raw JSONを受け取ってPythonへ組み込む | 本README、`docs/integration_contract.md`、`schemas`、`examples`、`dictionaries` | `docs/icad_windows_operations.md`、C#の実装詳細 |
| STEP／DXFだけをPythonで処理する | 本README、`docs/extraction_reference.md`、`docs/integration_contract.md` | ICAD、SXNET、Windows agent、C#の実装詳細 |
| ICAD PCで抽出または変換を担当する | 本README、`docs/icad_windows_operations.md`、`docs/extraction_reference.md` | DB保存、画面、RAGへの接続方法 |
| DB／APIへの保存を担当する | 本README、`docs/integration_contract.md`、`schemas`、`examples/results` | C#のビルドとICAD操作。ただしC# raw JSONの取得方法も担当する場合は読み飛ばせません |
| 辞書の保守だけを担当する | 本README「初期辞書」、`docs/integration_contract.md`「辞書」、`dictionaries` | C#、Docker、Windows agent |

担当範囲が増えた時点で、対応する資料を追加で確認してください。

### 1.5 文書以外の重要なファイル

| ファイルまたはフォルダー | いつ見るか | 確認すること |
|---|---|---|
| `manifest.json` | パッケージ受領時、展開後、別PCへのコピー後 | ファイルの相対パス、サイズ、SHA-256が一致しているか |
| `examples/raw` | 最初の動作確認、入力JSONを作るとき | C# 2D／3D raw JSONの構造 |
| `examples/results` | 出力比較、組み込み後の確認 | 正規化属性、タグ、警告を含む期待結果 |
| `schemas` | JSONを保存・送受信・検証するとき | キー、型、必須条件、契約バージョン |
| `dictionaries` | タグ語彙や別名を確認・変更するとき | 7種別、正規名、別名、JSON形式 |
| `tests/python` | 環境構築後、Python処理を変更した後 | Djangoなしで2D／3Dの期待結果と一致するか |
| `csharp` | ICAD抽出器をビルド・変更するとき | Runner、SXNET連携、C#単体テスト |
| `scripts` | manifest確認、ICAD抽出・変換、Windows agentを実行するとき | `Get-Help`で必須引数と例、`-ValidateOnly`で設定結果 |
| `docker` | Python処理をコンテナで確認するとき | 入力ファイル、辞書、出力先、Python 3.11環境 |

### 1.6 問題が起きたときの確認先

| 症状 | 最初に見る場所 | 主な確認内容 |
|---|---|---|
| PythonのインストールやCLI起動に失敗する | 本README「Pythonを使った最短の動作確認」、`docs/integration_contract.md`「Pythonパッケージ」「CLI」 | Pythonが3.11以上か、実行場所、入力パス、拡張子、標準エラー |
| 出力項目が不足する、値が想定と違う | `docs/extraction_reference.md`、`examples/results` | 入力形式で取得可能な項目か、`warnings`、交換形式で失われる情報 |
| JSON Schema検証に失敗する | `docs/integration_contract.md`「処理結果」「JSON Schema」、`schemas` | `schema_version`、必須キー、値の型 |
| タグが付かない、別のタグになる | `docs/extraction_reference.md`「タグ付け」、`docs/integration_contract.md`「辞書」、`dictionaries` | 辞書種別、正規名、別名、`evidence`、`confidence`、`reason` |
| ICAD抽出やDXF／STEP変換に失敗する | `docs/icad_windows_operations.md`「必要な環境」から「ICADの直接抽出」 | ICAD版と`sxnet.dll`、Runnerのパス、`-ValidateOnly`、標準エラー |
| Windows agentが接続できない | `docs/icad_windows_operations.md`「Windows agent」「Windows agentのHTTP契約」 | URL、token、worker名、heartbeat、接続先API |
| ファイルが不足している、変更された可能性がある | `scripts/verify_handoff_manifest.ps1`、`manifest.json` | 不足、追加、サイズ、SHA-256 |

エラーを確認するときは、処理を成功扱いにして続行せず、終了コード、標準エラー、出力JSONの`warnings`を保存してください。

## 2. 含まれる機能

- ICAD 2D／3DをSXNETで読み取るC#抽出処理
- ICADからDXF／STEPへ変換するC#処理
- C#の抽出結果、STEP、DXFを共通属性へ正規化するPython処理
- 文字列・属性・辞書から、根拠付きタグを生成するPython処理
- C#とPythonの入出力を定義するJSON Schema
- 初期辞書、2D／3Dサンプル、単体テスト
- Python処理を確認するDocker構成

DBへの保存、Web API、画面、RAG、ビューワーは含まれていません。Pythonの処理結果を組み込み先のDBやAPIへ保存してください。

## 3. 処理の流れ

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

## 4. フォルダー構成

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
│  ├─ verify_handoff_manifest.ps1
│  ├─ extract_icad_standalone.ps1
│  ├─ convert_icad_standalone.ps1
│  └─ start_windows_extraction_agent.ps1
├─ docker/
└─ docs/
```

`manifest.json`には、同梱ファイルの相対パス、サイズ、SHA-256が記録されています。

### 4.1 コピー後のファイル確認

パッケージのルートで次を実行します。`Verified`が`True`なら、manifestに記録されたファイル一覧、サイズ、SHA-256が一致しています。

```powershell
pwsh -NoLogo -NoProfile -File ".\scripts\verify_handoff_manifest.ps1"
```

不一致が表示された場合は、欠落・追加・破損の可能性があるため、そのまま実行せず配布元のパッケージと照合してください。

## 5. Pythonを使った最短の動作確認

### 5.1 前提

- Python 3.11以上
- PowerShell 7以上
- Djangoは不要

パッケージのルートで次を実行します。

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".\python"
```

`python --version`が3.11未満の場合は、Python 3.11または3.12へ切り替えてから仮想環境を作成してください。PowerShellの実行ポリシーにより有効化できない場合は、有効化せず`.\.venv\Scripts\python.exe -m pip install ".\python"`のように仮想環境のPythonを直接指定できます。

C# 2Dサンプルを処理します。

```powershell
icad-tag-extraction `
  --input ".\examples\raw\csharp_raw_2d.v1.json" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\tagged_result.json"
```

正常終了すると、`tagged_result.json`へ`canonical_attributes`と`derived_tags`が出力されます。

`icad-tag-extraction`が見つからない場合は、同じ処理をPythonモジュールとして実行できます。

```powershell
python -m icad_tag_extraction `
  --input ".\examples\raw\csharp_raw_2d.v1.json" `
  --dictionary ".\dictionaries\initial-dictionaries.json" `
  --output ".\tagged_result.json"
```

### 5.2 同梱テスト

```powershell
python -m pip install -r ".\python\requirements-dev.txt"
python -m pytest ".\tests\python"
```

このテストでは、Djangoに依存せず処理できること、JSON Schemaが有効であること、2D／3Dサンプルが期待結果と一致することを確認します。

## 6. STEP／DXFの処理

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

## 7. Dockerによる動作確認

DockerはPython処理だけを実行します。ICAD、SXNET、C# RunnerはWindows上で実行してください。

```powershell
docker compose -f ".\docker\docker-compose.yml" run --rm tag-extraction
```

`docker\data\input.json`を読み、`docker\data\output.json`へ結果を保存します。

## 8. Python APIへの組み込み

```python
from icad_tag_extraction import (
    ExtractionConfig,
    MappingDictionaryProvider,
    process_extraction,
)

config = ExtractionConfig(
    schema_version="1.1.0",
    normalizer_version="1.2.0",
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

## 9. 初期辞書

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

## 10. ICADを使用する処理

ICADの抽出、DXF／STEP変換、Windows agentの起動には、Windows、ICAD、対応する`sxnet.dll`、.NET Framework 4.8が必要です。ビルド方法と実行例は[`docs/icad_windows_operations.md`](docs/icad_windows_operations.md)を参照してください。
