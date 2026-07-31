# knowledge_system 作業メモ

## 目的
- 設計資料RAG（`http://210.165.3.139/web/chat`）の精度検証を行う。
- 問題の事実、改善提案、必要に応じた開発先確認事項を整理する。

## 現在の前提
- 共同開発先からアプリのソースコード共有はされていない。
- 検証は基本的にブラックボックスで実施する。
- 必要に応じて元資料をローカル確認して、RAGの回答と照合する。
- `http://210.165.3.139/web/chat` で実機能として見る対象は、基本的に RAG の検索・回答部分のみとする。
- RAG 以外の保存系、管理系、一覧系、設定系 UI はモック前提で扱い、実データの保存先・取得元・ダウンロード元だと決めつけない。

## ローカル開発サーバー起動方針
- このプロジェクトで「サーバーを起動して」と言われた場合は、原則として以下の3点をセットで起動・疎通確認する。
  - backend: Django `runserver`、通常は `http://127.0.0.1:8000/`
  - frontend: Vite dev server、通常は `http://127.0.0.1:5173/`
  - worker: `python manage.py process_drawing_metadata_jobs --loop --mode all`
- `http://127.0.0.1:8000/` が `api-only` JSON を返すだけの場合、起動完了扱いにせず、frontend の `5173` と worker heartbeat まで確認する。
- 既に起動済みのプロセスがある場合は二重起動せず、ポート、プロセス、HTTP応答、worker heartbeat を確認して報告する。

## 検索先の前提
- ナレッジシステムの検索先は、Web アプリ内の保存領域ではなく社内のデータベースである。
- 検証時は、検索対象の実体として以下の社内パス配下の元資料を前提にする。
  - `T:\NTC\TF設計部\TD2\コマツ小山`
  - `J:\NTC\MC設計部\広島アルミメキシコ\20240408_FTL-2184GC_BM対応他\20241101_カバー関係、ロボット関係`
- Excel や Word 仕様書に関する検証は、上記パス配下の元資料を必要最小限だけローカルへコピーして照合する。
- Web UI 上の文書管理・図面管理・保存・出力の導線は、モックの可能性を常に疑い、元資料パスの確認より優先しない。

## 主な対象
- 案件:
  - コマツ小山の治具
  - コマツ小山のガントリー
  - 広島アルミのガントリー
- 規格:
  - 澁谷工業の規格

## 元資料の参照先
- コマツ小山:
  - `T:\NTC\TF設計部\TD2\コマツ小山`
- 広島アルミ:
  - `J:\NTC\MC設計部\広島アルミメキシコ\20240408_FTL-2184GC_BM対応他\20241101_カバー関係、ロボット関係`
- SES PDF:
  - `D:\創屋用\SES_PDFs`

## 除外方針
- 議事録関連ファイルは原則除外する。
- 理由:
  - 見積工数など、対外共有を避けたい情報が含まれるため。

## 元資料のローカルコピー方針
- 元資料をローカル確認する場合は、検証に必要な最小限のファイルだけをワークスペースへコピーする。
- コピー元は以下に限定する。
  - `T:\NTC\TF設計部\TD2\コマツ小山`
  - `J:\NTC\MC設計部\広島アルミメキシコ\20240408_FTL-2184GC_BM対応他\20241101_カバー関係、ロボット関係`
  - `D:\創屋用\SES_PDFs`
- 議事録、見積、工数、社外共有不要情報を含むファイルはコピーしない。
- コピー先はワークスペース内の専用フォルダとし、原本は変更しない。
  - `C:\Users\s-iwata\Desktop\knowledge_system\local_test_materials`
- フォルダ構成は、出所が分かるように案件・規格ごとに分ける。
- コピー後は、どのファイルをどこから持ってきたかを検証結果またはメモに残す。
- ローカル確認の目的は、RAG回答の事実確認と質問設計の精度向上であり、資料の無制限な持ち込みはしない。

