# ICAD→DXF／STEP 独立変換 利用・引継ぎ手順

## 1. 結論

ICADからDXF、ICADからSTEPへの変換は、**Djangoを起動せずに利用できます**。

変換の正本は次の2層です。

| 層 | 正本 | 役割 | Django依存 |
|---|---|---|---|
| 変換コア | `src/IcadExtraction.SxNet/IcadCadFormatExporter.cs` | SXNETの`SxModel.export`を呼び、DXFまたはSTEPを生成する | なし |
| プロセス入口 | `src/IcadExtraction.Runner/IcadExtraction.Runner.csproj` の `convert-cad` | ICAD起動、セッション排他、入力準備、結果JSON、終了コードを管理する | なし |
| 手動・バッチ入口 | `scripts/convert_icad_standalone.ps1` | 引数検証、既存ファイル保護、Runner呼び出し、成果物検証を行う | なし |
| Django連携 | `backend/apps/drawing_metadata/services/extraction_runner.py` | Djangoジョブから同じRunnerを呼ぶ | Django側だけ |

Django管理コマンド`convert_icad_cad_formats`は独立変換の本体ではなく、登録済み図面と変換結果をDjangoへ取り込むための利用側です。

創屋側でDjangoへ組み込む前の動作確認、別システムからのバッチ実行、障害切り分けには、`convert_icad_standalone.ps1`を使用してください。低水準の`convert-cad`を直接組み立てるより、既存ファイル保護と完了確認を共通化できます。

## 2. 実行時に必要なもの

- Windows
- ICAD SX本体と、利用環境で有効なライセンス
- ICADに対応する`sxnet.dll`
- .NET Framework 4.8
- publish済み`IcadExtraction.Runner.exe`一式
- 入力`.icd`への読み取り権限
- 出力フォルダへの作成・書き込み権限

変換処理中だけICADとSXNETが必要です。生成済みDXF／STEPの参照や、Django側の保存・検索にはICADは不要です。

## 3. 配布物の作成

リポジトリのルートで、.NET Framework 4.8版をpublishします。

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"] = "utf8"; dotnet publish "src\IcadExtraction.Runner\IcadExtraction.Runner.csproj" -c Release -f net48 --no-self-contained'
```

創屋側へは、次を同じ版として渡します。

- `src\IcadExtraction.Runner\bin\Release\net48\publish\`配下の全ファイル
- `scripts\convert_icad_standalone.ps1`
- 本書

RunnerのEXEだけを抜き出さないでください。`IcadExtraction.Contracts.dll`、`IcadExtraction.SxNet.dll`、`Newtonsoft.Json.dll`などの同梱DLLも必要です。

## 4. 初回設定

PowerShellセッションで次の環境変数を設定すると、毎回パスを指定せずに利用できます。

```powershell
$env:ICAD_CONVERTER_RUNNER_PATH = "C:\path\to\IcadExtraction.Runner.exe"
$env:ICAD_CONVERTER_SXNET_DLL_PATH = "C:\path\to\sxnet.dll"
$env:ICAD_CONVERTER_ICAD_EXECUTABLE_PATH = "C:\path\to\icad.exe"
```

既存のWindows抽出agentと同じPCでは、`ICAD_CONVERTER_SXNET_DLL_PATH`が未設定の場合に限り、`DRAWING_METADATA_SXNET_DLL_PATH`も参照します。

環境変数を使わず、実行ごとに`-RunnerPath`、`-SxNetDllPath`、`-IcadExecutablePath`を指定しても構いません。ICADをあらかじめ起動している場合、`-IcadExecutablePath`は省略できます。

## 5. 実行前確認

最初は`-ValidateOnly`を付けます。ICADを起動せず、ファイルも生成せずに、入力・Runner・SXNET・出力先の解決結果を確認できます。

```powershell
pwsh -NoLogo -NoProfile -File "scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\drawing\sample.icd" `
  -OutputFormat dxf `
  -OutputDirectory "C:\converted" `
  -ValidateOnly
```

確認する項目は次のとおりです。

- `InputPath`が対象ICADの絶対パスになっている
- `OutputFormat`が`dxf`または`step`になっている
- `RunnerPath`がpublish済みEXEを指している
- `SxNetDllPath`が対象ICAD版のDLLを指している
- ICADを自動起動する場合は`IcadExecutablePath`が表示される

## 6. DXFへ変換

