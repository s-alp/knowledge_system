# ICAD共有サンプル抽出確認メモ

- 確認日: 2026-07-14 17:23:45 +09:00
- 対象: ユーザー共有の実ICADファイル 23件
- 出力先: `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\shared_icad_probe_2026-07-14`
- 実行方法: 現行 `IcadExtraction.Runner.exe` で各 `.icd` を `source-kind=2d` / `source-kind=3d` の両方で抽出

## 1. 結論

現行抽出器は、ICADファイル内に「2Dデータがあるか」「3Dデータがあるか」を明示判定できていない。

現在の実装は、呼び出し側が `source-kind=2d` または `source-kind=3d` を指定し、2Dなら `SxModel.getGlobalVS()`、3Dなら `SxModel.getGlobalWF()` を取得して処理する方式である。空に近い結果でも runner は exit code 0 になり得るため、成功可否だけでは「有効な2D/3Dが存在する」と判断してはいけない。

したがって、次の実装では `detect` または `extract --source-kind auto` を追加し、2D/3Dそれぞれについて以下を別々に返す必要がある。

- `has_2d`: 2D図面として扱える実体があるか
- `has_3d`: 3Dモデル/部品ツリーとして扱える実体があるか
- `2d_evidence`: texts, dimensions, geometry, print frames, VS info など
- `3d_evidence`: top part, part count, external refs, material/mass candidates など
- `confidence`: 件数と根拠に基づく判定信頼度

## 2. 実サンプル集計

| ファイル | 2D抽出の主な結果 | 3D抽出の主な結果 | 現時点の見立て |
| --- | ---: | ---: | --- |
| `U8105111315.icd` | texts=154, primitives=139, warning=1 | top_partあり, parts=1 | 2D図面情報が強い。3D名も候補として取れる |
| `217008-41J-3004.icd` | texts=71, primitives=49 | top_partあり, parts=1 | 2D図面情報が強い |
| `DFR-CM1-AA0305300011.icd` | texts=22, warning=21 | top_partあり, parts=1 | 2D注記に材料指示あり |
| `XH30-A08001-R03-JP_ロードカップ部改造.icd` | texts=0, primitives=1 | top_partあり, parts=575 | 3D組立が主。外部参照パーツ多数 |
| `XH3001-M08007-01.icd` | texts=0, primitives=0 | top_partあり, parts=1 | 3D単品寄り。2Dは空に近い |
| `03_20K03379P00_シュートベース.icd` | texts=31, weld_notes=5 | top_partあり, parts=9 | 2D注記と3D部品の両方に意味あり |
| `TR1D9Q00027.icd` | texts=0, primitives=0 | top_partあり, parts=34 | 3D寄り。2Dは空に近い |
| `TR1D9K99027.icd` | texts=185, primitives=153, warning=5 | top_partあり, parts=1 | 2D図枠・訂正表が強い |
| `M26A07720.icd` | texts=27, primitives=1, warning=3 | top_partあり, parts=1 | 2D注記に塗装/参考図番あり |

## 3. 取得できた実例

2D文字から、以下のような属性候補は既に拾えている。

- `U8105111315.icd`: `尺度`, `訂正`, `材`, `訂 正 理 由`
- `TR1D9K99027.icd`: `尺度`, `訂正`, `材`, `訂 正 理 由`
- `DFR-CM1-AA0305300011.icd`: `使用材料 丸棒 φ90 平角鋼材...`
- `03_20K03379P00_シュートベース.icd`: `塗装色ハ仕様書ニヨル`, `塗装色 手摺部:Y22-80X(黄)`, 部材指示
- `M26A07720.icd`: `塗装`, `参考図番: M24A88810`

3D部品ツリーから、以下のような属性候補は既に拾えている。

- top part name
- part name
- part comment
- external reference model name
- external reference model path
- mirror flag
- read-only flag
- unloaded flag

例: `XH30-A08001-R03-JP_ロードカップ部改造.icd` では `parts=575` で、外部参照パーツの `ref_model_name` / `ref_model_path` が取れている。

## 4. 現行実装の不足

### 4.1 2D/3D有無判定

未実装。

現行は `source-kind` 指定で2D/3Dを試しているだけである。`TR1D9Q00027.icd` の2D結果や `XH3001-M08007-01.icd` の2D結果のように、空に近い抽出でも成功扱いになる。

必要な対応:

- `SxModel.getGlobalVS()` / `getGlobalWF()` の成否だけではなく、件数と内容で判定する
- 2Dは `SxVS.getInf()`, `SxModel.getInfPrintList()`, `SxVS.getSegList()`, `SxEntSeg.getGeomList()` の結果を使う
- 3Dは `SxWF.getInfPartTree()`, `SxWF.getInfExTopPart()`, パーツ数、外部参照数を使う
- `empty_2d_success` のような warning を出す

### 4.2 図枠外/印刷範囲外の除外

現時点では後回し。ただし必ず要件として残す。

理由:

- 現行 `TextPayload` は文字列だけで、文字座標 `pnt` を保持していない
- 現行抽出は `SxModel.getInfPrintList()` を取っていないため、印刷範囲枠の座標がない
- 図枠外のメモ、退避文字、旧注記、作業用文字を弾くには、文字座標と印刷範囲の両方が必要

必要な対応:

1. `SxModel.getInfPrintList()` を抽出する
2. `SxInfPrint.dinfo[3]` から `[6]` の作画範囲を保持する
3. `SxGeomText` / `SxGeomLabel` の座標を保持する
4. 初期実装では削除せず、`inside_print_area=true|false|unknown` として記録する
5. 実データで精度確認後に、検索・タグ生成対象から除外する

### 4.3 ICAD起動制御

現行は不十分。

`IcadProcessStarter` は `icad`, `icadsx02`, `icadsx02_x86`, `RICAD` のプロセス名だけを見る。今回の環境では `ICADX4J.EXE` が起動していたが、この名前は現行の起動済み判定に含まれていない。