## 検証時の観点
- 初回回答の精度
- 追撃後の改善有無
- 案件名・企業名・カテゴリ名の切り分け
- 「資料なし」のときに無関係資料を参考に出さないか
- BOM/部品情報から案件名へ正しく上がれるか
- 回答本文と参考資料の整合

## Playwright運用メモ
- `http://210.165.3.139/web/chat` の検証は、原則として Playwright を第一候補とする。
- ただし、Playwright で触る対象は RAG チャット画面を優先し、文書管理・保存・設定などの周辺 UI を安易に実機能扱いしない。
- `browser_navigate` や `browser_click` 実行時に `EPERM: operation not permitted, mkdir 'C:\Windows\System32\.playwright-mcp'` が出ても、即時に完全失敗と判断しない。
- 上記エラーは非致命で、既存のブラウザコンテキストやページ状態が維持され、URL遷移・入力反映・`browser_snapshot` が継続する場合がある。
- そのため、上記エラー発生後は必ず `browser_snapshot`、必要に応じて `browser_evaluate` で、実際の URL・DOM・入力反映状況を確認してから成否を判定する。
- 報告時は「完全失敗」「部分成功」「ページ状態は遷移済み」を分けて明記する。
- 既知エラーだからといって省略せず、発生した都度ユーザーに共有する。
- RAG チャットの回答本文を回収するときは、UI の描画待ちだけに頼らず、認証済みセッション上で `/api/chats/{id}/messages` を直接参照して確認してよい。
- 新規質問の送信や回答有無の確認も、必要に応じて `/api/chats/`、`/api/chats/{id}/messages`、`/api/chats/{id}/messages/{message_id}/answer` を使ってよい。
- ただし、この API 直参照は RAG チャットの送受信確認に限定し、モック前提の保存系・管理系 UI の実機能確認には拡張しない。
- 回収時は、質問文・回答本文・参照資料をセットで確認し、必要なら UI 表示と API 応答の両方を照合する。

## 追撃比較の基本形
同じテーマで、必要に応じて以下を順に確認する。

1. 初回曖昧質問
2. 追撃で用語定義
3. 追撃で除外条件
4. 追撃で出力形式指定

## 出力物
- 検証結果Excel:
  - `C:\Users\s-iwata\Desktop\knowledge_system\output\spreadsheet\rag_test_summary_2026-04-23.xlsx`
- 生成スクリプト:
  - `C:\Users\s-iwata\Desktop\knowledge_system\scripts\generate_rag_test_report.py`

## 実装準備ドキュメント
- 現行仕様の正本:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\tag_extraction_and_assignment_current_spec_2026-07-29.md`
- 創屋向け最小パッケージ仕様:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\souya_tag_extraction_minimal_handoff_2026-07-30.md`
- 関連ドキュメント索引:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\tag_extraction_documentation_index_2026-07-29.md`
- Windows agent / C#入出力の正本:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\windows_extraction_agent_api_design_2026-07-29.md`
- 調査結果:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_investigation_2026-05-26.md`
- 設計計画:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_design_plan_2026-05-26.md`
- 実装引継ぎ:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_implementation_backlog_2026-05-26.md`
- C# / Django 分担案:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_csharp_python_architecture_2026-05-27.md`
- Django 統合計画:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\django_integration_plan_2026-05-28.md`
- 抽出結果スキーマ:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\extraction_result_schema_2026-05-28.md`
- タグ・属性管理 UI 計画:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\tag_attribute_management_ui_plan_2026-05-28.md`
- HTML 要約報告:
  - `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_report_2026-05-26.html`

## 現時点の実装前提
- 創屋側ナレッジシステム本体のソースコードは未共有である。一方、本リポジトリには移植用のDjango非依存Pythonコア、独立Django app、C#抽出器、統合Viteフロントが実装済みである。
- 実装は「後で創屋側本体へ移植しやすい独立モジュール」を前提に維持する。
- ICAD ネイティブ抽出コアは `C# + SXNET` で実装済みである。
- 正規化、辞書照合、タグ生成、STEP/DXF汎用抽出は `backend\icad_tag_extraction` のDjango非依存Pythonコアを正本とする。
- 創屋向け独立Pythonコアの正式対応範囲はPython 3.11以上とし、配布Docker例も`python:3.11-slim`を基準にする。
- Djangoのservice / task層は、DB辞書、保存、非同期ジョブ、手動補正、RAG previewを独立Pythonコアへ接続するadapterである。
- C# raw抽出、canonical属性、derived tags、Python処理結果の境界は `schemas\tag_extraction` のJSON Schemaを正本とする。
- ICAD抽出は `1図面 = 1回呼び出し` の一括実行を原則とし、Docker/Linux WebとWindows agentをHTTPで分離できる。
- 重い処理は Django の request thread に残さず、非同期ジョブまたはWindows agentで処理する。
- 現行挙動は `docs\tag_extraction_and_assignment_current_spec_2026-07-29.md` とコードを正とし、2026-05月の調査・計画文書は履歴資料として扱う。

