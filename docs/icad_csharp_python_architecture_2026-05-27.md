# ICAD抽出の C# / Python 分担アーキテクチャ案

- 作成日: 2026-05-27
- 目的: ICAD 2D/3D のタグ・属性抽出を実装する際に、`C#` と `Python` の責務分担、境界、入出力、実装順序を明確にする。
- 対象:
  - `sxnet` を使う ICAD ネイティブ抽出
  - 抽出後の正規化、タグ生成、保存、RAG 連携
  - Django ベースのナレッジシステムからの呼び出し方式

## 1. 参照元

| 参照元 | 本資料で使う観点 |
| --- | --- |
| `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_design_plan_2026-05-26.md` | タグ・属性の正本モデル、抽出後フロー |
| `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_investigation_2026-05-26.md` | 2D/3D で取れそうな情報、速度見立て |
| `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\default.html` | `sxnet` が .NET クラスライブラリであることの確認 |
| `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxWF@methods.html` | 3D 側の一括取得 API の確認 |
| `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxEntSeg.getGeomList.html` | 2D 側の一括取得 API の確認 |
| `C:\Users\s-iwata\Desktop\knowledge_system\sxnet\sxnet\sxnet.SxEnt.getInfList.html` | 配列取得 API の確認 |

## 2. 結論

- `sxnet` 直結の抽出コアは `C#` を第一候補とする。
- `Python` は抽出後の正規化、タグ生成、保存、RAG 連携、ジョブ制御を担当する。
- ただし今回の `Python` は単独スクリプトではなく、基本的に `Django の service / task 層` として考える。
- `Python -> C#` は「細かい API 呼び出し」ではなく、「1図面単位の一括呼び出し」にする。
- 実装では、`sxnet.dll` 未提供でも先に進められるよう、`C#` 側は **reflection ベース**で組み、`sxnet` への静的参照を避ける。
- Django / worker は Linux や Docker に載せやすい形にし、`net48` 抽出器は Windows 側へ閉じ込める。
- 境界の基本方針は以下。
  - C#:
    - ICAD ファイルを開く
    - `sxnet` API をまとめて呼ぶ
    - 生抽出 JSON を返す
  - Python / Django:
    - JSON を受ける
    - `canonical_attributes` を作る
    - `derived_tags` を作る
    - `図面管理` / viewer / RAG に流す

## 3. なぜ C# を優先するか

### 3.1 `sxnet` との親和性

- `sxnet` は .NET クラスライブラリとして提供されている。
- ドキュメントも C# / VB シグネチャ前提で整理されており、`.NET` 呼び出しが自然である。
- `pythonnet` で Python から直接叩く方法もあるが、CAD オブジェクトを細かく跨ぐと境界コストが増える。

### 3.2 高速化しやすい

- 2D では `SxEntSeg.getGeomList()` による一括取得が可能である。
- 3D では `SxWF.getInfPartTree()` により階層、部品詳細、任意情報をまとめて取れる。
- これらを C# 側で完結させれば、Python/C# 間の往復を `1図面=1回` に抑えられる。

### 3.3 保守しやすい

- C++ を噛ませるより、`sxnet.dll` との接続は C# の方が実装負荷・保守負荷が低い。
- 今回のボトルネックはネイティブ数値計算よりも、CAD オブジェクト走査と情報抽出の境界設計にある。
- そのため、まず C# で抽出コアを作る方が費用対効果が高い。

## 4. なぜ Python も残すか

- タグ・属性の正規化は、辞書更新やルール改善を頻繁に回したい。
- `図面管理` 保存、RAG インデックス投入、検証スクリプトとの接続は Python の方が機動力が高い。
- OCR や PDF/Word/Excel など、ICAD 以外の形式との連携資産は Python に寄せた方が全体統合しやすい。
- ナレッジシステム本体が Django で構築されている前提なら、抽出後処理を Django のモデル、トランザクション、ジョブ管理と自然につなぎやすい。

## 4.1 Django 前提での Python の位置づけ

- 今回の `Python` は、以下のいずれかの形で Django 配下に置く前提が自然である。
  - `app/services/...`
  - `app/tasks/...`
  - `management/commands/...`
- つまり、役割分担の本質は `C# vs Python` だけでなく、実運用では `C# 抽出コア vs Django オーケストレーション層` と捉える方が正確である。
- Django 側で担うべきこと:
  - 抽出ジョブの作成
  - C# 呼び出し
  - JSON の受け取り
  - 正規化
  - タグ生成
  - DB 保存
  - viewer / RAG 連携

## 5. 推奨分担

