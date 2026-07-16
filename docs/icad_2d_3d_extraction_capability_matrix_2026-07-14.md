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
| 図面名 / モデル名 | A | `SxModel.getInf()` -> `SxInfModel.name` | 実装済み | `raw_extract.model_info.name` と `canonicalAttributes.model_name` に保持。2D/3D共通 |
| 格納フォルダ | A | `SxInfModel.path` | 実装済み | `raw_extract.model_info.path` と `canonicalAttributes.model_path` に保持。ファイルパスとの照合に使える |
| モデルコメント | A | `SxInfModel.comment` | 実装済み | `raw_extract.model_info.comment` と `canonicalAttributes.model_comment` に保持。図面メタ候補 |
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
| 材質 | A | `SxEnt.getInfMaterialList()`, `SxEntPart.getInfMaterialList()`, `SxEntSeg.getInfMaterial()` -> `SxInfMaterial` | 実装済み | 3D全体の要素材質一覧と、部品ツリー各ノードの `entpart.getInfMaterialList()` を実装。部品単位は `parts[].materials` と `part_material_candidates` に保持 |
| 重量 | A/C | `SxWF.getExtent()` -> `SxWF.getEntList()` -> `SxEnt.getMass()` -> `SxInfMass.weight` | 実装済み | `mass_probe_status` と `mass_properties.weight` に保持。対象要素なし/例外は warning |
| 質量 | A/C | `SxInfMass.mass` | 実装済み | `mass_properties.mass` に保持。測定対象がシートの場合は無効になる可能性 |
| 体積 | A/C | `SxInfMass.volume` | 実装済み | `mass_properties.volume` に保持。シートの場合 `0.0` の可能性 |
| 面積 | A/C | `SxInfMass.area` | 実装済み | `mass_properties.area` に保持 |
| 比重/密度 | A | `SxInfMaterial.spe_grav`, `SxInfMass.density`, `SxOptMass.density` | 実装済み | `SxInfMass.density` と、全体/部品材質API由来の `spe_grav` を保持 |
| 重心 | A/C | `SxInfMass.pos` | 実装済み | `center_of_gravity_x/y/z` として保持 |
| 慣性モーメント | A/C | `SxInfMass.inf_global_moment`, `inf_gravity_moment`, `inf_main_moment` | 未実装 | 検索タグより設計解析属性向け |
| 図面サイズ | C | `SxInfPrint` または 2D出図範囲との照合 | 実装済み | 3D単独の固定属性としては未確認。モデル内の2D情報から取れる可能性が高い |
| PRFX | B/D | 任意情報、パーツ名、参照図面名に含まれる可能性 | 未実装 | SXNET固定フィールドとしてはヒットなし |
| ユニット番号 | B/D | 任意情報、パーツ名、階層名に含まれる可能性 | 未実装 | SXNET固定フィールドとしてはヒットなし |

## 4. 2D 取得可能性

