# ICAD 2D/3D 情報取得可能性 調査マトリクス

- 作成日: 2026-07-14
- 確認時刻: 2026-07-14 17:05:54 +09:00
- 調査対象:
  - `C:\Users\s-iwata\Desktop\icad_api_sxnet` 直下の SXNET HTML 3,175件
  - `C:\Users\s-iwata\Desktop\knowledge_system\src\IcadExtraction.*`
  - `C:\Users\s-iwata\Desktop\knowledge_system\output\live_extracts`
- 目的:
  - ICAD 3D/2D から何をどこまで取得できるかを、SXNET根拠、現行PoC実装状況、実サンプル確認状況に分けて整理する。

## 1. 結論

現時点では、3D/2D から取得可能な情報を完全把握できたとは言えない。

ただし、SXNET一次資料から見た取得可能性はかなり整理できた。特に以下は根拠が明確。

- 3D:
  - 図面名、モデル情報
  - 3DグローバルWF
  - パーツ階層
  - パーツ名、コメント、外部参照、未解決参照、ミラー、参照図面名
  - 材質情報
  - マスプロパティ、重量、質量、体積、面積、重心、慣性モーメント
- 2D:
  - 2DグローバルVS
  - VS名、尺度、ビュー種別
  - 出図範囲枠、用紙サイズ、用紙方向、作画スケール、作画範囲
  - 文字、注記、寸法、バルーン、溶接、幾何公差、表面粗さ、仕上げ記号、シンボル、切断線、矢視
  - 図枠内の図面名、担当者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号は、SXNETの固定フィールドではなく、文字/注記/表/図枠解析で抽出する対象

未確定なのは、各社図枠・実サンプルでの安定抽出率である。

## 2. 判定凡例

| 判定 | 意味 |
| --- | --- |
| A | SXNETに型付きAPI/フィールドがあり、取得方針が明確 |
| B | SXNETで文字・注記・任意情報として取得可能だが、意味付け・座標解析・辞書が必要 |
| C | SXNETに関連APIはあるが、実サンプルでの取得方法または対象範囲の検証が必要 |
| D | 現時点のSXNET HTML検索では専用API/固定フィールドを確認できない |

## 3. 3D 取得可能性

| 項目 | 判定 | SXNET根拠 | 現行PoC | 補足 |
| --- | --- | --- | --- | --- |
| 図面名 / モデル名 | A | `SxModel.getInf()` -> `SxInfModel.name` | 未実装 | `SxInfModel` は `name`, `comment`, `is_read_only`, `nvs`, `nwf`, `path` を持つ |
| 格納フォルダ | A | `SxInfModel.path` | 未実装 | ファイルパスとの照合に使える |
| モデルコメント | A | `SxInfModel.comment` | 未実装 | 図面メタ候補 |
| 3DグローバルWF | A | `SxModel.getGlobalWF()` | 実装済み | `"3DGLOBAL"` WFを取得 |
| パーツ階層 | A | `SxWF.getInfPartTree()` | 実装済み | 実サンプルで `parts=149` の抽出実績あり |
| トップパーツ任意情報 | A | `SxWF.getInfExTopPart()`, `SxInfPartTree.ex_inf` | 実装済み | PRFX/ユニット番号等が入る可能性はあるが、実データ確認が必要 |
| パーツ名 | A | `SxInfPart.name` | 実装済み | 部品タグ、ユニット候補 |
| パーツコメント | A | `SxInfPart.comment` | 実装済み | 設計意図、注記候補 |
| 外部パーツ | A | `SxInfPart.is_external` | 実装済み | 標準部品/外部参照判断 |
| ミラーパーツ | A | `SxInfPart.is_mirror` | 実装済み | 左右勝手・流用注意 |
| 読取専用 | A | `SxInfPart.is_read_only` | 実装済み | 外部部品のアクセス制約 |
| 未解決外部参照 | A | `SxInfPart.is_unloaded` | 実装済み | 抽出信頼度に影響 |
| 参照図面名 | A | `SxInfPart.ref_model_name` | 実装済み | 外部パーツ、外部パーツ配下内部パーツで有効 |
| 参照図面格納フォルダ | A | `SxInfPart.path` | 実装済み | 参照解決、ファイル追跡 |
| 材質 | A | `SxEnt.getInfMaterialList()`, `SxEntPart.getInfMaterialList()`, `SxEntSeg.getInfMaterial()` -> `SxInfMaterial` | 未実装 | `matid`, `name`, `spe_grav` を取得可能 |
| 重量 | A/C | `SxEnt.getMass()`, `SxEnt.getMassList()` -> `SxInfMass.weight` | 未実装 | 対象要素が表示されている必要あり。ワイヤ対象外、シート/ソリッド混在で例外 |
| 質量 | A/C | `SxInfMass.mass` | 未実装 | 測定対象がシートの場合は無効 |
| 体積 | A/C | `SxInfMass.volume` | 未実装 | シートの場合 `0.0` |
| 面積 | A/C | `SxInfMass.area` | 未実装 | マスプロパティの一部 |
| 比重 | A | `SxInfMaterial.spe_grav`, `SxInfMass.density`, `SxOptMass.density` | 未実装 | 要素に材質設定がある場合、`SxOptMass.density` は無視される |
| 重心 | A/C | `SxInfMass.pos` | 未実装 | マスプロパティ計算結果 |
| 慣性モーメント | A/C | `SxInfMass.inf_global_moment`, `inf_gravity_moment`, `inf_main_moment` | 未実装 | 検索タグより設計解析属性向け |
| 図面サイズ | C | `SxInfPrint` または 2D出図範囲との照合 | 未実装 | 3D単独の固定属性としては未確認。モデル内の2D情報から取れる可能性が高い |
| PRFX | B/D | 任意情報、パーツ名、参照図面名に含まれる可能性 | 未実装 | SXNET固定フィールドとしてはヒットなし |
| ユニット番号 | B/D | 任意情報、パーツ名、階層名に含まれる可能性 | 未実装 | SXNET固定フィールドとしてはヒットなし |