必要な対応:

- `icadx4j` を起動済み判定に追加する
- 既に起動しているICADを使う場合、抽出後に勝手に閉じない
- runner が自動起動したICADだけ自動終了対象にする
- 自動起動に失敗した場合は `ICADが立ち上がっていません` 相当の明示エラーを返す
- 既存起動中ICADを閉じる要件は危険なので、最初は `close_existing_icad=false` を既定にする
- どうしても閉じる場合は、抽出専用workerセッションで起動したプロセスだけに限定する

### 4.4 2D訂正内容

取得対象に追加する。

`U8105111315.icd` と `TR1D9K99027.icd` で `訂正`, `訂 正 理 由` が2D文字として取得できた。図面の改訂履歴、訂正理由、訂正日、訂正者は、ナレッジ検索では重要な属性になり得る。

必要な対応:

- 図枠解析の中に `revision_table` / `correction_history` を追加する
- 欄名候補: `訂正`, `訂正理由`, `変更`, `改訂`, `REV`, `DATE`, `担当`, `承認`
- まずは表全体を raw evidence として保持し、Gemini API等で低温JSON分類する
- 確信度が低い場合はタグ確定ではなく要確認候補にする

### 4.5 パーツ付加情報

2D/3Dとは別の情報源として扱うべき。

SXNET資料上、`SxWF.getInfPartTree()` はパーツ階層、パーツ詳細情報、パーツ任意情報をまとめて取得できる説明になっている。現行 `PartTreeFlattener` は `name`, `comment`, `ref_model_name`, `path`, `is_external` など一部しか展開していない。

必要な情報源分類:

- `2d_geometry`: 図枠、寸法、注記、訂正表、表面粗さ、溶接、バルーン
- `3d_structure`: WF、top part、部品階層、外部参照、ミラー、read-only
- `part_extended_info`: パーツ任意情報、部品詳細、品番、PRFX、ユニット番号、材質候補
- `material_mass`: 材質、比重、重量、質量、体積、面積
- `file_model_info`: モデル名、パス、コメント、読み取り専用など

客先や図面によって付加情報が無い場合もあるため、空をエラーにせず `not_present` として扱う。ただし、API呼び出し失敗と「データが無い」は区別する。

## 5. 追加共有サンプル 11件の確認

追加で共有された11件も、現行runnerで `source-kind=2d` / `source-kind=3d` の両方を抽出した。すべて exit code 0 でJSON出力はできた。

| ファイル | 2D抽出の主な結果 | 3D抽出の主な結果 | 現時点の見立て |
| --- | ---: | ---: | --- |
| `CAA5012-02434006P1R1.icd` | texts=0, primitives=0 | top_partあり, parts=1 | 3D単品寄り。2Dは空に近い |
| `CAA5012-02434000K1R1.icd` | texts=0, primitives=4 | top_partあり, parts=360 | 3D組立が主 |
| `PSG011-PA1100_クリーニング駆動.icd` | texts=10 | top_partあり, parts=427 | 3D組立が主。2D文字も少量あり |
| `PSG011-PA1300_ベース.icd` | texts=10 | top_partあり, parts=95 | 3D組立が主。2D文字も少量あり |
| `PSG011-PA13001.icd` | texts=33, primitives=8 | top_partあり, parts=1 | 2D図面情報と3D単品の両方 |
| `PSG011-PA13002.icd` | texts=21 | top_partあり, parts=13 | 2D図面情報と3D部品構成の両方 |
| `PSG011-PA0500_コラム.icd` | texts=10 | top_partあり, parts=262 | 3D組立が主。抽出時間も長め |
| `PSG011-P05008.icd` | texts=14 | top_partあり, parts=4 | 2D文字と3D部品の両方 |
| `PSG011-P05010.icd` | texts=15 | top_partあり, parts=19 | 2D文字と3D部品の両方 |
| `23022-007_231218.icd` | texts=4, warning=9 | top_partあり, parts=7 | 3D寄り。2Dは少量 |
| `23022-013_231218.icd` | texts=4, warning=9 | top_partあり, parts=37 | 3D寄り。2Dは少量 |

今回の追加分で、客先・図面体系がさらに分散した。したがって、特定客先の図枠名、座標、ファイル名規則、部品名規則に寄せた判定は危険である。実装方針は、まずSXNETから取得できる汎用証拠を欠落なく保存し、後段で客先別辞書やLLM分類を薄く重ねる形にする。

## 6. ICAD起動済みダイアログへの対応

現行 `IcadProcessStarter` は起動済み判定で `icad`, `icadsx02`, `icadsx02_x86`, `RICAD` だけを見ていた。しかし今回の環境では、ICAD SX 2025 の実行本体が `ICADX4J.EXE` として残っていた。

このため、既にICADが起動しているにもかかわらずrunnerが `icad.exe` を起動しようとし、`ICADSXはすでに起動されています` のダイアログが大量に出る原因になり得る。

対応:

- `IcadProcessStarter` の起動済み判定に `icadx4j` を追加した
- 既存起動中のICADはrunner終了時に閉じない
- runnerが自動起動したICADだけを終了対象にする既存方針は維持する

今後さらに必要な対応:

- 抽出前に `icad_process_detected=true` と検出プロセス名をログ/JSONへ記録する
- 自動起動失敗時は `ICADが立ち上がっていません` 相当の明示エラーを返す
- 既存ICADを閉じる操作は、ユーザー作業中のICADを巻き込むため既定では禁止する

## 7. 複数枚データと印刷枠

ICADの1ファイルには複数枚の2Dデータ、複数のビュー、複数の印刷枠が内包され得る。したがって、2D抽出では `getGlobalVS()` だけを対象にした単一シート前提では不足する。

必要な対応:

- `SxModel.getVSList()` でVS一覧を取得する
- 各VSに対して `SxVS.getInf()` を取得し、VS名、尺度、ビュー種別、コメントを保持する
- `SxModel.getInfPrintList()` で印刷枠を取得する
- `SxInfPrint.dinfo` の作画範囲を保持する
- 文字、寸法、記号、注記に座標を持たせる
- 各要素がどの印刷枠に入るかを `print_frame_id` / `inside_print_area` として記録する
- 初期段階では印刷枠外の要素を削除せず、検索・タグ生成から除外するかどうかを後段で制御する

印刷枠確認は、図枠外メモ、退避文字、旧注記、別シートの文字を誤ってタグ化しないために優先度が高い。

## 8. 追加共有サンプル 3件の確認

さらに共有されたライズ系3件を確認した。すべて exit code 0 でJSON出力はできた。

| ファイル | 2D抽出の主な結果 | 3D抽出の主な結果 | 現時点の見立て |
| --- | ---: | ---: | --- |
| `CAA5012-02430002P1R1.icd` | texts=0, primitives=0 | top_partあり, parts=1 | 3D単品寄り。2Dは実体なしに近い |
| `CAA5012-02430012P1R1.icd` | texts=0, primitives=0 | top_partあり, parts=1 | 3D単品寄り。2Dは実体なしに近い |
| `CAA5012-02435010P1R1.icd` | texts=0, primitives=0 | top_partあり, parts=1 | 3D単品寄り。2Dは実体なしに近い |

この3件は、`source-kind=2d` の抽出が成功しても実質的な2Dデータが無いケースとして有用である。`detect` 実装では、`getGlobalVS()` が成功したかどうかではなく、VS情報、印刷枠、文字、寸法、2Dジオメトリの件数から `has_2d=false` を返せるようにする。

## 9. 不足しそうなサンプル

現共有分で不足する場合は、推測で補わず、必要なサンプル種別を明示して追加共有を依頼する。

現時点で追加が必要になり得るサンプル:

- 1つのICADファイルに複数枚の2D図面、複数VS、複数印刷枠が入っているもの
- 印刷枠外に退避文字、旧注記、作業メモが残っているもの
- 図枠に重量、材質、表面処理、塗装指示が明確に入っているもの
- 訂正表/改訂履歴が複数行埋まっているもの
- 3Dパーツ付加情報にPRFX、ユニット番号、材質、客先固有属性が入っているもの
- 3D材質またはマスプロパティから重量・体積・比重が取れるもの
- バルーン、部品表、溶接記号、表面粗さ、幾何公差が多い2D図面

## 10. 次の実装優先度

1. `detect` コマンドを追加し、2D/3D有無と根拠件数を返す
2. `SxModel.getInf()` / `SxVS.getInf()` / `SxModel.getInfPrintList()` を raw extract に追加する
3. 2D文字・注記に座標を追加し、印刷範囲内外を `unknown` ではなく判定可能にする
4. `correction_history` を2D図枠解析の正式対象に入れる
5. `part_extended_info` を3D部品ツリーとは別セクションとして追加する
6. ICAD起動済み判定に `icadx4j` を追加し、自動起動失敗時のエラーを明示化する

## 11. 現時点の方針

図枠外データの除外は、今すぐ削除フィルタを入れるべきではない。まずは座標と印刷範囲を記録し、`inside_print_area` を付けて、除外判断は後段にする。

パーツ付加情報は3D抽出の付属物ではなく、タグ・属性生成に使う独立した evidence source として扱う。2D図枠、3D部品ツリー、パーツ任意情報のどれかだけを正本にせず、同一属性が複数ソースに出る場合は照合する。

## 12. 2026-07-14 追加実装後の確認

ユーザー共有済みサンプルは、最初の23件に加えて、NTC、不二越、澁谷工業系の16件を追加し、現時点で合計39件になった。

今回の実装で、`detect` コマンド、2D全VS抽出、印刷枠取得、レイヤー取得、保存パス/ファイル名取得、パーツ付加情報の展開、Django側の2D/3D/タグ候補表示を追加した。

### 12.1 最新16件の `detect` 結果

出力先:

- `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts\latest_shared_detect_2026-07-14`

| ファイル | 2D実体 | 3D実体 | VS数 | 印刷枠 | 2Dセグメント | 2Dジオメトリ | パーツ数 | 見立て |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `9NK5E56H20-00-BRACKET-A0-3D-01.icd` | あり | あり | 12 | 1 | 1564 | 1560 | 1 | 2D図面情報も強い3D単品 |
| `9NK5E51B70-00-BRACKET-A0-3D-01.icd` | あり | あり | 10 | 1 | 1999 | 1995 | 2 | 2D/3D両方を照合対象にする |
| `9NK5E51M00-00-COVER-A3-3D-01.icd` | あり | あり | 4 | 1 | 204 | 200 | 1 | 2D図面情報あり |
| `U8718-S71-149_A4.icd` | あり | あり | 4 | 0 | 85 | 85 | 4 | 2D実体はあるが印刷枠未取得 |
| `U8718-S71-002_A3.icd` | あり | あり | 3 | 0 | 49 | 49 | 5 | 2D実体はあるが印刷枠未取得 |
| `18T5-10BF(8).icd` | なし | あり | 2 | 0 | 0 | 0 | 4 | 2Dコンテナあり・実体なし |
| `G1630-S3000-502_A3a1.icd` | あり | あり | 3 | 1 | 101 | 101 | 2 | 2D/3D両方あり |
| `G1630-S3000-039_A0a1.icd` | あり | あり | 6 | 1 | 936 | 936 | 43 | 2D/3D両方あり |
| `32791729A01.icd` | なし | あり | 2 | 0 | 0 | 0 | 1 | 3D単品寄り |
| `36555211A01.icd` | なし | あり | 2 | 0 | 0 | 0 | 3 | 3D寄り |
| `6800DDU.icd` | なし | あり | 2 | 0 | 0 | 0 | 1 | 3D単品寄り |
| `4D-75.icd` | なし | あり | 2 | 0 | 0 | 0 | 1 | 3D単品寄り |
| `474300AC219.icd` | なし | あり | 3 | 0 | 0 | 0 | 1692 | 3D大規模アセンブリ |
| `6051033A.icd` | なし | あり | 2 | 0 | 0 | 0 | 1 | 3D単品寄り |
| `47323023A01.icd` | あり | あり | 6 | 1 | 102 | 102 | 1 | 2D図面情報あり |
| `47323200X40c.icd` | あり | あり | 6 | 1 | 188 | 188 | 436 | 2D/3D両方あり、部品数も多い |