| 項目 | 判定 | SXNET根拠 | 現行PoC | 補足 |
| --- | --- | --- | --- | --- |
| 2DグローバルVS | A | `SxModel.getGlobalVS()` | 実装済み | `"!!GLOBAL"` VSを取得 |
| VS名 | A | `SxVS.getInf()` -> `SxInfVS.name` | 実装済み | シート/ビュー識別 |
| VS尺度 | A | `SxInfVS.scale`, `SxInfSys.scale` | 実装済み | 図枠文字の尺度とも照合する |
| VS種別 | A | `SxInfVS.type`, `view_type` | 実装済み | グローバルビュー、基本ビュー、ローカルビュー、子図 |
| VSコメント | A | `SxInfVS.comment` | 実装済み | 子図で有効 |
| 出図範囲枠 | A | `SxModel.getInfPrintList()` -> `SxInfPrint` | 実装済み | 図面サイズ・用紙・作画範囲の強い候補。`probe-2d-print` でも単独確認可能 |
| 用紙サイズ | A | `SxInfPrint.size`, `SxInfPrint.dinfo[0]`, `[1]` | 実装済み | `"A0"～"A6"`, `"B1"～"B7"`, `"XY"` |
| 用紙方向 | A | `SxInfPrint.vertical` | 実装済み | 縦/横 |
| 作画スケール | A | `SxInfPrint.dinfo[2]` | 実装済み | `-1.0` は自動 |
| 作画範囲 | A | `SxInfPrint.dinfo[3]`～`[6]` | 実装済み | 2Dグローバルビュー座標 |
| 2Dセグメント | A | `SxVS.getSegList()` | 実装済み | 可視/実像部品/レイヤ/タイプ条件あり |
| 2Dジオメトリ一括取得 | A | `SxEntSeg.getGeomList()` | 実装済み | 型付きジオメトリへ変換 |
| 文字 | A | `SxGeomText.txt`, `text_line_num`, `pnt`, `atr_word` | 実装済み | 図枠・注記・表内文字の材料 |
| 注記 | A | `SxGeomLabel.txt`, `lead_line`, `underline` | 実装済み | 材質、表面処理、塗装、規格、担当者等の抽出元 |
| 線 / 円 / 円弧 | A | `SxGeomLine2D`, `SxGeomCircle2D`, `SxGeomArc2D` | 実装済み | 図枠・中央図面・表罫線の解析元 |
| スプライン | A | `SxGeomSpline2D` | primitive実装済み | 開始座標、点数、角度候補を保持。形状特徴タグ化は未実装 |
| 楕円 / 楕円弧 | A | `SxGeomEllipse2D`, `SxGeomElparc2D` | primitive実装済み | 中心、半径、角度候補を保持 |
| ハッチング | A | `SxGeomHatch` | primitive実装済み | パターン等は summary 保持。断面/材質表現としての意味付けは未実装 |
| 長さ寸法 | A | `SxGeomLengthDim`, `SxDimValueAtr`, `SxDimLineAtr` | 実装入口あり | 現行マッピングはフィールド名要再確認 |
| 角度寸法 | A | `SxGeomAngDim` | 実装入口あり | 同上 |
| 径寸法 | A | `SxGeomDiaDim` | 実装入口あり | φ/R等のタグ候補 |
| 面取り寸法 | A | `SxGeomChamDim` | 実装入口あり | 加工タグ候補 |
| 長円/角穴/座標寸法 | A | `SxGeomAplDim` | 実装入口あり | 長穴・角穴候補 |
| 円弧長寸法 | A | `SxGeomArcLengDim` | 実装入口あり | 曲げ/円弧特徴 |
| 寸法値詳細 | A | `SxDimValueAtr` | 実装入口あり | 実寸/擬寸、前置/後置/上下文字、公差、φ/R/M/□ |
| 幾何公差 | A | `SxGeomTol` | summaryのみ | 構造化未実装 |
| 表面粗さ | A | `SxGeomSmark` | 特徴候補実装済み | `geometry_feature_candidates` で `classification_label=表面粗さ記号あり`, `searchable_tag=false` として保持。表面粗さ記号の存在だけでは自動タグに採用しない |
| 溶接 | A | `SxGeomWeld`, `SxGeomWeld.MarkText` | summaryのみ | 溶接種別、開先、仕上げ等は構造化未実装 |
| 仕上げ記号 | A | `SxGeomFinishMark` | 特徴候補実装済み | `geometry_feature_candidates` で `classification_label=仕上げ記号あり`, `searchable_tag=false` として保持。`mark_type`, `side_leng`, `width`, `color` は raw に保持 |
| バルーン | A | `SxGeomBalloon` | summaryのみ | `txt1`, `txt2`, `num_use`, `lead_line` 等は構造化未実装 |
| シンボル / 矢視 / 切断線 | A | `SxGeomSymbol`, `SxGeomArrowView`, `SxGeomCutLine` | 切断線特徴候補実装済み | 断面図/詳細図/矢視判定は未実装 |
| 2D実像部品 | A | `SxEntRPart.getInfDetail()` -> `SxInfRPart` | 実装済み | `raw_extract.referenced_parts[]` / `canonicalAttributes.referenced_2d_part_names`, `referenced_2d_part3d_names`, `referenced_2d_ref_model_names`, `referenced_2d_ref_vs_names`。印刷枠がある場合は枠内要素だけ検索候補へ採用 |
| レファー / 配置子図 | A | `SxEntRefer.getInfDetail()` -> `SxInfRefer` | 実装済み | `raw_extract.referenced_parts[]` / `canonicalAttributes.referenced_2d_ref_model_names`, `referenced_2d_ref_vs_names`。配置スケール、角度、ミラー/空参照もrawに保持 |
| 図面名 | A/B | `SxInfModel.name`、図枠文字 | 候補実装済み | `title_block_candidates` / `title_block_fields`。2D/3D両方で照合対象 |
| 担当者 / 設計者 / 検図者 / 承認者 | B/D | `SxGeomText`, `SxGeomLabel` + 図枠解析 | 候補実装済み | SXNET固定フィールドとしてはヒットなし。作成/検図/承認分類は辞書拡充が必要 |
| 日付 / 作成日 / 改訂日 | B/D | `SxGeomText`, `SxGeomLabel` + 図枠/改訂表解析 | 候補実装済み | 作成日/改訂日/承認日の分類は未実装 |
| 材質 | B | 2D文字、注記、部品表、引出し注記 | 候補実装済み | 2D固定材質APIではなく文字解析対象。3D材質と照合 |
| 重量 | B | 図枠文字、注記、表 | 候補実装済み | 3Dマスプロパティと照合 |
| 表面処理 | B/D | 文字、注記、表面粗さ記号 | 候補実装済み | 専用語はSXNET固定フィールドとしてヒットなし。表面粗さ記号は特徴候補として別保持 |
| 塗装指示 | B/D | 文字、注記 | 候補実装済み | SXNET固定フィールドとしてはヒットなし |
| PRFX | B/D | 文字、図枠、部品表、注記 | 候補実装済み | SXNET固定フィールドとしてはヒットなし。客先固有辞書の拡充が必要 |
| ユニット番号 | B/D | 文字、図枠、部品表、注記 | 候補実装済み | SXNET固定フィールドとしてはヒットなし。客先固有辞書の拡充が必要 |

