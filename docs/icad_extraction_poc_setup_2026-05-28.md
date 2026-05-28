# ICAD抽出PoCセットアップ

- 作成日: 2026-05-28
- 目的: `knowledge_system` 内へ追加した standalone backend と C# 抽出 CLI を、次担当者が探索なしで起動できるようにする。

## 1. 追加した構成

### Django backend

- `C:\Users\s-iwata\Desktop\knowledge_system\backend\manage.py`
- `C:\Users\s-iwata\Desktop\knowledge_system\backend\knowledge_system_backend\`
- `C:\Users\s-iwata\Desktop\knowledge_system\backend\apps\drawing_metadata\`

### C# 抽出コア

- `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Contracts\`
- `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.SxNet\`
- `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.Runner\`
- `C:\Users\s-iwata\Desktop\knowledge_system\IcadExtraction.sln`

## 2. Django の起動

Windows PowerShell:

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; python -m venv "backend\.venv"'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe -m pip install -r "backend\requirements-base.txt"'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" migrate'
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" runserver'
```

## 3. worker の起動

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\backend\.venv\Scripts\python.exe "backend\manage.py" process_drawing_metadata_jobs --loop --sleep-seconds 5'
```

## 3.1 実抽出時の前提

- `sxnet.dll` が存在するだけでは不十分だった
- live 抽出では **ICAD 本体を起動済み**にしておく必要がある
- 未起動時は `self-check` は成功しても、`extract` が無出力のままタイムアウトする場合がある
- 少なくとも今回の環境では、起動対象は `C:\ICADSX\bin\icad.exe` だった
- worker が ICAD を自動起動する場合は、**その worker が起動した ICAD だけを終了対象にする**。既に人が起動していた ICAD は終了しない
- 最適構成は、Windows worker 専用の ICAD セッション、または専用マシンで運用すること
- 実サンプル確認は次の順で行う
  1. ICAD を起動
  2. `self-check`
  3. `extract`
  4. Django worker

## 4. Docker で載せる範囲

- `docker-compose.backend.yml` は以下を対象にする
  - `backend`
  - `worker`
- SQLite と抽出成果物は volume に出す
- ただし `sxnet.dll` / `net48` 抽出器は Docker コンテナ内で完結させる前提にしていない

## 5. C# 抽出 CLI

### self-check

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe self-check --sxnet-dll-path "C:\path\to\sxnet.dll"'
```

### 3D extract

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe extract --input-path "C:\path\to\sample_3d.icd" --source-kind 3d --output-path "C:\temp\sample_3d.json" --sxnet-dll-path "C:\path\to\sxnet.dll"'
```

### 2D extract

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe extract --input-path "C:\path\to\sample_2d.icd" --source-kind 2d --output-path "C:\temp\sample_2d.json" --sxnet-dll-path "C:\path\to\sxnet.dll"'
```

### ICAD 自動起動付き extract

```powershell
pwsh -NoLogo -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $PSDefaultParameterValues["*:Encoding"]="utf8"; .\src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe extract --input-path "C:\path\to\sample.icd" --source-kind 3d --output-path "C:\temp\sample.json" --sxnet-dll-path "C:\path\to\sxnet.dll" --icad-executable-path "C:\ICADSX\bin\icad.exe" --icad-startup-wait-seconds 8'
```

必要なら `--shutdown-icad-if-autostarted true|false` を渡せる。

## 6. 確認済み事項

- Django migration は通る
- Python pytest は通る
- `.NET` は `IcadExtraction.sln` で build / test が通る
- `net48` target の runner 実行ファイルは生成される
- `C:\ICADSX\bin\sxnet.dll` で `self-check` は成功する
- ICAD 起動済み状態では、3D `.icd` の live 抽出が成功する
- 同じ `.icd` に対して、`source-kind=2d` の live 抽出も成功する
- `job / snapshot` 単位の mode-aware 保存へ移行済み

## 7. 未確認事項

1. `sxnet.dll` の正式配置場所
2. 2D geometry の対応種類を増やす
3. Linux/Docker backend から Windows 抽出 worker をどう中継するか

## 8. 次にやること

1. 2D geometry の対応種類を増やす
2. worker から CLI を叩く実運用経路を確認
3. Linux/Docker backend から Windows 抽出 worker をどう中継するか決める