| 領域 | C# | Python / Django |
| --- | --- | --- |
| ICAD ファイルオープン | 主担当 | なし |
| `sxnet` API 呼び出し | 主担当 | なし |
| 3D 部品階層取得 | 主担当 | なし |
| 2D 文字・寸法・注記取得 | 主担当 | なし |
| 生抽出 JSON 生成 | 主担当 | なし |
| 抽出ジョブ起動 | 補助 | 主担当 |
| 属性正規化 | なし | 主担当 |
| タグ生成辞書適用 | なし | 主担当 |
| `manual_overrides` 反映 | なし | 主担当 |
| 図面管理保存 | なし | 主担当 |
| viewer 連携 | なし | 主担当または API 接続担当 |
| RAG インデックス投入 | なし | 主担当 |

## 5.1 Django からの呼び出し方式

### 推奨フロー

1. Django の図面登録処理で抽出ジョブを作成する
2. Django の task 層から C# 抽出器を呼ぶ
3. C# が生抽出 JSON を返す
4. Django service 層で `canonical_attributes` と `derived_tags` を生成する
5. Django model 層で `図面管理` の正本へ保存する
6. 必要に応じて RAG インデックス更新や viewer detail 更新を後続ジョブで実行する

### 呼び出し元の候補

- `View` / `APIView`
  - 入口としてはあり
  - ただし重い処理は request thread に残さない
- `Celery` などの非同期 task
  - 第一候補
  - 抽出、OCR、RAG 再インデックスの本命
- `management command`
  - バッチ再抽出やメンテナンス用途に向く

### 避けたい構成

- Django の view から直接、長時間 C# 抽出を同期実行する
- request/response の中で OCR や STEP 重解析まで完走させる
- Django model や serializer の中から直接 C# プロセス起動を行う

## 6. 境界の切り方

## 6.1 良い切り方

- `1図面 -> C# 1回呼び出し -> JSON 1つ返却`
- C# 側でループを回し切る
- Django service 層は JSON を受けて意味付けする

## 6.2 悪い切り方

- Python から `part` 1個ずつ問い合わせる
- Python から `segment` 1本ずつ問い合わせる
- Django/Python 側で `sxnet` オブジェクトを細かく持ち回る
- C# 側で正規化辞書まで抱え込み、業務ルール変更のたびに再ビルドする

## 7. 推奨実行モデル

## 7.1 第一候補: Python から C# CLI/EXE を呼ぶ

### 概要

- Django task / service が C# の抽出実行ファイルを起動する。
- C# は ICAD から抽出して JSON を返す。
- Django 側は JSON を読み込んで後段処理を行う。

### 利点

- プロセス分離できる
- C# 側が落ちても Python 本体を巻き込みにくい
- `sxnet` 周りの依存を C# 側に閉じ込めやすい
- 実運用でバッチ処理に載せやすい

### 向く用途

- 最初の PoC
- バッチ登録
- 図面管理の非同期抽出ジョブ

### 2026-05-28 実装反映

- `src/IcadExtraction.Runner`
  - `extract`
  - `self-check`
  を実装済み
- `src/IcadExtraction.SxNet`
  - `SxFileModel.open(true)` でモデルを開く経路を採用
  - 3D は `SxModel.getGlobalWF()` -> `getInfPartTree()` / `getInfExTopPart()`
  - 2D は `SxModel.getGlobalVS()` -> `getSegList(...)` -> `SxEntSeg.getGeomList(...)`
- `sxnet.dll` が無い状態でも build/test できるよう、実装は reflection 呼び出しで統一した

## 7.2 第二候補: Python から C# DLL を呼ぶ

### 概要

- Python から `pythonnet` などで C# ライブラリを直接呼ぶ。

### 利点

- プロセス生成コストが減る
- 応答は軽くできる

### 欠点

- 例外処理、依存解決、ランタイム差異の扱いが難しくなる
- 境界設計を間違えると往復回数が増えて遅くなる

### 向く用途

- CLI 方式で十分に安定した後の最適化

## 7.3 今回の推奨

- 最初は `C# CLI/EXE + Python orchestration` を推奨する。
- まずは安定性と責務分離を優先し、境界越えを最小化する。

## 8. C# 側の責務

### 8.1 3D 抽出

- `SxWF.getInfPartTree()` を起点に、以下を収集する。
  - 部品階層
  - 部品名
  - コメント
  - 外部参照図面名
  - 参照パス
  - 外部パーツ/未解決/ミラー情報
- `SxWF.getInfExTopPart()` で最上位任意情報を取得する。

### 8.2 2D 抽出

- `SxEntSeg.getGeomList()` を起点に、以下を収集する。
  - 一般文字
  - 注記
  - 寸法値
  - 公差
  - 記号
  - 溶接注記
  - バルーン関連情報

### 8.3 出力