### 4.1 2D印刷枠・プロッタ定義の実機確認

2026-07-15 に `probe-2d-print` コマンドを追加し、`SxModel.getInfPrintList()` と `SxInfPlot.getInfPlotList()` / `getInfDefPlot()` を読み取り専用で確認した。`SxModel.print` は実行していない。

| サンプル | 出図範囲枠 | プロッタ | デフォルト | 確認結果 |
| --- | ---: | ---: | --- | --- |
| `TR1D9K99027.icd` | 1 | 3 | `CubePDF` | A2横、範囲 `0,0` - `594,420` |
| `DFR-CM1-AA0305300011.icd` | 1 | 3 | `CubePDF` | A3横、範囲 `-410,-10` - `10,287` |
| `217008-41J-3004.icd` | 1 | 3 | `CubePDF` | A3横、範囲 `0,-0.00001943` - `420,297` |

出力JSONは `output\print_probe_2026-07-15\*_print_probe.json` に保存した。現時点では印刷実行を行わず、既存2Dビューワーへ渡すPDF/JPEG/TIFF生成は次段階の確認対象とする。

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
  - `SxWF.getExtent()` -> `SxWF.getEntList(SxBox, false)` -> `SxEnt.getMass(SxOptMass, SxEnt[])` で実装済み。
  - 共有サンプル3件で `mass_probe_status=available` を確認済み。
  - ただし対象要素なし、ICAD側計算例外、ワイヤ/シート混在の影響は `mass_probe_status` と warning で記録する。
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

1. `SxModel.getInf()` と `SxModel.getInfPrintList()` は実装済み。新規抽出ではモデル名、モデルコメント、モデル格納パス、VS数、WF数、出図範囲、用紙サイズ、作画スケールを出す。既存snapshotへ反映するには再抽出または再インポートが必要。
2. `SxVS.getInf()` は実装済み。VS名、尺度、ビュー種別を出す。
3. `SxEnt.getInfList()` と `SxEnt.getInfMaterialList()` を2D/3Dそれぞれで出す。
4. 3Dマスプロパティは実装済み。今後は部品単位/グループ単位の粒度と、例外条件のサンプル数を増やす。
5. `SxGeomHatch`, `SxGeomSmark`, `SxGeomCutLine`, `SxGeomTolDatum`, `SxGeomFinishMark`, `SxGeomElparc2D`, `SxGeomCircle2D` は特徴候補化済み。`SxGeomSpline2D`, `SxGeomEllipse2D`, `SxGeomSymbol`, `SxGeomArrowView` は追加構造化を続ける。
6. 2D文字を座標付きで保持し、図枠領域と中央図面領域に分類する。初期実装済みで、今後は中央図面/図枠の領域分類を精密化する。
7. 図枠欄名辞書は初期実装済み。担当者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号の候補を実サンプルで拡充する。
8. 2D/3D照合表を作り、同一属性の一致・不一致・片側欠落を記録する。

## 8. 調査時点の回答

「3D、2Dの情報をどこまで取得できるかは完全把握できているか」に対する答えは、まだ「いいえ」。

ただし、SXNET上の取得可能性は以下のレベルまで整理できた。

- 型付きで取れるもの:
  - モデル情報、VS/WF、出図範囲、パーツ階層、パーツ属性、材質、マスプロパティ、2Dジオメトリ、寸法、注記、バルーン、溶接、幾何公差、表面粗さ、仕上げ記号。
- 文字/図枠解析で取るもの:
  - 担当者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号、客先固有欄。
- 実サンプル検証が必要なもの:
  - 図枠欄の抽出率、2D/3D間の照合ルール、寸法/記号の実データでの分類率、3Dマスプロパティの例外条件。

したがって、現資料は「再設計資料」としては成立しているが、創屋へ最終仕様として渡すには、このマトリクスを実サンプル結果で埋める追加フェーズが必要。

## 9. 2026-07-14 追加実装反映

この資料作成後、以下は PoC 上で実装または確認済みに進んだ。

