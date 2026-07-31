# 創屋向け CADタグ・属性抽出 実装・受入チェックリスト

- 基準日: 2026-07-31
- 対象: 創屋向け最小ソースパッケージ
- 目的: C#、Python、Docker、ICAD→DXF/STEP変換、辞書、タグ付けを、創屋様が資料とソースコメントから実装・検証できる状態にする
- 説明資料: PPTXではなく、外部共有監査と全ページ目視確認を通したPDFを同梱する

## 1. 最初に確認すること

創屋様へ渡すのは、外部共有監査済みの最小パッケージとZIPだけです。本リポジトリ全体、Git履歴、当社内Django app、内部監査結果、顧客原本は受領対象ではありません。
READMEとMarkdown技術文書は`handoff/souya_tag_extraction/recipient_docs`の専用原稿だけを使用し、本書を含む社内用の納品準備・生成・監査資料は同梱しません。
PDFも同じ専用Markdownから`scripts/prepare_souya_tag_extraction_handoff.py`で生成し、MarkdownとPDFの説明内容を二重管理しません。

受領後、次の順で確認してください。

1. `manifest.json`の全ファイルについて、相対パス、サイズ、SHA-256が実ファイルと一致する。
2. `README.md`の供給範囲と「対象外」を確認する。
3. `docs/extraction_reference.md`で、入力形式ごとの抽出元と出力属性を確認する。
4. `schemas/*.schema.json`で、C# raw、canonical属性、自動タグ、最終結果の型を確認する。
5. Python配布テストとC#テストを実行する。

不一致、欠落、Schema違反が1件でもあれば、組み込みを開始せず当社へ連絡してください。

## 2. 創屋様だけで実施できる範囲

| 作業 | 入力 | 成果物 | 完了条件 |
|---|---|---|---|
| Pythonコアの導入 | `python/`、`dictionaries/` | インストール済み`icad_tag_extraction` | 配布テスト成功 |
| C#抽出器のビルド | `csharp/` | Runnerと依存DLL | `dotnet test`成功 |
| ICAD raw抽出 | `.icd`、ICAD、SXNET | C# raw JSON | raw Schema成功 |
| ICAD→DXF/STEP変換 | `.icd` | `.dxf`または`.stp/.step`、結果JSON | 変換成功と出力存在 |
| STEP/DXF汎用抽出 | `.step/.stp/.dxf` | raw相当データ | Python処理結果Schema成功 |
| 正規化 | raw JSON | `canonical_attributes` | canonical Schema成功 |
| 辞書照合・タグ生成 | canonical属性、辞書 | `derived_tags` | タグSchema成功、全タグに根拠あり |
| Docker実行 | `docker/`、入力JSON、辞書JSON | 処理結果JSON | compose構成成功、CLI正常終了 |
| 創屋様側adapter実装 | 処理結果JSON | 創屋様DB/APIの保存データ | 後述の接続契約を満たす |

配布承認済みの客先辞書3件と顧客固有規格`SES`は初期辞書に含まれます。案件辞書は空です。同梱値以外の運用値は、共有範囲の承認後に創屋様のDBまたは辞書JSONから注入してください。

## 3. 推奨する実装順序

### 3.1 配布物の自己検証

```powershell
python -m pip install ".\python"
python -m pip install -r ".\python\requirements-dev.txt"
python -m pytest ".\tests\python"
dotnet test ".\csharp\tests\IcadExtraction.Contracts.Tests\IcadExtraction.Contracts.Tests.csproj" -c Release
dotnet test ".\csharp\tests\IcadExtraction.Runner.Tests\IcadExtraction.Runner.Tests.csproj" -c Release
dotnet test ".\csharp\tests\IcadExtraction.SxNet.Tests\IcadExtraction.SxNet.Tests.csproj" -c Release
docker compose -f ".\docker\docker-compose.yml" config
docker compose -f ".\docker\docker-compose.yml" run --rm tag-extraction
```