- C# 側は「意味付け前の生抽出」を JSON 化して返す。
- この段階では、客先名や案件名を最終決定しない。
- 返すべき最小単位:
  - `source_format`
  - `source_kind`
  - `elapsed_ms`
  - `warnings`
  - `raw_extract`

## 9. Python 側の責務

ここでの Python 側責務は、実装上は Django service / task 層へ載せる前提とする。

### 9.1 正規化

- 抽出結果から `canonical_attributes` を構築する。
- 表記ゆれ、略語、別名、部署内通称を辞書で吸収する。

### 9.2 タグ生成

- `canonical_attributes` を元に `derived_tags` を作る。
- 例:
  - `equipment_category=ガントリー` -> `装置:ガントリー`
  - `maker_keywords=SMC` -> `メーカー:SMC`

### 9.3 運用連携

- `図面管理` 保存
- `manual_overrides` の適用
- viewer 向け detail 生成
- RAG インデックス投入

### 9.4 Django 側の追加責務

- 抽出ジョブ状態管理
- 失敗時のリトライ
- タイムアウト制御
- 排他制御
- 監査ログ
- 管理画面や API への状態返却

## 10. 入出力契約の推奨

## 10.1 C# 入力

- `input_path`
- `output_path` または標準出力
- `source_kind` 省略可
- `timeout_seconds`

## 10.2 C# 出力

```json
{
  "input_path": "string",
  "source_format": "icad",
  "source_kind": "2d|3d",
  "extractor_name": "icad-csharp-extractor",
  "extractor_version": "string",
  "elapsed_ms": 0,
  "warnings": [],
  "raw_extract": {}
}
```

## 10.3 Python の後段成果物

```json
{
  "raw_extract": {},
  "canonical_attributes": {},
  "derived_tags": [],
  "manual_overrides": {}
}
```

## 11. 速度観点での役割分担

### C# に置くべき処理

- CAD オブジェクト走査
- 型判定
- セグメント/部品の大量ループ
- 一括取得 API の利用

### Python に置くべき処理

- 辞書適用
- 属性正規化
- タグ付与
- 保存・更新
- 検証・レポート

### Django に残すべき処理

- モデル保存
- トランザクション管理
- ジョブ投入
- 実行履歴管理
- 外部 API や RAG 更新の制御

### 同期/非同期の切り分け

- 同期寄り:
  - ICAD 3D メタデータ抽出
  - ICAD 2D 文字/寸法抽出
- 非同期ジョブ寄り:
  - OCR
  - STEP の重解析/重変換

## 12. 推奨プロジェクト構成

### C# 側

- `IcadExtractionRunner`
- `Icad3DExtractor`
- `Icad2DExtractor`
- `ExtractionResultDto`
- `JsonOutputWriter`

### Python 側

- `app/services/icad_extraction_runner.py`
- `app/services/normalize_icad_extract.py`
- `app/services/build_icad_tags.py`
- `app/services/persist_drawing_metadata.py`
- `app/services/rag_index_bridge.py`
- `app/tasks/icad_extraction_tasks.py`
- `app/management/commands/reextract_icad_metadata.py`

### Django 側の入口イメージ

- 図面登録 API
- 図面再抽出 API
- 管理画面からの再実行
- バッチ再抽出 command

## 13. 実装順序

1. C# で 3D 抽出 CLI を作る
2. 3D 生抽出 JSON の形を固定する
3. Python で正規化とタグ生成を作る
4. C# で 2D 抽出 CLI を作る
5. `図面管理` 保存と viewer/RAG 連携をつなぐ

## 14. この構成で避けられる失敗

- Python から `sxnet` を細かく呼びすぎて遅くなる
- Django の request thread を長時間ブロックする
- 業務ルール変更のたびに C# を全面改修する
- OCR や STEP の重処理まで同期登録に入れて待ち時間を悪化させる
- ICAD ネイティブ抽出とタグ付与ルールが密結合になる

## 15. 未確定事項

1. C# 実行環境をどこに置くか
2. `sxnet.dll` の正式配置と参照条件
3. C# CLI 方式で始めるか、最初から DLL 方式にするか
4. `図面管理` 保存 API の正式契約
5. 2D/3D 実サンプルの提供方法

## 16. 結論

- 今回の案件では、`高速化が必要なところは C#` という方針は妥当である。
- ただし、C# を広げすぎず、`ICAD ネイティブ抽出コア` に責務を限定するのが重要である。
- ナレッジシステムが Django 前提である以上、実装の現実形は `C# 抽出コア + Django(Python) 正規化/保存/連携` と整理するのが最も自然である。
- `C# 抽出コア + Django(Python) 正規化/保存/連携` が、速度、実装難易度、保守性のバランスが最も良い。