ポイント:

- 16件すべてでファイル存在確認と `detect` が成功した。
- 16件すべてで `has_3d=true`。
- 9件で `has_2d=true`。
- 9件で `segment_count > 0`。`has_2d` は `segment_count > 0` または `geometry_count > 0` を実体ありとして判定する。
- 7件は `has_2d_container=true` だが、`has_2d=false`。つまり、VSコンテナは存在しても図面として使える2D実体が無いケースがある。
- 2D実体ありでも印刷枠が0件のファイルがあるため、印刷枠だけを2D有無の判定根拠にしてはいけない。

`ICADSXはすでに起動されています` ダイアログの連発対策として、ICAD/SXNETアクセス全体をプロセス間 Mutex で直列化した。起動判定だけではなく、抽出・検出が終わるまでロックを保持する。修正前は同一ファイルの `detect` を3並列で投げると2件がSXNET呼び出し例外になったが、修正後は3件すべて `exit_code=0` で完了した。

### 12.2 澁谷工業系パーツ付加情報

`TR1D9Q00027.icd` と `TR1D9K99027.icd` で、`SxWF.getInfPartTree()` 由来の `ex_inf` からパーツ付加情報を取得できることを確認した。

確認できたフィールド例:

- `User_Type`
- `User_WBHIN1` から `User_WBHIN5`
- `User_WBHNA`
- `User_WBZAI1`
- `User_WCMCD`
- `User_WCMNA`
- `User_WCTYP`

`TR1D9K99027.icd` では `User_WBZAI1="ＲＭ"`, `User_WCMNA="ＳＵＳ"` のように材質・分類に使える候補が入っていた。これは2D/3Dとは別の `part_extended_info` evidence source として保持する。

### 12.3 本番ナレッジシステム実画面確認

確認対象:

- `http://210.165.3.139/web/drawing`
- `http://210.165.3.139/web/project`
- `http://210.165.3.139/web/product`
- `http://210.165.3.139/web/part`

読み取り専用で画面表示とフロント資産を確認した。登録、変更、削除は行っていない。

2026-07-14 の追加確認では、Chromeのログイン済みタブを読み取り専用で操作し、以下にスクリーンショットを保存した。

- `output/knowledge_ui_screenshots_2026-07-14/project_list.png`
- `output/knowledge_ui_screenshots_2026-07-14/project_detail.png`
- `output/knowledge_ui_screenshots_2026-07-14/product_unit_list.png`
- `output/knowledge_ui_screenshots_2026-07-14/product_unit_detail.png`
- `output/knowledge_ui_screenshots_2026-07-14/part_list_reload.png`
- `output/knowledge_ui_screenshots_2026-07-14/part_detail.png`
- `output/knowledge_ui_screenshots_2026-07-14/drawing_list.png`
- `output/knowledge_ui_screenshots_2026-07-14/drawing_detail.png`

| 画面 | 一覧の主な列 | タグ/属性の見た目 | 所見 |
| --- | --- | --- | --- |
| 図面一覧 | 図面番号、図面名、バージョン、図面タイプ、ステータス、紐づき概要、最終更新日時 | 一覧列には見えない | `紐づき概要` に PRJ/製品/部品の関係だけ表示 |
| プロジェクト一覧 | プロジェクト名、顧客名、顧客担当者、ステータス、責任者、開始日、終了予定日、終了日 | 一覧列には見えない | 客先・案件タグを載せる候補だが、既存一覧には未表示 |
| 製品・装置・ユニット一覧 | 名称、カテゴリ、種別、フェーズ、プロジェクト数、下位/上位/部品数、ステータス、担当者、最終更新日 | 一覧列には見えない | 装置カテゴリ、ユニット、工程タグの適用候補 |
| 部品一覧 | 部品番号、部品名、カテゴリ、ステータス、担当者、最終更新日 | 一覧列には見えない | 材質、メーカー、パーツ付加情報タグの適用候補 |

静的フロント資産では以下を確認した。

- `drawing_attributes` API 参照あり
- `product_attributes` API 参照あり
- `part_attributes` API 参照あり
- `project_attributes` API 参照は見当たらない
- 図面詳細系のレスポンスには `tags` / `attributes` を表示する受け口がある

実画面の詳細表示では以下を確認した。

| 画面 | 実画面でのタグ/属性の見え方 | 所見 |
| --- | --- | --- |
| 図面詳細 | 基本情報内に `タグ` と `属性情報` が表示される。右側に2Dプレビュー、表示切替として `2D` / `3D` がある | ICAD抽出タグ・属性の最初の反映先として最も自然 |
| プロジェクト詳細 | 基本情報と関連タブはあるが、タグ/属性の表示口は見えない | プロジェクトタグを使うなら創屋へ新規表示/API追加を確認する |
| 製品・装置・ユニット詳細 | `属性情報` は表示されるが、タグ欄は見えない | 装置種別、ユニット番号、工程などは既存属性口に載せられる可能性がある |
| 部品詳細 | `属性情報` は表示されるが、タグ欄は見えない | 材質、メーカー、パーツ付加情報、参照ICADパスの反映候補 |