## 4. 2D 取得可能性

| 項目 | 判定 | SXNET根拠 | 現行PoC | 補足 |
| --- | --- | --- | --- | --- |
| 2DグローバルVS | A | `SxModel.getGlobalVS()` | 実装済み | `"!!GLOBAL"` VSを取得 |
| VS名 | A | `SxVS.getInf()` -> `SxInfVS.name` | 未実装 | シート/ビュー識別 |
| VS尺度 | A | `SxInfVS.scale`, `SxInfSys.scale` | 未実装 | 図枠文字の尺度とも照合する |
| VS種別 | A | `SxInfVS.type`, `view_type` | 未実装 | グローバルビュー、基本ビュー、ローカルビュー、子図 |
| VSコメント | A | `SxInfVS.comment` | 未実装 | 子図で有効 |
| 出図範囲枠 | A | `SxModel.getInfPrintList()` -> `SxInfPrint` | 未実装 | 図面サイズ・用紙・作画範囲の強い候補 |
| 用紙サイズ | A | `SxInfPrint.size`, `SxInfPrint.dinfo[0]`, `[1]` | 未実装 | `"A0"～"A6"`, `"B1"～"B7"`, `"XY"` |
| 用紙方向 | A | `SxInfPrint.vertical` | 未実装 | 縦/横 |
| 作画スケール | A | `SxInfPrint.dinfo[2]` | 未実装 | `-1.0` は自動 |
| 作画範囲 | A | `SxInfPrint.dinfo[3]`～`[6]` | 未実装 | 2Dグローバルビュー座標 |
| 2Dセグメント | A | `SxVS.getSegList()` | 実装済み | 可視/実像部品/レイヤ/タイプ条件あり |
| 2Dジオメトリ一括取得 | A | `SxEntSeg.getGeomList()` | 実装済み | 型付きジオメトリへ変換 |
| 文字 | A | `SxGeomText.txt`, `text_line_num`, `pnt`, `atr_word` | 実装済み | 図枠・注記・表内文字の材料 |
| 注記 | A | `SxGeomLabel.txt`, `lead_line`, `underline` | 実装済み | 材質、表面処理、塗装、規格、担当者等の抽出元 |
| 線 / 円 / 円弧 | A | `SxGeomLine2D`, `SxGeomCircle2D`, `SxGeomArc2D` | 実装済み | 図枠・中央図面・表罫線の解析元 |
| スプライン | A | `SxGeomSpline2D` | 未対応 warning | 実サンプル2Dで warning 多数。中央図面解析には追加対応必須 |
| 楕円 / 楕円弧 | A | `SxGeomEllipse2D`, `SxGeomElparc2D` | 未実装 | 中央図面特徴 |
| ハッチング | A | `SxGeomHatch` | 未実装 | 断面、材質表現、加工領域 |
| 長さ寸法 | A | `SxGeomLengthDim`, `SxDimValueAtr`, `SxDimLineAtr` | 実装入口あり | 現行マッピングはフィールド名要再確認 |
| 角度寸法 | A | `SxGeomAngDim` | 実装入口あり | 同上 |
| 径寸法 | A | `SxGeomDiaDim` | 実装入口あり | φ/R等のタグ候補 |
| 面取り寸法 | A | `SxGeomChamDim` | 実装入口あり | 加工タグ候補 |
| 長円/角穴/座標寸法 | A | `SxGeomAplDim` | 実装入口あり | 長穴・角穴候補 |
| 円弧長寸法 | A | `SxGeomArcLengDim` | 実装入口あり | 曲げ/円弧特徴 |
| 寸法値詳細 | A | `SxDimValueAtr` | 実装入口あり | 実寸/擬寸、前置/後置/上下文字、公差、φ/R/M/□ |
| 幾何公差 | A | `SxGeomTol` | summaryのみ | 構造化未実装 |
| 表面粗さ | A | `SxGeomSmark` | 未実装 | 除去加工、筋目方向、JIS種別、指示値 |
| 溶接 | A | `SxGeomWeld`, `SxGeomWeld.MarkText` | summaryのみ | 溶接種別、開先、仕上げ等は構造化未実装 |
| 仕上げ記号 | A | `SxGeomFinishMark` | 未実装 | 仕上げ工程タグ |
| バルーン | A | `SxGeomBalloon` | summaryのみ | `txt1`, `txt2`, `num_use`, `lead_line` 等は構造化未実装 |
| シンボル / 矢視 / 切断線 | A | `SxGeomSymbol`, `SxGeomArrowView`, `SxGeomCutLine` | 未実装 | 断面図/詳細図/矢視判定 |
| 2D実像部品 | A | `SxEntRPart.getInfDetail()` -> `SxInfRPart` | 未実装 | `name`, `part3d_name`, `ref_model_name`, `ref_vs_name` |
| レファー / 配置子図 | A | `SxEntRefer.getInfDetail()` -> `SxInfRefer` | 未実装 | 参照先図面名、参照VS名、配置スケール |
| 図面名 | A/B | `SxInfModel.name`、図枠文字 | モデル名未実装、文字は実装済み | 2D/3D両方で照合対象 |
| 担当者 / 設計者 / 検図者 / 承認者 | B/D | `SxGeomText`, `SxGeomLabel` + 図枠解析 | 文字取得のみ | SXNET固定フィールドとしてはヒットなし |
| 日付 / 作成日 / 改訂日 | B/D | `SxGeomText`, `SxGeomLabel` + 図枠/改訂表解析 | 文字取得のみ | SXNET固定フィールドとしてはヒットなし |
| 材質 | B | 2D文字、注記、部品表、引出し注記 | 文字取得のみ | 2D固定材質APIではなく文字解析対象。3D材質と照合 |
| 重量 | B | 図枠文字、注記、表 | 文字取得のみ | 3Dマスプロパティと照合 |
| 表面処理 | B/D | 文字、注記、表面粗さ記号 | 文字取得のみ | 専用語はSXNET固定フィールドとしてヒットなし |
| 塗装指示 | B/D | 文字、注記 | 文字取得のみ | SXNET固定フィールドとしてはヒットなし |
| PRFX | B/D | 文字、図枠、部品表、注記 | 文字取得のみ | SXNET固定フィールドとしてはヒットなし |
| ユニット番号 | B/D | 文字、図枠、部品表、注記 | 文字取得のみ | SXNET固定フィールドとしてはヒットなし |

