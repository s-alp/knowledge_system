# 別PCのICADをWindows抽出Agentとして接続する手順（創屋向け）

- 文書状態: **現行実装に基づく別PC配置手順**
- 基準日: 2026-07-30
- 対象:
  - Django Web/APIを動かすサーバーPC
  - ICAD、SXNET、C# Runnerを動かすWindows Agent PC
  - 同一社内ネットワークまたは信頼できる閉域網

## 1. 目的と現在の前提

現在の検証・初期導入は、DjangoとICADを同じWindows PCで動かす構成を既定とする。
別PCのICADを使う必要が生じた場合は、本書に従ってICAD搭載PCをWindows抽出Agentとして追加する。

別PC構成は現行コードで対応済みであるが、2026-07-30時点では同一社内ネットワーク上の別PCを使った
創屋環境での実機疎通は未確認である。創屋環境へ切り替える際は、後述の受入確認を実施してから常用する。

HTTP APIのrequest、response、Bearer token、lease、heartbeat、C# raw JSONの正本は
[`windows_extraction_agent_api_design_2026-07-29.md`](windows_extraction_agent_api_design_2026-07-29.md)とする。
本書は、同一PC構成から別PC構成へ切り替える作業手順と確認項目を補足する。

## 2. 構成と責務

```text
DjangoサーバーPC
  ├─ Web/API、ジョブ、DB、タグ・属性保存
  └─ 8000/TCP等でAgent APIを待受
          ↑ Windows AgentからのHTTP(S) + Bearer token
ICAD搭載Windows Agent PC
  ├─ ICAD本体、対応するsxnet.dll、ICADライセンス
  ├─ .NET Framework 4.8
  └─ publish済みIcadExtraction.Runner.exe一式
```

Windows AgentがDjangoへ定期的にjobを取りに行く。通常、Agent PCで外部からの受信ポートを開く必要はない。
受信許可が必要なのはDjangoサーバー側のAPIポートである。

## 3. Agent PCへ配置するもの

### 3.1 必須

- Windows
- ICAD本体と利用可能なライセンス
- ICADの版と互換性がある`sxnet.dll`
- .NET Framework 4.8
- `net48`向けにpublishした`IcadExtraction.Runner.exe`一式
- `scripts\start_windows_extraction_agent.ps1`
- 対象図面またはDjango APIへアクセスできるWindowsユーザー・セッション

EXEだけを抜き出さず、publishフォルダ内のDLLと設定ファイルを含む全ファイルを配置する。
publish済み一式を受け取る場合、Agent PCへC#ソース、Visual Studio、.NET SDKを入れる必要はない。
Agent PC自身でビルドする場合だけ、対応する.NET SDKとC#ソースが必要になる。

### 3.2 配置例

```text
C:\IcadExtractionAgent\
├─ publish\
│  ├─ IcadExtraction.Runner.exe
│  ├─ IcadExtraction.Contracts.dll
│  ├─ IcadExtraction.SxNet.dll
│  └─ その他publish出力
└─ scripts\
   └─ start_windows_extraction_agent.ps1
```

## 4. publishと配布

開発リポジトリから作成する場合:

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; dotnet publish "src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" -c Release -f net48 --no-self-contained'
```

創屋向け最小パッケージから作成する場合:

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; dotnet publish "csharp\src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" -c Release -f net48 --no-self-contained'
```

生成された`publish`フォルダの全ファイルと`start_windows_extraction_agent.ps1`をAgent PCへコピーする。
ソースとpublish済み成果物の版を混在させない。

## 5. Djangoサーバー側の設定

### 5.1 APIの待受

Docker構成は`docker-compose.backend.yml`で`0.0.0.0:8000`へbindし、ホストの8000番ポートを公開する。