図面詳細の3D表示へ切り替えた際、`/web/public/models/test_000445.gltf` の読み込みで `Unexpected token '<'` のエラー画面が出た。登録、更新、削除は行っていない。これはタグ抽出とは別件だが、2D/3Dプレビュー連携 fixture を作る際に創屋へ共有すべき表示側の確認事項として残す。

したがって、創屋へ渡すときの優先順位は次の順が現実的。

1. 図面詳細にタグ・属性候補を表示する
2. 製品・装置・ユニット、部品の属性 API に対応する形でタグ候補を渡す
3. プロジェクトは既存受け口が未確認なので、詳細内補助タブまたは新規 API/列追加の相談事項にする

### 12.4 既存2D/3Dビューワーとの合わせ込み

`C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を確認し、以下の考え方を本実装側にも寄せた。

- 本体へ直接埋め込む前提ではなく、移植しやすい独立画面として作る。
- Django View は薄くし、表示用の整形は service に寄せる。
- 既存ナレッジ画面の補助パネルとして、属性、関連情報、履歴、備考のように読める構成にする。
- 初心者向けコメントは、SXNET依存の難しい箇所と本番連携境界にだけ簡潔に入れる。

### 12.5 3Dマスプロパティ実装と実測

`SxWF.getExtent()` でモデル全体を囲む `SxBox` を取得し、`SxWF.getEntList(SxBox, false)` で3D要素を集め、`SxEnt.getMass(SxOptMass, SxEnt[])` を呼ぶ流れを抽出器へ追加した。

取得結果は `raw_extract.mass_probe_status` と `raw_extract.mass_properties` に保持し、Django側の正規化と3D詳細表示にも出す。

実サンプル結果:

| ファイル | parts | mass_probe_status | element_count | unit | mass | weight | volume | area |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| `6800DDU.icd` | 1 | `available` | 17 | `mm-kg` | 0.00055092 | 0.00540269 | 701.64779731 | 1858.76904715 |
| `474300AC219.icd` | 1692 | `available` | 2767 | `mm-kg` | 17.7113085 | 173.68860346 | 92838201.3023013 | 27095829.3503268 |
| `TR1D9Q00027.icd` | 34 | `available` | 39 | `mm-kg` | 0.02220905 | 0.2177964 | 129916.95147963 | 取得値あり |

`TR1D9Q00027.icd` は `parts_with_ex_info=20` で、`User_WBZAI1` などのパーツ付加情報も同時に取得できた。したがって、3D重量系は「取得可能性あり」から「実装済み、ただし対象要素なし/ICAD側例外は status と warning で記録」に更新する。

### 12.6 次に残る実装

- 2Dジオメトリの詳細意味付け。`SxGeomSpline2D` などは primitive として取り込み済みだが、長穴、穴数、外形特徴、断面/切断線などの設計特徴タグへの変換は未実装
- 2D図枠欄名辞書は初期実装済み。今後は実サンプルでの辞書拡充と、Gemini API低温度JSON分類を曖昧欄名の補助に限定して追加する
- 3D材質 API である `SxEnt.getInfMaterialList()` / `SxEntPart.getInfMaterialList()` の実サンプル実装確認
- 本番ナレッジシステム向けの創屋引き継ぎ仕様として、図面/プロジェクト/製品・装置・ユニット/部品別の連携項目表を作る

### 12.7 2D図枠欄名候補の初期実装

Django正規化層で、2D文字から図枠欄候補を作る初期辞書を追加した。対象は図番、図面名、材質、重量、表面処理、塗装指示、尺度、設計者、検図者、承認者、日付、改訂、PRFX、ユニット番号。

実装方針:

- CADに存在する文字だけを候補化し、生成AIで値を推測しない
- `inside_print_area=false` の文字は候補から外す
- ラベルだけの文字は低信頼候補として保持し、採用値にしない
- 材質、PRFX、ユニット番号など短い属性は値の長さ上限を厳しめにし、長文注記を採用値にしない
- `title_block_candidates` に根拠文字、座標、レイヤー、印刷枠判定、信頼度を保持する
- 値が同一文字内または次行にあり、長さ・ラベル判定を通ったものだけ `title_block_fields` に上げる

実抽出JSONでの確認:

| ファイル | 候補数 | 採用フィールド | 所見 |
| --- | ---: | --- | --- |
| `TR1D9K99027_allviews_2d.json` | 10 | `designer` | 図枠ラベル中心。ラベルのみは低信頼候補として保持 |
| `CAA5012-02430002P1R1_allviews_2d.json` | 0 | なし | 図枠欄候補に該当する2D文字なし |
| `DFR-CM1-AA0305300011_2d.json` | 2 | `material` | 材質候補を取得。長文注記は低信頼候補に落とし、採用値から除外 |

### 12.8 2D形状・記号特徴候補の初期実装

2D primitive から、レビューに使える特徴証拠候補を集計する初期ルールを追加した。これは確定判定ではなく、CAD内に存在する primitive を根拠にした候補である。表面粗さ、データム、穴候補などの存在だけでは検索・分類タグとして粗いため、`searchable_tag=false` と `tag_adoption_status=excluded` を付けて自動タグから除外する。

初期対象:

- `SxGeomHatch`: `classification_label=ハッチング/断面候補`
- `SxGeomSmark`: `classification_label=表面粗さ記号あり`
- `SxGeomCutLine`: `classification_label=切断線あり`
- `SxGeomTolDatum`: `classification_label=データム記号あり`
- `SxGeomTol`: `classification_label=幾何公差記号あり`
- `SxGeomFinishMark`: `classification_label=仕上げ記号あり`
- `SxGeomElparc2D`: `classification_label=長穴/楕円弧候補`
- `SxGeomCircle2D`: `classification_label=穴/円候補`

`inside_print_area=false` の primitive は候補から外す。長穴や穴は形状確定ではなく低信頼の候補として保持する。

実抽出JSONでの確認:

| ファイル | 特徴候補 | 所見 |
| --- | --- | --- |
| `TR1D9K99027_allviews_2d.json` | `穴/円候補` 2件 | 円 primitive 由来の低信頼証拠候補。自動タグには採用しない |
| `CAA5012-02430002P1R1_primitives_2d.json` | `ハッチング/断面候補` 8件、`表面粗さ記号あり` 2件、`長穴/楕円弧候補` 17件 | 証拠候補として保持。自動タグには採用しない |
| `DFR-CM1-AA0305300011_2d.json` | なし | 対象 primitive なし |

### 12.9 Gemini 低温度JSON分類の入口

`title_block_candidates` を対象に、Gemini API で欄名分類だけを補助するサービスを追加した。実装上の制約は以下。

- `GEMINI_API_KEY` 未設定時は明示エラーにする
- 温度は設定値 `GEMINI_TEMPERATURE` を使用し、既定は `0.0`
- `responseMimeType=application/json` を指定する
- APIには候補の index、既存値、根拠文字、座標系メタだけを渡す
- Geminiは値を生成しない。返せるのは候補 index と許可済み field 名だけ
- 許可されていない field、範囲外 index、不正 confidence は破棄する
- U+FFFD を含む文字化け候補はGeminiへ送らず、抽出証跡として候補側には残す
- 文字化け候補を除外しても、Geminiの返却 index は元の `title_block_candidates` の index へ戻してから適用する

実API呼び出しは2D抽出ジョブへ組み込み済みで、APIキー未設定時はスキップし、API失敗時は `title_block_llm_classification_failed` warning として保持する。2026-07-15 に `backend\.env` よりOS環境変数の古い `GEMINI_API_KEY` が優先されていた問題を確認し、`load_dotenv(..., override=True)` へ変更した。さらに `gemini-2.5-flash` が新規ユーザー向けに利用不可だったため、`gemini-flash-latest` を主モデル、`gemini-3.1-flash-lite` / `gemini-3.5-flash` をフォールバックにした。

修正後、代表manifestの2D抽出20 JSONで図枠候補あり6ファイル/6サンプルを確認し、上位5サンプルへ実API分類を実行した。2026-07-17に現行正規化で再プローブし、5件すべてで `gemini` 応答を取得した。Geminiへ送る正例3件は classification precision 1.0000、positive recall 1.0000、誤分類0、誤採用0だった。採用件数は0件で、既存ルールで採用済みの値を上書きせず、CADに無い値を生成していないことを確認できた。結果は `output/live_extracts/title_block_llm_probe_2026-07-14/gemini_probe_current_normalization_2026-07-17.json` に保存した。

文字化け候補の事前除外を追加後、Geminiを呼ばずに共有抽出JSONを再集計した。共有抽出JSON 69件中、図枠候補ありは11ファイル/5サンプルで、上位5サンプルの `skipped_replacement_character_count` は0件だった。再集計結果は `output/live_extracts/title_block_llm_probe_2026-07-14/filtered_reprobe_2026-07-14.json` に保存した。

### 12.10 3D材質APIの初期実装

`SxWF.getExtent()` と `SxWF.getEntList(SxBox, false)` で3D要素を集め、`SxEnt.getInfMaterialList(SxEnt[])` から `SxInfMaterial` を取得する probe を追加した。戻り値は要素ごとの配列がネストするため、再帰的に平坦化してから `matid`, `name`, `spe_grav` で重複集約する。

実サンプル結果:

| ファイル | material_probe_status | material_count | 材質ID | 比重 | element_count | 所見 |
| --- | --- | ---: | --- | ---: | ---: | --- |
| `6800DDU.icd` | `available` | 1 | `SUS440C` | 7.7 | 17 | warningなし。日本語材質名は文字化けがあるため材質IDを主キー寄りに扱う |

Django側では `material_probe_status`, `material_ids`, `material_names`, `material_specific_gravities`, `material_keywords` に正規化し、`材質:<値>` タグ候補も生成する。

### 12.11 3D部品単位材質APIの実装

SXNETオリジナルHTML `C:\Users\s-iwata\Desktop\icad_api_sxnet` を確認し、`SxInfPartTree.entpart` が `SxEntPart` 型であること、`SxEntPart.getInfMaterialList()` が `SxInfMaterial[]` を返すことを確認した。資料上、このメソッドは部品内の要素に付加された材質を返し、子パーツ内の要素は対象外である。

このため、C#抽出器では部品ツリーを走査する各ノードで `entpart.getInfMaterialList()` を呼び、結果を `parts[].materials` に保持する。部品別材質はDjango正規化で `part_material_candidates` の `source=3d_part_material`, `confidence=high` として扱う。従来の単一パーツ/単一全体材質の推定、およびパーツ付加情報内の材質表記は補助候補として残す。

部品材質APIが個別部品で失敗した場合は、抽出全体を止めず `warnings[].code=part_material_probe_failed` に部品パス付きで記録する。これは実サンプル調査を止めないためであり、失敗部品を後から確認できるようにする。

実装確認:

| 確認 | 結果 |
| --- | --- |
| C# `PartTreeFlattenerTests` | フェイク `entpart.getInfMaterialList()` から `parts[].materials` を生成し、同一材質を `element_count` で集約 |
| Python `test_normalization.py` | `parts[].materials` を高信頼の `part_material_candidates` として正規化 |
| 実サンプル横断確認 | 共有済みICAD 39件で3D抽出を実行。39件成功、全体材質33件、部品別材質13件、`part_material_probe_failed` は0件 |

横断集計:

- 実行スクリプト: `scripts/run_shared_part_material_probe_2026_07_14.ps1`
- 集計JSON: `output/live_extracts/part_material_probe_2026-07-14/_summary.json`
- 対象: これまで共有されたICAD 39件
- 3D抽出成功: 39/39
- 全体材質あり: 33/39
- 部品別材質あり: 13/39
- 部品材質API warning: 0件
- 部品別材質IDのユニーク値: `PPS`, `75`, `PVC`, `SUS316`, `PTFE`, `A5052P`, `SUS304`, `SS400`, `ZZZ`, `CDQ`, `13クロム系ステンレス`, `一般構造用鋼`, `S45C`, `SPCC`, `FC300`, `S45C相当`, `PET`, `NBR`, `PP`, `AU`, `EPDM`, `H-PVC`, `SI`, `FKM`

### 12.12 材質ID辞書の分類強化

共有39件の3D抽出JSONに対して、材質値を `formal` / `unresolved` / `excluded` に分類する辞書を追加した。

方針:

- `formal`: 通常の `材質:<値>` タグに使う
- `unresolved`: 捨てずに `材質要確認:<値>` の低信頼タグにする
- `excluded`: `RM`, `ZZ購入品`, `LMレール`, `LMブロック`, 重量文字列など、材質タグへ出すとノイズになる値
- 材質名に ICAD 側の番号が付くケースは、先頭番号を外して辞書照合する
- 日本語材質名は正式な同義語として辞書化するが、文字化け済み文字列や重量文字列は除外する

実測結果:

- 対象: `output/live_extracts/part_material_probe_2026-07-14` の3D抽出JSON 39件
- 通常材質側へ分類できた主な値:
  - `SS400`, `SUS304`, `SUS316`, `SUS`, `SUS440C`, `SPCC`, `S45C`, `FC300`, `FC250`, `A5052P`
  - `PPS`, `PVC`, `H-PVC`, `PTFE`, `PET`, `PETG`, `POM`, `NBR`, `EPDM`, `FKM`, `PP`, `AU`, `SI`
  - `13クロム系ステンレス`, `合金工具鋼`, `炭素鋼`, `ねずみ鋳鉄`
- 要確認側に残った値:
  - `ZZZ`: 4件
  - `CDQ`: 1件
  - `75`: 1件

これにより、共有39件では材質名や樹脂・ゴム名が通常タグへ寄り、意味未確定の客先固有コードだけをレビュー対象として残せる状態になった。

### 12.13 2D図枠候補のノイズ抑止

共有抽出JSON 69件を `scripts/probe_title_block_llm.py` で再確認し、2D図枠候補ありは11ファイル/5サンプルだった。

今回、実サンプルで見えた以下の誤採用を抑止した。

- `製図者` から末尾の `者` だけを `designer` 値として採用しない
- `１．使用材料` のような注記見出しから `１．使用` を `material` 値として採用しない
- `塗装色...` は `塗装` より `塗装色` を優先して欄名を切り出す
- 低信頼候補は根拠文字として残すが、使えない値は `value=null` にして採用候補へ上げない

再プローブ結果:

- `TR1D9K99027_2d.json`: `selected_fields={}`。図枠ラベルは候補として残るが、ラベル片は採用されない
- `U8105111315_2d.json`: `selected_fields={}`。同上
- `DFR-CM1-AA0305300011_2d.json`: `material` は見出しではなく次行の材料説明へ寄る
- `03_20K03379P00_shoot_base_2d.json`: `coating_instruction` は `塗装色` 優先で抽出
- `M26A07720_2d.json`: `参考図番` 由来の図番候補は維持

これにより、Gemini APIが使えない状態でも、図枠候補の初期辞書だけで低品質な自動採用を減らせる。

代表結果:

| ファイル | parts | 全体材質数 | 材質付き部品数 | 部品材質候補数 | 部品材質ID |
| --- | ---: | ---: | ---: | ---: | --- |
| `474300AC219.icd` | 1692 | 21 | 1577 | 1597 | `SUS304`, `PET`, `ZZZ`, `NBR`, `PP`, `AU`, `SUS316`, `EPDM`, `H-PVC` |
| `XH30-A08001-R03-JP_ロードカップ部改造.icd` | 575 | 8 | 414 | 414 | `PPS`, `75`, `PVC`, `SUS316`, `PTFE`, `A5052P`, `SUS304` |
| `47323200X40c.icd` | 436 | 6 | 411 | 411 | `SUS304`, `SI`, `PTFE`, `FKM`, `ZZZ`, `SUS316` |
| `CAA5012-02434000K1R1.icd` | 360 | 9 | 40 | 41 | `SS400`, `A5052P`, `SUS304`, `CDQ`, `13クロム系ステンレス`, `一般構造用鋼` |
| `23022-013_231218.icd` | 37 | 1 | 36 | 36 | `SS400` |
| `PSG011-PA1100_クリーニング駆動.icd` | 427 | 5 | 28 | 28 | `SS400`, `SUS304`, `S45C`, `SPCC` |

所見:

- `SxEntPart.getInfMaterialList()` は、客先差のある実データでも例外なく呼べた。API自体は採用してよい。
- ただし部品別材質が取れるかはデータ次第で、39件中13件だった。全体材質があるのに部品別材質が0件のファイルもある。
- よってタグ/属性生成では、部品別材質を最優先の高信頼 evidence とし、全体材質は図面/モデル全体タグ、パーツ付加情報は補助 evidence として扱う。
- `ZZZ` や `75` のように材質辞書上の意味が不明または客先固有の値がある。実装では `ZZZ`, `75`, `CDQ` を `unresolved_material_keywords` に分離し、通常の `材質:<値>` ではなく `材質要確認:<値>` の低信頼タグとして保持する。

## 13. 2D座標と印刷枠内外判定

2026-07-14 の追加実装で、2D文字、寸法、溶接、バルーン、幾何公差系 payload に以下を追加した。

- `position_x`
- `position_y`
- `position_z`
- `inside_print_area`
- `print_frame_no`

座標取得は、文字では `SxGeomText.pnt`、寸法では `SxGeomLengthDim` などの `pnt1` を代表点として使う。印刷枠が取得でき、かつ座標がある場合は、`SxInfPrint.dinfo[3]` から `[6]` の作画範囲に入るかを判定する。印刷枠または座標が無い場合は `null` とし、削除や除外は行わない。複数枚/複数印刷枠を後段で扱えるよう、内側判定が成立した要素には所属する `print_frame_no` も保持する。

`TR1D9K99027.icd` の2D再抽出では以下を確認した。

- texts=190
- text_pos=190
- inside=true: 185
- inside=false: 5
- inside=null: 0
- print_frame_noあり文字: 185
- dimensions=21
- print_frames=1

これにより、図枠外の退避文字や作業メモを即削除せず、後段の検索・タグ生成で除外候補として扱うための最低限の足場ができた。2026-07-15 の再確認では、`TR1D9K99027.icd` で印刷枠1、文字190、寸法21、primitive862を取得し、文字185件が `print_frame_no=1`、5件が印刷枠外として記録された。

## 14. 未対応2Dジオメトリの primitive 化

2026-07-14 の追加実装で、以下の2Dジオメトリを `unsupported_geometry` ではなく `geometry_primitives` として保持するようにした。

- `SxGeomSpline2D`
- `SxGeomEllipse2D`
- `SxGeomElparc2D`
- `SxGeomHatch`
- `SxGeomSmark`
- `SxGeomCutLine`
- `SxGeomDelta`
- `SxGeomTolDatum`

primitive には、取得可能な範囲で開始座標、終点座標、中心座標、半径、角度、点数、印刷枠内外を入れる。これにより、中央図面の形状情報を後段で特徴量化する足場ができた。

実サンプル再抽出結果:

| ファイル | primitives | primitive座標あり | warning | unsupported | 主なprimitive型 |
| --- | ---: | ---: | ---: | ---: | --- |
| `TR1D9K99027.icd` | 862 | 232 | 1 | 0 | `SxGeomLine2D`, `SxGeomArc2D`, `SxGeomSpline2D`, `SxGeomDelta`, `SxGeomCircle2D` |
| `CAA5012-02430002P1R1.icd` | 244 | 86 | 0 | 0 | `SxGeomLine2D`, `SxGeomElparc2D`, `SxGeomHatch`, `SxGeomSmark`, `SxGeomCutLine`, `SxGeomSpline2D`, `SxGeomTolDatum` |

`TR1D9K99027.icd` の残 warning は、`!!GLOBAL` ビューでジオメトリ数とレイヤー数が一致しなかった件だけである。これはレイヤー番号の付与精度の問題であり、ジオメトリ型未対応ではない。

2026-07-15 の代表manifest 19件再抽出では、`SxGeomLine2D` が `x1/y1/x2/y2` ではなく `pnt1/pnt2` 系で座標を持つケースが多いことを確認した。抽出器を修正し、線分の開始点・終点を `pnt1/pnt2`、`pos1/pos2`、`sp/ep`、`start/end` からも拾うようにした。

修正前は印刷枠判定不明の大半が `SxGeomLine2D` だったが、再抽出後の不明は `unknownPrintArea=488` まで低下した。内訳は `output\souya_handoff\icad_2d_print_area_unknown_analysis_2026-07-15.json` に保存した。

- 代表2D 19件の判定対象: 23,300件
- ビュー/用紙数: 121
- 印刷枠数: 22
- レイヤー数: 4,845
- 印刷枠内: 3,212件
- 印刷枠外: 19,600件
- 印刷枠判定不明: 488件
- 判定不明の主因: `SxGeomHatch` と座標なし文字
- 座標ありだが印刷枠判定に失敗した要素: 0件

`SxGeomHatch` は SXNET の公開フィールド上、直接座標または外接矩形を確認できなかったため、ハッチング座標は推測生成しない方針にした。raw extract には `geometry_primitives` として残し、印刷枠がある図面では `inside_print_area=true` の要素だけを自動タグ・検索候補へ使う。

2026-07-15 に Django 正規化層へ、印刷枠あり図面の `inside_print_area=null` を自動タグ入力から外す制御を追加した。`text_tokens` や raw primitive は証跡として保持しつつ、`part_keywords`、`spec_tokens`、図枠候補、訂正内容候補、形状特徴候補から除外する。旧fixtureとの比較では、自動タグ9件、`part_keywords` 1,031件、`spec_tokens` 1,014件、ハッチング/断面カウント169件が減少した。比較結果は `output\souya_handoff\drawing_metadata_fixture_tag_diff_unknown_filter_2026-07-15.json` に保存した。

2026-07-15 に `probe-2d-print` を追加し、印刷実行なしで `SxModel.getInfPrintList()` と `SxInfPlot.getInfPlotList()` / `getInfDefPlot()` を読む確認を行った。

| ファイル | 出図範囲枠 | 用紙 | 範囲 | プロッタ | デフォルト |
| --- | ---: | --- | --- | ---: | --- |
| `TR1D9K99027.icd` | 1 | A2横 | `0,0` - `594,420` | 3 | `CubePDF` |
| `DFR-CM1-AA0305300011.icd` | 1 | A3横 | `-410,-10` - `10,287` | 3 | `CubePDF` |
| `217008-41J-3004.icd` | 1 | A3横 | `0,-0.00001943` - `420,297` | 3 | `CubePDF` |

これで、図枠外データをいきなり削除せず `inside_print_area` で記録し、検索・タグ候補側で制御する方針の根拠が増えた。一方で、PDF/JPEG/TIFFなど既存2Dビューワーへ渡せる実表示資産の生成は未確定で、`SxModel.print` または `SxFileModel.print` と CubePDF/プロッタ設定の実出力確認が次段階で必要。