## 5. 現行PoCの実サンプル確認

| サンプル | mode | 結果 |
| --- | --- | --- |
| `9NK452WX90-00-LINER-A3-3D-01.json` | 3D | `top_part.name` と `parts=1` を抽出 |
| `9NK452RS60-03-CASSETTE-A0-3D-01.json` | 3D | `parts=149` を抽出 |
| `9NK452WX90-00-LINER-A3-2D-01.json` | 2D | `texts=159`, `geometry_primitives=596`, `warnings=68` |

2Dサンプルでは `SxGeomSpline2D` が未対応 warning として多数出ている。したがって、中央図面の曲線・外形特徴を実用的に扱うには、現行 `GeometryMapper` の拡張が必要。

また、同サンプルでは現行PoC上 `dimensions=0`, `balloons=0`, `tolerances=0`, `weld_notes=0` だった。これは対象図面に存在しない可能性もあるが、検索条件・ジオメトリ対応・寸法マッピングの検証が必要。

## 6. まだ完全把握できていない領域

以下は、SXNET資料上の候補または文字解析方針はあるが、実サンプル横断での取得率が未確認。

- 3D重量:
  - `SxEnt.getMass` で取れる根拠はある。
  - ただし対象要素の表示状態、シート/ソリッド混在、ワイヤ除外、パーツ/グループ単位の扱いを実サンプルで確認する必要がある。
- 3D図面サイズ:
  - `SxInfPrint` で出図範囲枠情報は取れる。
  - 3D単独属性として図面サイズを持つか、2D出図範囲由来かを分ける必要がある。