Django開発サーバーで一時的に別PC疎通を確認する場合は、ループバック限定ではなく次のように起動する。

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" runserver 0.0.0.0:8000'
```

`runserver`は開発・疎通確認用であり、本番常用には使用しない。

### 5.2 環境変数

`backend\.env`等へ次を設定する。実際のtoken、社内IP、ホスト名は文書やGitへ記録しない。

```dotenv
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,<Agentが接続先として使うDjangoサーバーのIPまたはホスト名>
DRAWING_METADATA_AGENT_TOKEN=<十分に長いランダムtoken>
```

Djangoから存在確認できないWindowsドライブまたはUNCパスを`source.path`として登録し、
Agent PCから直接読む場合だけ次を有効にする。

```dotenv
DRAWING_METADATA_ALLOW_REMOTE_AGENT_PATHS=true
```

ブラウザからDjangoへアップロード済みの原本をAgentが`downloadUrl`で取得する構成では、
リモートパス許可を必須にしない。

設定変更後はDjangoプロセスまたはDockerコンテナを再起動し、設定を反映する。

### 5.3 ネットワーク

- Djangoサーバー側で使用するAPIポートへの受信を許可する
- 許可元は可能な限りAgent PCのIPまたは運用対象のサブネットへ限定する
- Agent PCからDjangoサーバーへの送信を許可する
- 別端末間はHTTPS、または管理された信頼できる閉域網を使用する
- Agentはブラウザではないため、Agent API通信のためだけにCORS許可元を追加しない

ファイアウォール変更は創屋側のネットワーク管理方針に従い、ポートを社外へ公開しない。

## 6. Agent PC側の設定

PowerShellセッションで次を設定する。`127.0.0.1`はAgent PC自身を指すため、別PC構成では使用しない。

```powershell
$env:DRAWING_METADATA_AGENT_API_BASE_URL = "http://<DjangoサーバーのIPまたはホスト名>:8000/"
$env:DRAWING_METADATA_AGENT_TOKEN = "<Django側と同じtoken>"
$env:DRAWING_METADATA_AGENT_WORKER_NAME = $env:COMPUTERNAME
$env:DRAWING_METADATA_SXNET_DLL_PATH = "C:\path\to\sxnet.dll"
$env:DRAWING_METADATA_ICAD_EXECUTABLE = "C:\path\to\icad.exe"
```

複数Agentを動かす場合、`DRAWING_METADATA_AGENT_WORKER_NAME`はAgentごとに一意にする。
既定のWindowsマシン名を使えば、通常は重複しない。

tokenをソース、設定例、ログへ書かない。常駐化するときの保存先と権限は創屋側の秘密情報管理方針に従う。

## 7. 図面の参照方式

### 7.1 Agent PCから直接読む

`source.path`をAgent PCが読めるUNCパスまたはローカルパスにする。
ネットワークドライブ文字はWindowsユーザーやログオンセッションごとに割り当てが異なるため、
常駐運用では可能な限りUNCパスを使用する。

Agent実行ユーザーには対象図面共有への読み取り権限だけを付与する。
外部参照パーツがあるICADでは、原本だけでなく参照先も同じユーザーから解決できることを確認する。

### 7.2 Djangoからdownloadする

Agent PCから`source.path`を直接読めない場合、Agentはclaim responseの`source.downloadUrl`から原本を取得する。
Django側に原本が保存され、download APIから取得できることが前提となる。

原本だけを一時downloadすると外部参照パーツを解決できない場合がある。
アセンブリの外部参照が必要な案件では、UNC直接参照または参照ファイル一式の受け渡し方式を採用する。

## 8. 初回疎通確認

### 8.1 TCP接続

Agent PCで次を実行する。

```powershell
Test-NetConnection -ComputerName "<DjangoサーバーのIPまたはホスト名>" -Port 8000
```

`TcpTestSucceeded`が`True`にならない場合、Agentを起動せず、IP・名前解決・待受・ファイアウォールを確認する。

### 8.2 Agentの1回実行

最初は`-Once`で起動する。キューが空なら疎通確認だけを行い、jobがあれば1件処理して終了する。

```powershell
pwsh -NoLogo -NoProfile -File "C:\IcadExtractionAgent\scripts\start_windows_extraction_agent.ps1" `
  -RunnerPath "C:\IcadExtractionAgent\publish\IcadExtraction.Runner.exe" `
  -Once