```powershell
pwsh -NoLogo -NoProfile -File "scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\drawing\sample.icd" `
  -OutputFormat dxf `
  -OutputDirectory "C:\converted"
```

成功時は、次の2ファイルが生成されます。

- `C:\converted\sample.dxf`
- `C:\converted\sample.dxf.conversion.json`

PowerShellの戻り値には`ConvertedPath`、`SizeBytes`、`ResultJsonPath`、`WarningCount`、`IcadAutostarted`、`RunnerTerminatedAfterCompletedResult`、`IcadShutdownAfterRunnerTermination`、`Completed`が含まれます。

## 7. STEPへ変換

```powershell
pwsh -NoLogo -NoProfile -File "scripts\convert_icad_standalone.ps1" `
  -InputPath "C:\drawing\sample.icd" `
  -OutputFormat step `
  -OutputDirectory "C:\converted"
```

成功時は、次が生成されます。

- `C:\converted\sample.step`または`C:\converted\sample.stp`
- `C:\converted\sample.step.conversion.json`

STEPの実拡張子はSXNETの版・出力実装により`.step`または`.stp`です。後続処理は固定名を組み立てず、PowerShell戻り値の`ConvertedPath`、または結果JSONの`converted_asset.file_path`を使用してください。

## 8. 出力名、上書き、ICAD終了の指定

### 8.1 出力名を変える

```powershell
-OutputBaseName "converted_part_001"
```

`OutputBaseName`にはフォルダを含めず、拡張子を除いた名前だけを指定します。

### 8.2 既存ファイルを上書きする

既存DXF／STEPまたは結果JSONがある場合、スクリプトは既定で処理を中断します。内容を確認し、置き換えてよい場合だけ次を付けます。

```powershell
-Overwrite
```

### 8.3 自動起動したICADを残す

既定では、Runnerが自動起動したICADだけを変換後に終了します。利用者が先に起動していたICADは終了対象にしません。連続した手動検証で自動起動分を残す場合だけ次を付けます。

```powershell
-KeepAutostartedIcadOpen
```

### 8.4 SXNET用の一時短縮パスを強制する

長いパスやSXNET側のパス解釈問題を切り分ける場合だけ次を付けます。原本は変更せず、一時コピーをSXNETへ渡します。

```powershell
-ForceSxNetStagedInput
```

## 9. 結果JSONの判定

成功と判定する最低条件は次のすべてです。

- プロセス終了コードが`0`、または完成済み成果物の確認後に限り`RunnerTerminatedAfterCompletedResult=true`
- `completed`が`true`
- `converted_asset.status`が`ready`
- `converted_asset.file_path`が存在する
- 変換ファイルが0バイトではない

`convert_icad_standalone.ps1`は上記を確認し、満たさない場合はPowerShellエラーとして処理を中断します。ただし、SXNETの版によっては成果物完成後のモデル後片付けだけが完了しないことがあります。この場合に限り、スクリプトは完成済み結果を確認してからRunner子プロセスを終了し、`RunnerTerminatedAfterCompletedResult=true`を返します。Runnerが自動起動したICADは、続けて`shutdown-icad`で保存せず終了し、`IcadShutdownAfterRunnerTermination=true`を返します。利用者が事前起動したICADは終了しません。

呼び出し側で未完了JSONや0バイトファイルへ既定値を補い、成功扱いにしないでください。

結果JSONには、少なくとも次を保持します。

| 項目 | 用途 |
|---|---|
| `input_path` | 変換元ICADの原本パス |
| `source_file` | 原本とSXNETへ渡したパスの関係 |
| `output_format` | 正規化済みの`dxf`または`step` |
| `elapsed_ms` | 変換時間 |
| `icad_autostarted` | RunnerがICADを起動したか |
| `completed` | 変換完了フラグ |
| `warnings` | 一時パス利用など、処理を中断しない注意事項 |
| `converted_asset` | 実ファイル名、パス、拡張子、MIME type、サイズ |

## 10. SXNET出力形式番号の確認

ICAD／SXNETの版によって、`SxOptExport`の定数名が異なる可能性があります。推測した数値を使用せず、実機DLLを調査します。

```powershell
& "C:\path\to\IcadExtraction.Runner.exe" probe-cad-export-types `
  --sxnet-dll-path "C:\path\to\sxnet.dll" `
  --output-path "C:\temp\sxnet_export_types.json"