- 2D図枠:
  - 線分・文字・出図範囲から推定可能。
  - 会社別図枠により位置、欄名、表構造が変わるため、固定座標では危険。
- 担当者/承認者/日付:
  - SXNET固定フィールドは見つからない。
  - 図枠文字・表構造・欄名辞書で抽出する。
- 表面処理/塗装指示:
  - SXNET固定フィールドは見つからない。
  - 文字/注記/表面粗さ/仕上げ記号から抽出する。
- PRFX/ユニット番号:
  - SXNET固定フィールドは見つからない。
  - 2D図枠、部品表、注記、3Dパーツ名、任意情報、参照図面名から候補抽出する。

## 7. 次に必要な実調査

完全把握へ近づけるには、代表CADを複数用意して、下記を機械的に確認する必要がある。

1. `SxModel.getInf()` と `SxModel.getInfPrintList()` を現行抽出に追加し、図面名、VS数、WF数、出図範囲、用紙サイズ、作画スケールを出す。
2. `SxVS.getInf()` を追加し、VS名、尺度、ビュー種別を出す。
3. `SxEnt.getInfList()` と `SxEnt.getInfMaterialList()` を2D/3Dそれぞれで出す。
4. `SxEnt.getMass()` / `getMassList()` を3Dサンプルで試し、重量・質量・体積・面積・単位・例外条件を確認する。
5. `SxGeomSpline2D`, `SxGeomEllipse2D`, `SxGeomElparc2D`, `SxGeomHatch`, `SxGeomSmark`, `SxGeomFinishMark`, `SxGeomSymbol`, `SxGeomCutLine`, `SxGeomArrowView` を構造化する。
6. 2D文字を座標付きで保持し、図枠領域と中央図面領域に分類する。
7. 図枠欄名辞書を作り、担当者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号を候補抽出する。
8. 2D/3D照合表を作り、同一属性の一致・不一致・片側欠落を記録する。

## 8. 調査時点の回答

「3D、2Dの情報をどこまで取得できるかは完全把握できているか」に対する答えは、まだ「いいえ」。

ただし、SXNET上の取得可能性は以下のレベルまで整理できた。

- 型付きで取れるもの:
  - モデル情報、VS/WF、出図範囲、パーツ階層、パーツ属性、材質、マスプロパティ、2Dジオメトリ、寸法、注記、バルーン、溶接、幾何公差、表面粗さ、仕上げ記号。
- 文字/図枠解析で取るもの:
  - 担当者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号、客先固有欄。
- 実サンプル検証が必要なもの:
  - 重量の安定取得、図枠欄の抽出率、2D/3D間の照合ルール、寸法/記号の実データでの分類率。

したがって、現資料は「再設計資料」としては成立しているが、創屋へ最終仕様として渡すには、このマトリクスを実サンプル結果で埋める追加フェーズが必要。

## 9. 2026-07-14 追加実装反映

この資料作成後、以下は PoC 上で実装または確認済みに進んだ。

| 項目 | 実装/確認状況 | 補足 |
| --- | --- | --- |
| 2D/3D有無判定 | 実装済み | `detect` コマンドで `has_2d`, `has_2d_container`, `has_3d` を返す |
| 2D全VS確認 | 実装済み | `SxModel.getVSList()` 経由で全VSを走査する |
| VS情報 | 実装済み | VS名、尺度、コメント、ジオメトリ数を raw extract に保持 |
| 出図範囲枠 | 実装済み | `SxModel.getInfPrintList()` の結果を `print_frames` として保持 |
| レイヤー情報 | 実装済み | レイヤー一覧と、取得可能な2D要素の `layer_no` を保持 |
| 保存フォルダ/ファイル名 | 実装済み | runner の `source_file` と Django canonical attributes に保持 |
| パーツ付加情報 | 実装済み | `ex_inf` を `ex_info_fields` として展開。澁谷工業系サンプルで取得確認済み |
| 本番ナレッジ連携受け口 | 読み取り確認済み | 図面/製品/部品属性 API はフロント資産で参照あり。プロジェクト属性 API は未確認 |

最新の共有16件では、全件 `has_3d=true`、9件 `has_2d=true` だった。7件は `has_2d_container=true` だが `has_2d=false` であり、2DグローバルVSまたはVSコンテナの存在だけでは「図面情報あり」と判定できないことが確認できた。

まだ完全把握できていない領域は変わらない。特に、重量/マスプロパティ、2D文字座標による印刷枠内外判定、図枠欄名解析、未対応ジオメトリの構造化、2D/3D属性照合ルールは次フェーズで詰める。