すべて成功するまで、創屋様本番DB/APIへの接続は行わないでください。
環境によってsolution一括実行が長時間待機する場合があるため、受入手順では上記3プロジェクトを個別実行する。

### 3.2 Pythonコアの呼び出し

```python
from icad_tag_extraction.dictionary_provider import load_json_dictionary_provider
from icad_tag_extraction.pipeline import process_extraction

provider = load_json_dictionary_provider("dictionaries/production-dictionaries.json")
result = process_extraction(raw_payload, dictionary_provider=provider)
```

`process_extraction()`はDB、ファイル、外部APIを更新しません。返された`result`をSchema検証した後、創屋様側adapterが保存します。

### 3.3 保存adapterの必須責務

創屋様側adapterは次を実装してください。

1. C# raw入力を`icad-csharp-raw-extraction.v1.schema.json`で検証する。
2. Python処理結果を`icad-tag-extraction-result.v1.schema.json`で検証する。
3. `source_file`、`canonical_attributes`、`derived_tags`、`warnings`を欠落させず保存する。
4. `derived_tags`の`source`、`evidence`、`confidence`、`reason`、`tag_rule_version`を保持する。
5. Schema違反、辞書不正、未対応形式、ICAD/SXNET失敗時は保存を中断し、エラーを記録・通知する。
6. 同じ図面を再処理した場合の更新単位、履歴、手動補正との優先順位を創屋様本体の仕様として決定する。

最小コアは、創屋様本番DBのテーブル名、API URL、認証方式を知りません。これらをコアへ直接書き込まず、adapterに閉じ込めてください。

## 4. 当社確認なしに決めてはいけない事項

次はソースだけでは確定できない本番環境固有情報です。創屋様の判断だけで仮定せず、当社と確認してください。

| 確認事項 | 確認する内容 | 確定前に行わないこと |
|---|---|---|
| 本番保存先 | API/DB、項目対応、更新単位、履歴 | 本番書き込み |
| 認証・権限 | API認証、Windows agent token、サービスアカウント | 固定tokenの埋め込み |
| ICAD実行環境 | ICAD/SXNET版、ライセンス、同時実行数 | 本番一括処理 |
| ネットワーク | agent URL、許可host、Firewall、UNC権限 | ポート公開 |
| 運用辞書 | 客先・案件・別名、登録責任者、更新手順 | 配布承認されていない実値のseed化 |
| ジョブ運用 | timeout、retry、再実行、監視、障害通知 | エラー握り潰し |
| 手動補正 | 自動再抽出との優先順位、監査履歴 | 自動結果で上書き |
| RAG連携 | payload項目、投入時点、削除・再索引 | RAG本番投入 |

## 5. 受入テスト

### 5.1 必須ケース

1. 同梱2D raw例を処理し、同梱期待結果と完全一致する。
2. 同梱3D raw例を処理し、同梱期待結果と完全一致する。
3. 架空の客先辞書を注入し、`客先:顧客A`が根拠付きで生成される。
4. 辞書ファイル不在・不正JSON・不明種別で処理が失敗し、seedへ自動フォールバックしない。
5. ICADがない環境ではPython/Dockerだけが動作し、ICAD処理を成功扱いにしない。
6. ICAD環境では2D/3D raw抽出とDXF/STEP変換を別々に確認する。
7. STEP/DXF変換後に失われる属性を元ICAD結果と比較し、代替経路を正本扱いしない。
8. 創屋様adapterでSchema違反時にDB/API更新が中断される。

### 5.2 完了判定

次をすべて満たしたときだけ、創屋様側の組み込み完了とします。

