# Docker Web / Windows ICAD抽出エージェント接続設計

- 作成日: 2026-07-29
- 目的: Django WebをLinux/Dockerへ配置したまま、ICAD・SXNET・C#抽出器をWindowsホストへ分離し、安全にジョブ連携できる状態を完成させる。

## 1. 参照ドキュメント一覧

| 参照先 | 抽出内容 |
|---|---|
| `AGENTS.md` | Docker側とWindows側の責務、1図面1回呼び出し、非同期ジョブ、エラー処理 |
| `README.md` | 現行PoC、Docker構成、C# Runner、Windows workerの現状 |
| `docs/icad_csharp_python_architecture_2026-05-27.md` | C#は生抽出、Djangoは正規化・タグ・保存を担当する境界 |
| `docs/django_integration_plan_2026-05-28.md` | DB-backed job、claim、lease、worker、snapshot保存の既存設計 |
| `docs/extraction_result_schema_2026-05-28.md` | C#抽出結果JSONの契約 |
| `docker-compose.backend.yml` | 現行Dockerサービス、永続ボリューム、worker起動方式 |
| `backend/apps/drawing_metadata/tasks/extraction_tasks.py` | claim、lease、抽出結果保存、失敗処理 |
| `src/IcadExtraction.Runner/Program.cs` | 既存C#抽出CLIと引数 |

## 2. 現状の問題

- Dockerの`worker`がDjango workerを起動し、`subprocess.run()`で抽出器を直接実行する。
- `.env`の抽出器、`sxnet.dll`、`icad.exe`はWindows絶対パスであり、Linuxコンテナから実行できない。
- SQLiteと抽出ファイルはDocker名前付きボリュームにあり、Windows workerから直接共有できない。
- Windows worker専用のclaim、入力取得、結果登録、preview asset転送、heartbeat APIがない。

## 3. 完成形

1. Django backendが抽出ジョブをDBへ登録する。
2. Docker workerはSTEP/DXF等のgeneric CADジョブだけを処理する。
3. Windows上の`IcadExtraction.Runner.exe agent`がBearer token付きHTTPでICADジョブをclaimする。
4. Windows agentは、Windowsから参照できる元パスを優先し、参照できない場合だけDjangoから入力をdownloadする。
5. agentは同じEXEの`extract`子プロセスを1図面1回起動する。
6. 抽出中はheartbeatを送信し、Djangoがjob leaseを延長する。
7. preview assetをDjangoへuploadした後、生抽出JSONをcomplete APIへ返す。
8. Djangoが正規化、タグ生成、snapshot、監査ログを保存する。
9. 失敗時はagentがfail APIへ明示的にエラーを返し、ジョブをfailedにする。

## 4. API契約

すべて`Authorization: Bearer <DRAWING_METADATA_AGENT_TOKEN>`を必須とする。worker所有権が必要なAPIでは`workerName`も照合する。

| Method | Path | 役割 |
|---|---|---|
| `POST` | `/api/v1/drawing-metadata/agent/jobs/claim` | ICADジョブを原子的にclaim |
| `GET` | `/api/v1/drawing-metadata/agent/jobs/{jobId}/source` | Docker側に入力がある場合のdownload |
| `POST` | `/api/v1/drawing-metadata/agent/jobs/{jobId}/assets` | preview assetを相対パス付きでupload |
| `POST` | `/api/v1/drawing-metadata/agent/jobs/{jobId}/complete` | 生抽出JSONを受け取りDjango後段処理を実行 |
| `POST` | `/api/v1/drawing-metadata/agent/jobs/{jobId}/fail` | 抽出失敗を登録 |
| `POST` | `/api/v1/drawing-metadata/agent/heartbeat` | agent状態を保存し、処理中jobのleaseを延長 |

claimが空の場合は`204 No Content`とする。重複処理を防ぐため、complete・fail・assetは`processing`かつ同一`workerName`のjobだけを受け付ける。

## 5. ファイルとパス

- `sourcePath`はWindows agentが直接参照できる場合だけ使用する。
- Docker側にupload済みの入力はsource APIから取得できる。
- preview assetはjob別ディレクトリへ保存し、相対パスの`..`、絶対パス、jobディレクトリ外への解決を拒否する。
- C#結果内のpreview URLはDjango APIの公開URLを使用する。
- agentの一時入力、結果、previewはjob別work directoryに置き、成功・失敗後に削除する。診断保持を明示した場合だけ残す。

## 6. エラーと再実行

- 認証失敗は`401`、worker所有権不一致は`409`、入力不在は`404`、不正payloadは`400`とする。
- API・ファイル・抽出エラーを握り潰さず、agentコンソールとDjango job errorへ出す。
- heartbeatでleaseを延長し、agent停止後にlease期限が切れたjobだけを別agentが再claimできる。
- complete済みjobを重ねて更新しない。

## 7. 完了チェックリスト

- [x] API名と引数名が本資料と一致
- [x] Bearer token未設定時にサーバーとagentが安全側で停止
- [x] Docker workerがICADジョブをclaimしない
- [x] Windows agentだけがICADジョブをclaim
- [x] sourcePath直接参照とHTTP downloadの両方を検証
- [x] preview assetのpath traversalを拒否
- [x] heartbeatでleaseが延長される
- [x] completeで既存の正規化・タグ・snapshot保存が実行される
- [x] failでジョブがfailedになりエラーが残る
- [x] Djangoテスト、C#テスト、Docker compose検証が成功
- [x] READMEと`.env.example`に起動方法と設定を記載
- [x] エラーハンドリングが`AGENTS.md`方針に準拠

## 8. 2026-07-29 実機確認結果

- Docker composeでbackendがhealthy、generic workerがrunningになることを確認した。
- ICADジョブを作成後、generic workerが7秒間claimせず`queued`を維持することを確認した。
- Windowsの`IcadExtraction.Runner.exe agent --once true`が同ジョブをclaimした。
- `cad_data/9NK452W650-00-PAD-A3-3D-01.icd`を使い、`C:\ICADSX\bin\icad.exe`の自動起動、SXNET 3D抽出、結果completeまで成功した。
- Django側jobは`succeeded`、extractorは`icad-csharp-extractor`、抽出時間は4,027msだった。
- snapshotで原本のWindowsフルパス、正規化属性、派生タグを確認した。
- agentがuploadしたSTLは130,547 bytesで、preview asset APIからHTTP 200で取得できた。
- agentが自動起動したICADは処理後に終了し、ICADプロセスが残っていないことを確認した。