## 創屋向け最小パッケージの再生成手順

### 基本方針
- パッケージ作成は、生成スクリプトだけを機械的に実行して完了扱いにしない。
- Codexが変更差分、契約影響、テスト結果、同梱内容、既存成果物を順に確認し、各段階の成功を確認してから生成する。
- `scripts\build_souya_tag_extraction_package.py`は収集・manifest・ZIP生成を再現するための道具であり、変更内容の妥当性を自動判断するものではない。
- エラー、Schema差分、現行結果との不一致、意図しないDjango依存、顧客資料やキャッシュの混入が1件でもあれば生成・コミットを中断し、原因を修正する。
- 既存パッケージを自動削除・自動上書きしない。同名成果物がある場合は、内容と利用状況を確認し、原則として日付または`_r2`等を付けた新しい出力先を使う。

### 1. 変更範囲の確認
1. `git status --short`、`git diff`、`git diff --cached`を実行する。
2. 他Codex、他エージェント、ユーザーの変更を分類し、今回のパッケージ対象と混ぜない。
3. 少なくとも次の変更有無を確認する。
   - `src\IcadExtraction.*`、`tests\IcadExtraction.*`
   - `backend\icad_tag_extraction`
   - `backend\apps\drawing_metadata`のadapter
   - `schemas\tag_extraction`
   - `examples\tag_extraction_contract`
   - `scripts\generate_tag_extraction_schemas.py`
   - `scripts\build_souya_tag_extraction_package.py`
   - 初期辞書、変換スクリプト、引き渡し文書
4. C# DTO、canonicalキー、タグpayload、バージョン、辞書種別に変更がある場合は、JSON Schemaと例の更新が必要と判断する。

### 2. 正本ドキュメントの確認
- 実装判断前に、少なくとも次を読み、現行コードとの差異がないか確認する。
  - `docs\tag_extraction_and_assignment_current_spec_2026-07-29.md`
  - `docs\souya_tag_extraction_minimal_handoff_2026-07-30.md`
  - `docs\extraction_result_schema_2026-05-28.md`
  - `docs\windows_extraction_agent_api_design_2026-07-29.md`
  - `docs\icad_dxf_step_standalone_conversion_guide_2026-07-29.md`
- コード、Schema、コマンド、同梱範囲を変更した場合は、パッケージ生成前に関連文書と`tasklist.md`を更新する。

### 3. Schemaの生成と確認
リポジトリルートで次を実行する。

```powershell
backend\.venv\Scripts\python.exe scripts\generate_tag_extraction_schemas.py
backend\.venv\Scripts\python.exe scripts\generate_tag_extraction_schemas.py --check
```

