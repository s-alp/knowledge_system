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

| ファイル | 2D実体 | 3D実体 | VS数 | 印刷枠 | 2Dジオメトリ | パーツ数 | 見立て |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `9NK5E56H20-00-BRACKET-A0-3D-01.icd` | あり | あり | 12 | 1 | 1560 | 1 | 2D図面情報も強い3D単品 |
| `9NK5E51B70-00-BRACKET-A0-3D-01.icd` | あり | あり | 10 | 1 | 1995 | 2 | 2D/3D両方を照合対象にする |
| `9NK5E51M00-00-COVER-A3-3D-01.icd` | あり | あり | 4 | 1 | 200 | 1 | 2D図面情報あり |
| `U8718-S71-149_A4.icd` | あり | あり | 4 | 0 | 85 | 4 | 2D実体はあるが印刷枠未取得 |
| `U8718-S71-002_A3.icd` | あり | あり | 3 | 0 | 49 | 5 | 2D実体はあるが印刷枠未取得 |
| `18T5-10BF(8).icd` | なし | あり | 2 | 0 | 0 | 4 | 2Dコンテナあり・実体なし |
| `G1630-S3000-502_A3a1.icd` | あり | あり | 3 | 1 | 101 | 2 | 2D/3D両方あり |
| `G1630-S3000-039_A0a1.icd` | あり | あり | 6 | 1 | 936 | 43 | 2D/3D両方あり |
| `32791729A01.icd` | なし | あり | 2 | 0 | 0 | 1 | 3D単品寄り |
| `36555211A01.icd` | なし | あり | 2 | 0 | 0 | 3 | 3D寄り |
| `6800DDU.icd` | なし | あり | 2 | 0 | 0 | 1 | 3D単品寄り |
| `4D-75.icd` | なし | あり | 2 | 0 | 0 | 1 | 3D単品寄り |
| `474300AC219.icd` | なし | あり | 3 | 0 | 0 | 1692 | 3D大規模アセンブリ |
| `6051033A.icd` | なし | あり | 2 | 0 | 0 | 1 | 3D単品寄り |
| `47323023A01.icd` | あり | あり | 6 | 1 | 102 | 1 | 2D図面情報あり |
| `47323200X40c.icd` | あり | あり | 6 | 1 | 188 | 436 | 2D/3D両方あり、部品数も多い |

ポイント:

- 16件すべてでファイル存在確認と `detect` が成功した。
- 16件すべてで `has_3d=true`。
- 9件で `has_2d=true`。
- 7件は `has_2d_container=true` だが、`has_2d=false`。つまり、VSコンテナは存在しても図面として使える2D実体が無いケースがある。
- 2D実体ありでも印刷枠が0件のファイルがあるため、印刷枠だけを2D有無の判定根拠にしてはいけない。

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

### 12.5 次に残る実装

- 2Dジオメトリの詳細意味付け。`SxGeomSpline2D` などは primitive として取り込み済みだが、長穴、穴数、外形特徴、断面/切断線などの設計特徴タグへの変換は未実装
- `SxEnt.getMass()` / `getMassList()` による重量、体積、質量、面積の取得確認
- 2D図枠欄名の辞書化と、Gemini API低温度JSON分類の導入
- 本番ナレッジシステム向けの創屋引き継ぎ仕様として、図面/製品/部品/プロジェクト別の連携項目表を作る

## 13. 2D座標と印刷枠内外判定

2026-07-14 の追加実装で、2D文字、寸法、溶接、バルーン、幾何公差系 payload に以下を追加した。

- `position_x`
- `position_y`
- `position_z`
- `inside_print_area`

座標取得は、文字では `SxGeomText.pnt`、寸法では `SxGeomLengthDim` などの `pnt1` を代表点として使う。印刷枠が取得でき、かつ座標がある場合は、`SxInfPrint.dinfo[3]` から `[6]` の作画範囲に入るかを判定する。印刷枠または座標が無い場合は `null` とし、削除や除外は行わない。

`TR1D9K99027.icd` の2D再抽出では以下を確認した。

- texts=190
- text_pos=190
- inside=true: 185
- inside=false: 5
- inside=null: 0
- dimensions=21
- print_frames=1

これにより、図枠外の退避文字や作業メモを即削除せず、後段の検索・タグ生成で除外候補として扱うための最低限の足場ができた。

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