| 項目 | 実装/確認状況 | 補足 |
| --- | --- | --- |
| 2D/3D有無判定 | 実装済み | `detect` コマンドで `has_2d`, `has_2d_container`, `has_3d` を返す。2DはVSセグメント数とジオメトリ数を実体判定に使う |
| 2D全VS確認 | 実装済み | `SxModel.getVSList()` 経由で全VSを走査する |
| VS情報 | 実装済み | VS名、尺度、コメント、ジオメトリ数を raw extract に保持 |
| 出図範囲枠 | 実装済み | `SxModel.getInfPrintList()` の結果を `print_frames` として保持。2D文字・寸法・記号系には `inside_print_area` と所属枠 `print_frame_no` を保持 |
| レイヤー情報 | 実装済み | レイヤー一覧と、取得可能な2D要素の `layer_no` を保持 |
| 保存フォルダ/ファイル名 | 実装済み | runner の `source_file` と Django canonical attributes に保持 |
| ICADモデル情報 | 実装済み | `SxModel.getInf()` の `name`, `comment`, `path`, `is_read_only`, `nvs`, `nwf` を `model_info` と canonical attributes に保持 |
| パーツ付加情報 | 実装済み | `ex_inf` を `ex_info_fields` として展開。澁谷工業系サンプルで取得確認済み |
| 本番ナレッジ連携受け口 | 読み取り確認済み | 図面/製品/部品属性 API はフロント資産で参照あり。プロジェクト属性 API は未確認 |
| 未対応2Dジオメトリ | primitive実装済み | `SxGeomSpline2D`, `SxGeomEllipse2D`, `SxGeomElparc2D`, `SxGeomHatch`, `SxGeomSmark`, `SxGeomCutLine`, `SxGeomDelta`, `SxGeomTolDatum` を warning ではなく raw evidence として保持 |
| 2D/3D属性照合 | 基本形実装済み | `reconciledAttributes` に一致、片側のみ、統合、手動上書き、競合、採用値、理由を保持。詳細画面にもレビュー行を表示 |
| 2D形状・記号属性 | 実装済み | 表面粗さ記号数/値、断面・切断表現数、長穴/楕円候補数、穴/円候補数、候補径を canonical attributes と詳細画面へ表示 |
| 3D部品材質候補 | 実装済み | `SxInfPartTree.entpart` から `SxEntPart.getInfMaterialList()` を呼び、部品別材質は高信頼候補として保持。単一パーツ/単一全体材質とパーツ付加情報は補助候補として保持 |
| Gemini図枠分類補助 | 実装済み | 2D抽出ジョブで `title_block_candidates` を低温度JSON分類し、`title_block_llm_classifications` と候補行の `llm_*` に保持。APIキー未設定時はスキップ、API失敗時は warning に記録。実API評価は `gemini_probe_after_parse_fallback_2026-07-15.json` と評価JSONで確認済み。classification precision 1.0000、positive recall 0.5000、guardrail safety 1.0000、accepted uplift 0 |
| 図枠欄名断片の誤採用抑止 | 実装済み | `製図者` など欄名だけの文字から `者` を値として採用しない。候補行は残し、採用値からは除外 |
| 2D訂正内容候補 | 実装済み | `訂正内容`, `改訂内容`, `変更`, `修正`, `REV` 系の文字を `revision_note_candidates` に保持。詳細画面にも根拠文字、座標、印刷枠内外を表示 |

最新の共有16件では、全件 `has_3d=true`、9件 `has_2d=true` だった。7件は `has_2d_container=true` だが `has_2d=false` であり、2DグローバルVSまたはVSコンテナの存在だけでは「図面情報あり」と判定できないことが確認できた。再検証では9件で `segment_count > 0`、9件で `geometry_count > 0` となり、現時点の共有16件ではセグメント数とジオメトリ数の実体判定は整合している。

3D重量/マスプロパティは実装と共有サンプル3件での取得確認まで進んだ。3D材質は全体要素の材質一覧取得、部品ツリー各ノードの材質一覧取得、部品材質候補生成まで進んだ。共有済みICAD 39件の3D横断抽出では、39件成功、全体材質33件、部品別材質13件、部品材質API warning 0件だった。2D図枠欄名解析は初期辞書、候補表示、Gemini低温度JSON分類のジョブ組み込みまで進んだ。2D primitive は特徴候補タグと形状・記号属性の両方へ展開した。2D/3D属性照合は基本形を実装し、競合だけでなく片側欠落や統合理由も保持できる。まだ完全把握できていない領域は、部品単位マスプロパティ、材質ID `ZZZ` や `75` など客先固有値の辞書化、2D図枠欄名辞書の客先横断拡充、円/楕円を穴・長穴として断定する客先横断条件である。