- 1行目で現行C# DTOとPython canonicalからSchema・2D/3D例を再生成する。
- 2行目で保存済みSchema・例が現行コードと完全一致することを確認する。
- 意図しない差分が出た場合はSchemaだけを採用せず、DTO、正規化結果、例のどこが変わったかを確認する。

### 4. パッケージ生成前の必須検証
リポジトリルートで次を順に実行し、すべて成功させる。

```powershell
backend\.venv\Scripts\python.exe -m pytest -c backend\pytest.ini --basetemp=backend\tmp\pytest_run backend
backend\.venv\Scripts\python.exe backend\manage.py check
dotnet test tests\IcadExtraction.Contracts.Tests\IcadExtraction.Contracts.Tests.csproj -c Release --no-restore
dotnet test tests\IcadExtraction.Runner.Tests\IcadExtraction.Runner.Tests.csproj -c Release --no-restore
dotnet test tests\IcadExtraction.SxNet.Tests\IcadExtraction.SxNet.Tests.csproj -c Release --no-restore
backend\.venv\Scripts\python.exe scripts\audit_tag_documentation.py
backend\.venv\Scripts\python.exe scripts\audit_beginner_source_comments.py
git diff --check
```

- 独立PythonコアとDjango adapterの2D/3D完全一致テストを必ず含める。
- C# raw、canonical、derived tags、Python処理結果のSchema検証を必ず含める。
- 廃止済み外部AI項目へ影響する変更では、`scripts\audit_retired_ai_database_history.py`も実行する。
- Docker関連を変更した場合は、Docker Engineの状態を確認してからcompose構成検証とimage buildを行う。Engine都合で未完了の場合は成功と表現しない。

### 5. 新しい出力先の決定と生成
1. `Get-Date -Format yyyy-MM-dd`で作業日を確認する。
2. `output\souya_tag_extraction_minimal_YYYY-MM-DD`を基本名とし、同名があれば内容を確認して`_r2`等の別名を選ぶ。
3. 既存成果物を置換する必要がある場合は、対象絶対パス、manifest、Git状態を確認し、ユーザーの意図が明確な場合だけ実施する。
4. 出力先を明示して生成する。

```powershell
<pypdfを利用できる生成用Python> scripts\build_souya_tag_extraction_package.py `
  --output output\souya_tag_extraction_minimal_YYYY-MM-DD `
  --guide-pdf output\pdf\<外部共有安全版PDF>
```

生成用Pythonは、Codex Desktopの`load_workspace_dependencies`で確認した文書用Python、または`pypdf`を導入した専用環境を使う。PPTXはPDF生成の中間物であり、創屋様への配布物には含めない。

生成対象は、C#抽出器とテスト、Django非依存Pythonコア、JSON Schema、初期辞書、2D/3D例、ICAD→DXF/STEP変換スクリプト、Docker例、引き渡し文書、外部共有安全版PDFである。Djangoモデル、DB、API、UI、RAG、顧客原本は含めない。

生成スクリプトはmanifestとZIPを作る前に`scripts\audit_souya_handoff_content.py`を実行する。配布承認済みの客先・案件・規格値は`dictionaries\initial-dictionaries.json`内だけ許可し、それ以外の文書・PDF・サンプルに混入した社内パス、実図面名、実測件数、配布対象外ディレクトリは拒否する。辞書JSONは全7種別がobjectであることを必須とし、案件辞書は現行seedに値がないため0件である。

### 6. 生成後の受入確認
1. `manifest.json`と実ファイルの集合、サイズ、SHA-256が一致することを確認する。
2. `__pycache__`、`.pyc`、`.pytest_cache`、`bin`、`obj`、Djangoの`apps`、顧客資料が含まれないことを確認する。
3. 配布専用テストをパッケージ内のPythonだけで実行する。