```

結果JSONの`expected_formats.step.matches`と`expected_formats.dxf.matches`を確認します。期待する定数が公開されていない環境では、確認済みの数値だけを`-ExportFileType`へ指定します。

```powershell
-ExportFileType 123
```

## 11. 創屋側システムからの推奨呼び出し方

言語を問わず、RunnerまたはPowerShellスクリプトを**1図面につき1プロセス**で呼び出してください。

推奨境界は次のとおりです。

1. 創屋側で入力ICADと出力先を確定する
2. `convert_icad_standalone.ps1`を子プロセスとして起動する
3. 終了コードを確認する
4. 戻り値の`ConvertedPath`または結果JSONの`converted_asset.file_path`を取得する
5. ファイル存在・サイズを確認してから、後続の保存・抽出・表示へ渡す
6. 失敗時は標準エラーと結果JSONをジョブログへ保存する

`IcadCadFormatExporter`を直接DLL参照する方法もありますが、呼び出し側がICAD起動、排他、SXNETコンテキスト破棄、一時入力の後始末を正しく実装する必要があります。創屋側へ最初に引き継ぐ境界は、プロセス分離されたRunner／PowerShell入口を推奨します。

## 12. 運用上の注意

- 同じWindowsログオンセッションでは、Runnerが名前付きMutexでICAD利用を直列化します。
- ICAD初回起動には時間がかかるため、独立変換スクリプトの起動待ちは既定30秒です。必要な場合は`-IcadStartupWaitSeconds`で調整します。
- 変換全体の既定タイムアウトは600秒です。変更する場合は`-RunnerTimeoutSeconds`、ICAD終了待ちは`-IcadShutdownTimeoutSeconds`を使用します。
- 変換中はICADセッションを占有するため、人が編集中のICADと自動変換を同居させない運用を推奨します。
- 入力ICADは読み取り専用で開きます。変換先は別フォルダにしてください。
- 低水準`convert-cad`は同名出力を置き換えます。手動・創屋側バッチでは保護確認のあるPowerShell入口を使用してください。
- DXF／STEPは交換形式のため、ICAD正本の材質、質量、部品付加情報、完全なアセンブリ意味を常に保持するとは限りません。
- STEPは主に3D形状・製品構造、DXFは主に2D図形・文字・寸法・レイヤーの受け渡しに使用します。

## 13. 創屋側の受入チェックリスト

- [ ] 配布先PCで`-ValidateOnly`が成功する
- [ ] 代表ICADからDXFを1件生成できる
- [ ] 代表ICADからSTEPを1件生成できる
- [ ] 結果JSONの`completed=true`と実ファイルサイズを確認できる
- [ ] 既存成果物が`-Overwrite`なしで保護される
- [ ] ICAD版に対応した`sxnet.dll`を指定している
- [ ] 自動起動したICADだけが既定で終了する
- [ ] 標準エラーと結果JSONを創屋側ジョブログへ残せる
- [ ] 同一PCで変換ジョブを無制限並列実行しない

## 14. 関連資料

- `README.md`
- `docs/windows_extraction_agent_api_design_2026-07-29.md`
- `docs/icad_csharp_python_architecture_2026-05-27.md`
- `docs/cad_tag_extraction_sources_for_souya_2026-07-28.md`
- `docs/extraction_result_schema_2026-05-28.md`

## 15. 実機確認記録

2026-07-29に、publish済みnet48 Runnerと`scripts/convert_icad_standalone.ps1`を使い、同じ検証用ICADから次を確認しました。

| 確認項目 | 結果 |
|---|---|
| `-ValidateOnly` | ICADを起動せず、入力・Runner・SXNET・ICAD実行体・出力先を解決 |
| ICAD→STEP | 成功、`.stp` 47,128 bytes、結果JSON`completed=true` |
| ICAD→DXF | 成功、`.dxf` 1,063,724 bytes、結果JSON`completed=true` |
| DXF後片付け待ち | 完成済み結果を確認後にRunnerのみ終了 |
| 自動起動ICADの後処理 | `shutdown-icad`で保存せず終了、ICAD／Runner残留なし |
| 既存成果物保護 | `-Overwrite`なしでは実行前に中断 |
| .NETテスト | Contracts 3件、SXNET 30件、Runner 8件、合計41件成功 |
| コメント監査 | 対象268ファイル、要補強0件 |