```

次を確認する。

1. Agentが設定不足やHTTPエラーなしで終了する
2. Django側でAgent heartbeatと`workerName`を確認できる
3. テスト用ICAD jobを1件だけ起票する
4. Agentがjobをclaimし、ICAD/SXNET抽出を実行する
5. jobが`succeeded`になり、raw JSON、タグ・属性が保存される
6. Django側の登録原本と抽出結果の`input_path`が同じ図面を示す
7. エラー時はAgentコンソールとDjango jobの両方に原因が残る

viewer用preview assetは創屋向け最小パッケージの必須範囲ではない。
創屋様側でviewer連携を別途採用した場合だけ、そのadapterと保存結果を追加確認する。

疎通確認後、`-Once`を外して常駐起動する。
Windowsサービス化やタスクスケジューラ登録は現行配布物の自動設定対象外である。
ICADライセンスと対話Windowsセッションの条件を確認してから、創屋側の運用方式を決める。

## 9. 主なエラーの切り分け

| 症状 | 主な確認先 |
|---|---|
| 接続拒否、timeout | Djangoのbind先、サーバーIP、APIポート、サーバー側ファイアウォール |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS`に、AgentがURLで使用したDjangoサーバーのIPまたはホスト名があるか |
| `401`または`403` | DjangoとAgentのtokenが同じか、余分な空白がないか |
| `503 agent_token_not_configured` | Django側の`DRAWING_METADATA_AGENT_TOKEN`と再起動 |
| `204 No Content` | エラーではなく、claim対象のICAD jobがない状態 |
| 原本が見つからない | UNC・ローカルパス、Agent実行ユーザーの権限、remote path許可、download API |
| 外部参照が欠落する | 一時downloadではなくUNC直接参照が必要か、参照先の権限 |
| `sxnet.dll`エラー | ICAD版との互換性、DLLパス、Runnerのbit数・target |
| ICADを起動できない | `icad.exe`パス、ライセンス、Windowsセッション、起動待機時間 |
| job所有権の`409` | `workerName`の重複、lease中の別Agent、job状態 |

エラーを既定値で回避せず、原因を解消してから再実行する。

## 10. 創屋側受入チェックリスト

- [ ] 現在の同一PC構成で既存のICAD抽出が成功する
- [ ] 別PC Agent用の固定IPまたは名前解決方法を決める
- [ ] Agent PCへpublishフォルダ一式、起動スクリプト、互換`sxnet.dll`を配置する
- [ ] ICADライセンスとWindowsセッションの運用条件を確認する
- [ ] Djangoの待受、`DJANGO_ALLOWED_HOSTS`、tokenを設定する
- [ ] 必要な場合だけ`DRAWING_METADATA_ALLOW_REMOTE_AGENT_PATHS=true`を設定する
- [ ] APIポートの許可元をAgent PCまたは必要なサブネットへ限定する
- [ ] Agent PCからTCP接続と`-Once`疎通を確認する
- [ ] UNC直接参照またはDjango downloadのどちらを使うか決める
- [ ] 外部参照を含む実図面で2D・3D抽出を確認する
- [ ] raw JSON、タグ・属性、エラー記録を確認する
- [ ] viewer連携を別途採用する場合だけ、preview assetの生成・保存・表示を確認する
- [ ] 常駐方法、実行ユーザー、token保管、ログ保管を決める

## 11. 完了条件

別PCのICADを対象にする切替は、疎通だけで完了としない。
実図面の2D・3D jobが同じAgent PCで成功し、参照パーツ、タグ・属性の保存結果、再実行時のleaseと所有権まで
確認できた時点で受入完了とする。