```powershell
$package = Resolve-Path output\souya_tag_extraction_minimal_YYYY-MM-DD
$env:PYTHONPATH = Join-Path $package "python"
$env:PYTHONDONTWRITEBYTECODE = "1"
backend\.venv\Scripts\python.exe -m pytest `
  (Join-Path $package "tests\python")
```

4. `docker compose -f <package>\docker\docker-compose.yml config`で構成を確認する。
5. ZIPの存在、サイズ、manifestのfile countを確認する。
6. 配布するPDFは全ページをPNGへ変換して目視確認し、次の本文監査も実行する。

```powershell
<pypdfを利用できる生成用Python> scripts\audit_souya_handoff_content.py `
  output\souya_tag_extraction_minimal_YYYY-MM-DD `
  --pdf <外部共有安全版PDF>
```

PDF本文監査では画像内文字を判定できないため、実データを含むスクリーンショットは使わず、架空データだけの図に差し替える。PDF内のページ数、文字切れ、重なり、空白ページ、社内情報、顧客固有情報を全ページ目視する。

7. 生成後にもう一度`git status --short`を実行し、並行作業の成果物を混入させていないことを確認する。

### 7. コミット・共有
- コミット前に`git diff`と`git diff --cached`を確認し、今回の実装・Schema・文書・配布物だけをパス指定でstageする。
- 生成元ソース、Schema、生成スクリプト、配布専用テスト、手順書をGitの正本とし、展開済みパッケージとZIPは既定ではコミットしない。
- 展開済みパッケージは同じソースの二重管理になり、checkout時の改行変換でmanifestのSHA-256が変わる可能性があるため、`.gitignore`対象のローカル引き渡し成果物として扱う。
- ユーザーが展開済みパッケージのバージョン管理を明示した場合だけ、改行変換を含むmanifest再検証方法を決めてからコミットする。
- `*.zip`はローカル引き渡し物として`.gitignore`対象であり、ユーザーの明示指示なしに`git add -f`しない。
- コミットメッセージは日本語で書く。
- push後は、ブランチ名、コミットID、push先、ローカルに残した未コミット変更を報告する。

## 実装時のコメント方針
- 実装・修正時は、創屋側の初心者でも処理を追える水準の日本語コメントを適切に入れる。
- コメント品質は、既存の2D・3Dビューワー実装と同等以上を基準とする。
- ファイル、公開クラス、公開関数、API、非同期ジョブ、外部I/Oの境界では、少なくとも以下を説明する。
  - 何を担当する処理か
  - どこから入力を受け、何を返すか
  - 処理の順序とデータの流れ
  - DB更新、ファイル操作、外部API呼び出しなどの副作用
  - 失敗または処理中断になる条件
  - その実装方式や責務分担を採用した理由
- コードを日本語へ言い換えるだけのコメントや、明白な1行処理への過剰なコメントは避ける。
- 複雑な条件分岐、正規化、照合、タグ採用、手動補正、セキュリティ境界には「何をしているか」だけでなく「なぜ必要か」も記載する。
- 実装を変更した場合は、古い説明が残らないよう関連コメント、docstring、XMLドキュメントも同時に更新する。
- テストと運用スクリプトには、実行目的、前提条件、検証対象、失敗時に何を疑うべきかを記載する。
- 依存ライブラリ、ビルド生成物、自動生成コードはコメント補強の対象外とし、生成元の正本へ説明を記載する。
- 実装完了時は `python scripts\audit_beginner_source_comments.py` を実行し、保守対象ソースのコメント不足がないことを確認する。

## やり取り項目リスト運用
- 開発先とのやり取り項目は、`C:\Users\s-iwata\Desktop\knowledge_system\ナレッジシステム_やり取り項目リスト.xlsx` の `検索関連やり取り項目リスト` シートに追記する。
- 新規追記前に、既存の `No.1` から最新番号までを確認し、完全重複だけでなく、論点の親子関係・未解消確認・再発確認も見て、既存項目へ統合すべきかを判断する。
- 新規項目として残す場合は、少なくとも以下を埋める。
  - `No`
  - `項目`
  - `ステータス`：新規起票時は `起票`
  - `確認者(アルパイン)`
  - `確認日`
  - `確認内容`
- `確認内容` には、情報不足にならないよう最低限以下を入れる。
  - 対象チャットの `URL`
  - `正解ファイル`
  - `不正解ファイル`
  - 何がどうずれたか
- `確認内容` には、可能なら「本来この資料から出るはず」という観点を明示する。
- 既存項目と関連が強いが別起票で残す場合は、`備考欄` に `関連No: xx, yy` のように関連する項目番号を書く。
- `直した` と `直った` は分けて扱う。過去に `対応しました` となっていても、再確認で未解消なら、その事実が分かるように起票または関連Noで明記する。
- 今回の会話で追加した `No.31` 以降は、追撃条件の再反映不足、案件名と根拠の対応崩れ、規格表の列挙ズレ、改造対応項目の誤着地、Excel/Word仕様書の誤着地・過剰混線を記録している。

## Excel整理方針
- `事実` と `改善提案` は必ず別セル・別列に分ける。
- 開発先に確認したい論点がある場合は `開発先確認事項` に入れる。
- `優先対応` は基本的にこちら側の整理用とする。

## 対外共有の温度感
- 現時点では、開発先や客先には
  - 「こういう問題があった」
  - 「こういうのは直せないか」
 というレベルで共有する。
- こちら側の内部優先順位づけや細かな実装推測は、すぐには外へ出さない。

## 現時点の検証所見
- `SES` は初回だと一般語に誤解しやすいが、追撃で「澁谷工業の社内規格」と定義すると改善する。
- ただし、追撃後も参考資料の混線は残る場合がある。
- `コマツ小山のガントリーの走行速度` のように、案件名とカテゴリ名が明確な質問は比較的安定している。
- `資料なし` のときでも、無関係寄りの参考資料を付けてしまう傾向がある。
- `BOM/部品 -> 案件名` の変換は弱く、用途名・部品名・案件名・不具合件名が混ざりやすい。
- `広島アルミのガントリー関連資料` は、初回だと側部カバーや干渉チェック資料へ流れやすい。
- 2Dビューワーはアルパイン側で表示の滑らかさを改善済み。旧ドキュメントでは未記載だったため、2026-05-19に `docs\PDMナレッジシステム見積調査まとめ_2026-04-27.md` へ追記済み。
- 2Dビューワーについては、本体改善そのものよりも、ナレッジシステム側の図面詳細・類似検索結果・図面管理導線へどこまで組み込むか、創屋との責任境界を確認する必要がある。

## 現時点のローカル検証素材
- コピー先:
  - `C:\Users\s-iwata\Desktop\knowledge_system\local_test_materials`
- 主なファイル:
  - `komatsu_koyama_gantry\【製作仕様書】20220404_KO小山ガントリー装置STEP2.pdf`
  - `komatsu_koyama_gantry\C5A0-00_ガントリー品質要求事項確認チェックリスト.xlsx`
  - `hiroshima_alumi_gantry\現地改造計画図.pdf`
  - `hiroshima_alumi_gantry\ケースライン確認図.pdf`
  - `hiroshima_alumi_gantry\20241202_対応項目.txt`
  - `shibuya_specs\熱処理指定方法_2GDE82D.pdf`
  - `shibuya_specs\材料の熱処理適性および硬さ_2GDE81D.pdf`
  - `shibuya_specs\長穴の寸法_2GDE03D.pdf`

## 次会話での最重要前提
- 利用者は「装置メーカーの設計者」である。
- 質問設計は、一般検索や雑談ではなく、設計実務で使う粒度に寄せること。
- 評価基準は以下を優先する。
  - 案件名・客先名・装置名で正しく絞れるか
  - 部品/BOM情報から設計判断に必要な粒度まで上がれるか
  - 無い情報を無いと言えるか
  - 根拠が別案件に混ざらないか
  - 追撃で条件を足したときに改善するか

## 次会話で優先して進めること
- 2Dビューワーの滑らか表示改善を反映した外部共有用資料として、`ナレッジシステム_第一段階_進捗報告_2Dviewer反映_2026-05-19.pptx` と `ナレッジシステム_第一段階_進捗報告_2Dviewer反映_2026-05-19.pdf` を作成済み。元の `ナレッジシステム_第一段階_進捗報告.pptx` はロックファイルが存在したため未上書き。
- 2Dビューワー改善済み版の組み込み範囲を、開発先確認事項として整理する。
- ICAD 3D 抽出 PoC を `C# 抽出コア + Django 連携前提` で具体化する。
- ICAD 2D 抽出 PoC を同じ境界で具体化する。
- `図面管理` のタグ・属性正本モデルを、Django app として後移植できる形で設計する。
- `SMC案件` の 4 段階比較:
  1. 初回曖昧質問
  2. 追撃で用語定義
  3. 追撃で除外条件
  4. 追撃で出力形式指定