- Python配布テスト、C#テスト、compose構成確認が成功している。
- 同梱PDFの本文監査と全ページ目視確認が成功している。
- 創屋様環境でICAD/SXNETの実機受入が成功している。
- 本番DB/APIの項目対応と認証方式が当社・創屋様間で確定している。
- 客先・案件辞書の共有範囲と管理責任者が確定している。
- エラー、再実行、手動補正、監査履歴の運用が確定している。
- 実顧客資料を使う受入テストは、別途承認された環境とデータだけで実施している。

## 6. 当社生成環境での最終確認結果

2026-07-31に、装置カテゴリ判定・塗装指示抽出の改善と辞書配布許可を反映した
`souya_tag_extraction_minimal_2026-07-31_r18`で次を確認しました。
機械確認は`scripts/verify_souya_tag_extraction_handoff.py`へ固定し、ZIPの一時展開先だけで
Pythonをインストールするため、展開済み配布フォルダーへbuild、egg-info、キャッシュを残しません。

| 確認項目 | 結果 |
|---|---|
| Schema再生成・保存済みSchemaとの一致 | 合格 |
| バージョン | Python package 1.2.0、結果Schema 1.1.0、正規化規則 1.2.0 |
| backend pytest | 200件合格 |
| Django system check | 問題0件 |
| C#単体テスト | Contracts 3件、Runner 8件、SxNet 30件の計41件合格 |
| タグ関連文書監査 | エラー0件、警告0件 |
| ソースコメント監査 | 295ファイル合格 |
| 配布専用Pythonテスト | Python 3.11.9と3.12.10で各4件合格 |
| ZIP受領シミュレーション | 専用一時領域へ展開し、展開済みフォルダーとの全74ファイルのSHA-256一致に合格 |
| クリーンPython導入 | 最終ZIPからPython 3.11.9と3.12.10へ隔離インストールし、`importlib.metadata`でpackage 1.2.0を照合 |
| 初期辞書 | 客先3件、案件0件、規格7件（SES含む）を同梱 |
| クリーンC#導入 | ZIP内ソリューションだけでrestore・ビルド・41件のテストに合格 |
| PowerShellスクリプト | ICAD変換・Agent起動の2ファイルとも構文エラー0件 |
| Docker Compose構成確認 | 合格 |
| Docker image build | 合格 |
| Dockerコンテナ実行 | 同梱サンプル入力から`docker/data/output.json`を生成し、期待JSONと意味的に一致 |
| PDF | 18ページの本文監査と全ページ目視確認に合格。単体PDFとパッケージ内PDFもSHA-256一致 |
| 外部共有監査 | 配布承認済み初期辞書を許可し、それ以外の社内パス、実図面名、実測件数、配布対象外情報の検出0件 |
| manifest | manifest対象73ファイルの集合、サイズ、SHA-256が一致。manifest自身を含むZIPは74ファイル |
| ZIP | 314,544 bytes、SHA-256 `3bb9cc39ffee2f1f6c57b74adc888ece9a9b26a1e21e6a11b8009d5691d86365` |
| PDFファイル | 145,556 bytes、SHA-256 `17f4f2ab624caa93e11f767dee19dc7f01d9e1976b42a748e109b3a17e6f5ffe` |
| 配布対象外生成物 | `__pycache__`、`.pyc`、`.pytest_cache`、`bin`、`obj`、`build`、`*.egg-info`、PPTX、Django `apps`、顧客資料の混入0件 |

この結果は、同梱ソース・Schema・辞書・例・文書・Docker構成の自己完結性を示します。
創屋様環境のICAD/SXNET実機動作、本番DB/API、認証、ネットワーク、運用辞書は環境固有なので、5.2の受入確認が別途必要です。

## 7. 問い合わせ時に添える情報

- `manifest.json`の`packageName`
- 実行したコマンド
- 入力形式（ICAD 2D/3D、DXF、STEP）
- エラー全文と終了コード
- 対象Schema名
- `warnings`の内容
- ICAD/SXNET版、Python版、.NET版、Docker版

顧客原本や実パスをメール・チャットへ直接貼らず、当社指定の共有方法を確認してください。