- `広島アルミのガントリー関連資料` の 4 段階比較
- `澁谷工業` で `SES` を使わない規格質問の 4 段階比較
- 結果は `rag_test_summary_2026-04-23.xlsx` に追記する

## Windows側確認事項(2026-07-17 抽出・タグ改善)
- 詳細手順と成果物の定義: `docs/windows_confirmation_items_2026-07-17.md`
- A. 幾何公差の種別・値がSXNET(SxGeomTol)から取れるか。取れれば「幾何公差:平行度」等をタグ化する。
- B. 溶接記号の種別(すみ肉/開先/現場)判別の可否。weld_notes 実値の収集。
- C. 図枠のラベル・値は同一テキスト要素内だけを自動対応とし、別要素間の汎用座標ペアリングは費用対効果と誤対応リスクを考慮して実装しない。座標は表示・監査証跡として保持し、特定客先で効果が確認できた場合だけ限定対応を再検討する。
- D. PRFXの実フィールド名と値形式。`User_PRFX` 以外の名前や「0030」型の値のみのケースを客先別に整理する。
- E. 熱処理・硬度注記の実例収集。今回実装の辞書(焼入れ/浸炭/窒化/高周波等)とHRC/HVパターンでの取りこぼし確認。
- F. 尺度表記の実態(S=1:6か裸の1:6か)。テーパ併記での誤確定がないか確認。
- G. 部品数=外部参照パーツの妥当性。実BOM感覚と合うか、ミラー・複数参照の数え方の確定。
- H. 客先・装置・案件の辞書語彙の収集(辞書は2026-07-17にDB化済み。システム設定>タグ辞書管理のGUIまたは/adminから登録でき、案件辞書はパス照合で`案件:`タグになる)。フォルダ命名規則(`日付_案件名(担当者様)`)の一覧化も継続。
- 2026-07-17 実装済み(Windows側は `git pull` 後に `python manage.py renormalize_drawing_metadata_snapshots` で既存データへ反映):
  - 装置の部品数を外部参照パーツのみへ変更(内部パーツは参考属性)
  - 尺度 `1:6` / `S=1:6` のパターン判定(候補1種類のときのみ確定)
  - 熱処理辞書+硬度指定(HRC/HV等)の抽出とタグ化
  - 手動補正が再抽出・統合で消えない合成方式への修正(タグ削除の復活防止、補正のキー単位マージ)
  - タグ辞書のDB化とGUI(システム設定>タグ辞書管理、/admin)。初回は `python manage.py seed_tag_dictionaries` を実行

## 更新日
- 2026-07-30 創屋向け最小パッケージのCodex確認型再生成手順を追記
- 2026-07-17 Windows側確認事項を追記
