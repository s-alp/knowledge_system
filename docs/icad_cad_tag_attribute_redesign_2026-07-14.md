# ICAD 2D/3D 情報抽出とタグ・属性自動付与 再設計案

- 作成日: 2026-07-14
- 確認時刻: 2026-07-14 16:34:16 +09:00
- 目的: 既存 PoC の形に引っ張られず、ナレッジシステム本番へ後で埋め込める前提で、ICAD 2D/3D から取得すべき情報、タグ・属性の付与対象、自動付与方式、創屋への提供境界を再定義する。

## 1. 結論

ICAD からのタグ・属性付与は、最初から「タグを作る処理」として組むべきではない。

まず CAD 内に存在する事実を、2D/3D それぞれで可能な限り型付きで抜き出す。その後、抜き出した事実を正規化し、最後にタグへ変換する。

推奨する層は以下の 3 層。

| 層 | 役割 | 自動化方針 |
| --- | --- | --- |
| Evidence layer | SXNET で取れた生データを保持する | C# / SXNET。ここでは意味を決めつけない |
| Normalized fact layer | 図面・部品・寸法・注記・加工指示などの設計事実へ整理する | ルール、辞書、座標解析を中心にする |
| Tag proposal layer | 検索・図面管理・RAG で使うタグ候補を作る | ルール優先。曖昧分類のみ Gemini API を低温度・JSON Schema 固定で使う |

最も重要なのは、タグ付与対象を「図面ファイルだけ」に閉じないこと。

タグ付与対象は最低でも以下に分ける。

- 図面ファイル
- 3D トップパーツ / アセンブリ
- 3D 部品
- 2D シート / ビュー
- 2D 図枠
- 2D 図面本体
- 寸法・公差・幾何公差
- 注記・文字列・表
- バルーン / 部品番号
- 溶接・表面粗さ・仕上げ・加工指示

## 2. 参照ドキュメント一覧

| 参照先 | 取得した内容 |
| --- | --- |
| `AGENTS.md` | 作業ルール、PowerShell 文字化け対策、既存前提、創屋との分担 |
| `README.md` | 現行 PoC の C# / Django 分担、2D/3D mode-aware 抽出前提 |
| `tasklist.md` | 現行 PoC の完了済み範囲、未完了タスク、抽出 worker 前提 |
| `docs/extraction_result_schema_2026-05-28.md` | 既存スキーマの生抽出 / canonical / derived tags / manual overrides 分離 |
| `docs/icad_tag_attribute_implementation_backlog_2026-05-26.md` | 既存バックログの依存関係と創屋確認事項 |
| `docs/icad_2d_3d_extraction_capability_matrix_2026-07-14.md` | 3D/2D取得可能性、SXNET根拠、現行PoC実装状況、未確認事項 |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\default.html` | SXNET が外部 .NET から iCAD SX を操作するクラスライブラリであること、SxWF / SxVS / SxEnt などの役割 |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\sxnet.SxWF.getInfPartTree.html` | 3D グローバル WF の最上位パーツから階層構造、パーツ詳細情報、任意情報を一括取得できること |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\sxnet.SxVS.getSegList-1.html` | 2D VS 内のセグメントを可視/部品/レイヤ/タイプ条件付きで取得できること |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\sxnet.SxEntSeg.getGeomList.html` | セグメントから文字、注記、寸法、バルーン、溶接、幾何公差、表面粗さ、記号などを型付きジオメトリとして取得できること |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\sxnet.SxDimValueAtr@members.html` | 寸法値、実寸/擬寸、上下公差、前置/後置文字、φ/R/M/□ 等の寸法記号を取得できること |
| `C:\Users\s-iwata\Desktop\icad_api_sxnet\sxnet.SxInfPart@members.html` | パーツ名、コメント、外部パーツ、ミラー、読取専用、未解決、参照図面名、参照パスを取得できること |
| Gemini API 現行ドキュメント | `temperature` などの生成設定、`application/json`、JSON Schema / response_format による構造化出力が使えること |

## 3. 抽出の基本思想

1. 2D と 3D は片方を主、片方を補助にしない。
2. 3D は「構成・部品・外部参照・材質・配置関係」を強く持つが、図面名、図面サイズ、重量、PRFX、ユニット番号なども持つ場合がある。
3. 2D は「図枠・寸法・公差・加工指示・注記」を強く持つが、材質、重量、表面処理、塗装指示、担当者、日付、PRFX、ユニット番号なども持つ場合がある。
4. 2D の中央図面を画像的に扱う前に、SXNET のネイティブ型付き情報を優先する。
5. OCR は最後の補助であり、最初から OCR 前提にしない。
6. 一社固有の名前を schema に埋め込まない。会社別・案件別の違いは辞書パックとルールパックで吸収する。
7. 2D/3D のどちらかを固定の正本にしない。同じ属性が両方にある場合は照合し、差異を要確認として残す。

## 4. 3D から取得すべき情報

### 4.1 優先度 A: 必ず取る

| 分類 | SXNET 根拠 | 取得項目 | タグ・属性への用途 |
| --- | --- | --- | --- |
| パーツ階層 | `SxWF.getInfPartTree()` | 親子構造、ツリーパス、トップパーツ | 装置、ユニット、流用設計、構成検索 |
| パーツ詳細 | `SxInfPart` | `name`, `comment`, `cs` | 部品名、設計意図、配置系 |
| 外部参照 | `SxInfPart` | `is_external`, `path`, `ref_model_name` | 外部参照、標準部品、未解決リスク |
| ミラー | `SxInfPart.is_mirror` | ミラー有無 | 左右勝手、流用、注意タグ |
| 未解決 / 読取専用 | `is_unloaded`, `is_read_only` | 参照不備、編集制約 | 抽出信頼度、保守リスク |
| 任意情報 | `SxInfPartTree.ex_inf`, `SxWF.getInfExTopPart()` | パーツ任意情報 | 社内属性、手入力メタデータ |
| 要素情報 | `SxEnt.getInfList()` | 種別、次元、レイヤ、表示、下書き、ボディタイプ | 3D 構成の統計、抽出品質 |
| 材質 | `SxEnt.getInfMaterialList()`, `SxEntSeg.getInfMaterial()` | 材料記号、材質名称、比重 | 材質タグ、購買・加工検索 |
| 3D 側メタ情報 | パーツ名、モデル名、任意情報、参照情報、必要に応じた外部属性 | 図面名、PRFX、ユニット番号、図面サイズ、重量の候補 | 2D 図枠情報との照合、検索属性候補 |

### 4.2 優先度 B: 取るが、タグ化は慎重に行う

| 分類 | 取得項目 | 注意点 |
| --- | --- | --- |
| ソリッド / シート / ワイヤ分類 | `SxInfEnt.body_type` | 形状の存在確認には効くが、設計意味へ直結させすぎない |
| FC ソリッド状態 | `SxInfEnt.fc_state` | モデリング品質や表現状態のタグには使える |
| 3D 寸法 / パラメトリック情報 | `SxWF.getInf3DParametric()` 周辺 | 取得可否と運用実態の追加検証が必要 |
| 重量 / 体積 / 質量属性 | 材質、比重、形状情報、iCAD 側属性の組み合わせ | SXNET で直接取得できるか、計算または属性読取が必要かを実サンプルで確認する |
| 図面サイズ | モデル情報、2D 連携情報、任意情報 | 3D ファイル単独で持つ場合と 2D 図枠由来の場合を区別する |
| 3D -> 2D 投影 | `SxWF.project3D2D_2()` | 抽出元というより、確認用・2D生成用。既存図面の正本扱いはしない |

### 4.3 3D で作るべき代表タグ

- `構成:トップアセンブリ`
- `構成:外部参照あり`
- `構成:未解決参照あり`
- `構成:ミラー部品あり`
- `材質:SS400` など
- `部品役割:フレーム`
- `部品役割:ブラケット`
- `部品役割:カバー`
- `流用候補:同名部品あり`
- `品質注意:読取専用外部部品`

部品役割は名称だけで断定しない。最初は辞書候補とし、確信度を持たせる。

## 5. 2D から取得すべき情報

2D は以下の 3 領域に分けて扱う。

1. 図枠情報
2. 中央の図面本体
3. 寸法・注記・加工指示

この分割は固定座標で決め打ちしない。外周線、文字密度、表構造、図面サイズ、タイトルブロック候補を使って判定する。

### 5.1 図枠情報

図枠はタグ付けに最も効くが、会社ごとの差が大きい。したがって `title_block_fields` は固定列ではなく、正規化前は key-value 候補として持つ。

| 取得対象 | 取得方法 | 用途 |
| --- | --- | --- |
| 外周図枠 | 2D 線分、矩形、最大外接枠 | 図面サイズ、図枠領域判定 |
| タイトルブロック候補 | 右下や外周近傍の文字密度、罫線構造 | 図番、図名、尺度、改訂、作成者 |
| 表のセル候補 | 線分交差、文字配置、罫線 | 部品表、改訂表、承認欄 |
| 図面番号 | 図枠内文字 + 辞書/正規表現 | 図面識別キー |
| 図名 | 図枠内文字 + 位置 + ラベル推定 | RAG 検索・図面管理 |
| 改訂 | 図枠/改訂表 | 最新性・履歴検索 |
| 尺度 / 用紙 | 図枠文字、VS scale | 表示・プレビュー |
| 担当者 / 承認者 | 図枠内の作成、設計、検図、承認欄 | 履歴、責任範囲、問い合わせ先 |
| 日付 | 作成日、改訂日、検図日、承認日 | 最新性、履歴、版管理 |
| 重量 | 図枠または注記欄 | 3D 重量候補との照合、搬送・製作判断 |
| PRFX / ユニット番号 | 図枠、部品表、注記欄 | 装置・ユニット単位の検索、3D 構成との照合 |

図枠文字は Gemini に丸投げしない。まず位置・ラベル・周辺文字から候補を作り、Gemini は曖昧な項目名の対応付けだけに使う。

### 5.2 中央の図面本体

中央図面は、RAG に全文投入する対象ではなく、検索補助の設計特徴量として扱う。

| 取得対象 | SXNET 根拠 | 用途 |
| --- | --- | --- |
| 線 / 円 / 円弧 / スプライン | `SxEntSeg.getGeomList()` | 外形・穴・長穴・曲げなどの形状特徴 |
| ハッチング | `SxGeomHatch` | 断面、材質表現、加工領域 |
| シンボル / 矢視 / 切断線 | `SxGeomSymbol`, `SxGeomCutLine`, `SxGeomArrowView` | 断面図、詳細図、矢視検索 |
| 風船 | `SxGeomBalloon` | BOM / 部品番号との接続 |
| 実像部品 / 参照 | `SxInfEnt.kind`, `SxVS.getRPartList()` | 2D と 3D 部品の対応候補 |

中央図面から作るタグは、具体寸法の羅列ではなく、設計者が探す時に効く特徴に寄せる。

- `特徴:長穴あり`
- `特徴:丸穴多い`
- `特徴:断面図あり`
- `特徴:矢視あり`
- `特徴:ハッチングあり`
- `特徴:バルーンあり`
- `図種:組立図`
- `図種:部品図`

### 5.3 寸法・公差・加工指示

寸法は全部タグ化するとノイズになる。寸法情報は、タグ・属性・検索本文の 3 種類に振り分ける。

| 情報 | SXNET 型 | 扱い |
| --- | --- | --- |
| 長さ寸法 | `SxGeomLengthDim` | 属性 / 検索本文。重要寸法のみタグ候補 |
| 角度寸法 | `SxGeomAngDim` | 属性 / 検索本文 |
| 径寸法 | `SxGeomDiaDim` | `φ` 系タグ候補 |
| 面取り寸法 | `SxGeomChamDim` | `加工:面取り` タグ候補 |
| 長円・角穴・座標寸法 | `SxGeomAplDim` | `特徴:長穴`, `特徴:角穴` 候補 |
| 円弧長寸法 | `SxGeomArcLengDim` | 曲げ・円弧特徴 |
| 寸法値属性 | `SxDimValueAtr` | 実寸/擬寸、公差、前置/後置、φ/R/M/□ |
| 幾何公差 | `SxGeomTol` | `品質:幾何公差あり`、公差種別 |
| 表面粗さ | `SxGeomSmark` | `加工:表面粗さ`, 除去加工、筋目方向 |
| 溶接 | `SxGeomWeld` | `加工:溶接`, 溶接種別、開先、仕上げ |
| 仕上げ記号 | `SxGeomFinishMark` | 仕上げ工程タグ |
| 注記 / 文字列 | `SxGeomText`, `SxGeomLabel` | 材質、熱処理、表面処理、検査、規格 |

2D からも材質は必ず取得対象にする。材質は図枠、部品表、注記、引出し注記、表面処理欄に現れる場合があるため、`material_candidates` として複数候補を保持し、3D 側の材料情報と照合する。

2D で特に取り落としてはいけない属性:

- 図面名
- 図面番号
- 改訂
- 担当者、設計者、検図者、承認者
- 作成日、改訂日、検図日、承認日
- 図面サイズ、用紙サイズ
- 尺度
- 重量
- 材質
- 表面処理
- 塗装指示
- 熱処理
- PRFX
- ユニット番号
- 部品番号、バルーン番号
- 規格、社内規格、客先規格

### 5.4 2D/3D 共通属性の照合

同じ意味の属性が 2D と 3D の両方に存在する場合、どちらかを無条件に正としない。属性ごとに候補、根拠、信頼度、差異を持つ。

| 属性 | 2D 側候補 | 3D 側候補 | 照合方針 |
| --- | --- | --- | --- |
| 図面名 | 図枠、タイトルブロック | モデル名、トップパーツ名、任意情報 | 完全一致、正規化一致、片側欠落を判定 |
| 図面サイズ | 図枠外形、用紙欄 | モデル/任意情報にある場合 | 2D 図枠を優先候補にしつつ、3D 側値と差異確認 |
| 重量 | 図枠、注記、部品表 | 材質/形状/属性からの値 | 単位、丸め、対象範囲を見て照合 |
| 材質 | 図枠、注記、部品表、引出し注記 | `SxInfMaterial`、部品属性 | 部品単位と図面単位を混同しない |
| PRFX | 図枠、注記、部品表 | パーツ名、任意情報、外部参照名 | 表記揺れを正規化して照合 |
| ユニット番号 | 図枠、注記、部品表 | パーツ名、階層、任意情報 | 装置/ユニット/部品の粒度を分ける |
| 表面処理 / 塗装 | 注記、表面処理欄、塗装指示 | 3D 任意情報にある場合 | 基本は 2D 注記を強候補、3D 側は補助候補 |
| 日付 / 担当者 | 図枠、改訂表、承認欄 | 3D 任意情報にある場合 | 2D 図枠の欄名とセットで保持する |

照合結果は以下の形で残す。

```json
{
  "field": "material",
  "accepted_value": "SS400",
  "status": "matched|conflicted|single_source|missing|needs_review",
  "candidates": [
    {
      "source": "2d.title_block",
      "value": "SS400",
      "evidence_id": "tb-001",
      "confidence": "high"
    },
    {
      "source": "3d.material",
      "value": "SS400",
      "evidence_id": "part-014",
      "confidence": "high"
    }
  ]
}
```

## 6. タグ・属性の対象モデル

本番ナレッジシステムへ埋め込む前提では、以下の単位で ID を持つ設計にする。

| 対象 | ID 例 | 主な属性 | 主なタグ |
| --- | --- | --- | --- |
| CAD ファイル | `drawing_id` | ファイル名、更新日時、抽出モード | 図種、客先、案件 |
| 3D アセンブリ | `assembly_id` | トップパーツ名、階層深さ、部品数 | 装置、ユニット、外部参照 |
| 3D 部品 | `part_id` | パーツ名、コメント、材質、参照先、重量候補、PRFX候補、ユニット番号候補 | 部品役割、材質、流用 |
| 2D シート / ビュー | `sheet_id` | VS 名、尺度、図枠領域、図面サイズ | 図種、用紙、断面図 |
| 図枠 | `title_block_id` | 図番、図名、改訂、担当者、承認者、日付、重量、材質、PRFX、ユニット番号 | 図面識別、版管理 |
| 寸法 | `dimension_id` | 種別、値、公差、記号、座標 | φ、R、面取り、公差 |
| 注記 | `note_id` | テキスト、位置、引出線 | 材質、熱処理、表面処理、塗装、検査 |
| バルーン | `balloon_id` | 番号、使用数、位置 | BOM 接続、部品番号 |
| 照合属性 | `reconciled_attribute_id` | 2D候補、3D候補、採用値、差異状態、要確認理由 | 信頼度、未解決、要確認 |

## 7. 汎用化のための設計

一社向けで役に立たなくなる原因は、schema に会社固有語を直接入れること。

避けるべき例:

- `komatsu_equipment_type`
- `shibuya_ses_category`
- `alpine_title_block_format`

採用すべき形:

- 共通 schema: `customer_name`, `project_name`, `equipment_name`, `document_kind`, `part_role`, `process_tags`
- 辞書パック: `customer_aliases`, `equipment_aliases`, `title_block_label_aliases`, `process_terms`
- ルールパック: `title_block_layout_rules`, `drawing_kind_rules`, `part_role_rules`
- テナント / 案件別上書き: 共通 schema を壊さず、候補辞書を追加するだけにする

タグは必ず namespace を持つ。

例:

- `客先:コマツ`
- `案件:小山`
- `装置:ガントリー`
- `図種:組立図`
- `部品役割:カバー`
- `加工:溶接`
- `品質:幾何公差あり`
- `材料:SS400`
- `状態:未解決外部参照あり`

## 8. Gemini API の使い方

Gemini API は、CAD から取れた事実そのものを作るためではなく、曖昧な意味分類を補助するために使う。

### 8.1 使ってよい場面

- 図枠内のラベル揺れを `drawing_number`, `drawing_name`, `revision` などへ対応付ける
- 注記文から `材料`, `熱処理`, `表面処理`, `検査`, `安全注意` を分類する
- 部品名と周辺情報から `部品役割` 候補を出す
- 寸法・注記のまとまりから `重要寸法候補` を出す
- RAG 用の短い説明文を作る

### 8.2 使ってはいけない場面

- CAD に存在しない属性の生成
- 寸法値や公差値の補完
- 図番・改訂の推測採用
- 参照先パスや外部部品有無の推測
- 低信頼候補の自動確定保存

### 8.3 推奨設定

Gemini API は現行ドキュメント上、生成設定で `temperature` を指定でき、構造化出力では `application/json` や JSON Schema / response_format を使える。

推奨:

- `temperature`: `0` から `0.1`
- `top_p`: 低め
- `candidate_count`: `1`
- 出力: JSON Schema 固定
- enum: schema に定義した値以外は受け付けない
- 返却値: `value`, `confidence`, `evidence_ids`, `reason`, `needs_review`
- 保存: `needs_review=false` かつ信頼度閾値を超えたものだけ自動候補化

Gemini の出力は必ずバリデーションし、schema 不一致、根拠 ID 不足、存在しない値、禁止 enum は破棄する。

## 9. 創屋へ渡すべき成果物

創屋が本番ナレッジシステムへ組み込む前提で、こちらは以下を提供する。

| 成果物 | こちら | 創屋 |
| --- | --- | --- |
| Windows 抽出 CLI / worker | 作成 | 実行環境調整協力 |
| SXNET 抽出 JSON | 作成 | 本番保存先へ取り込み |
| 正規化仕様 | 作成 | 本番 DB/API へ反映 |
| タグ候補 JSON | 作成 | 図面管理・検索 UI へ反映 |
| 辞書 / ルールパック | 作成 | 管理画面への組み込み |
| 手動補正履歴仕様 | 設計 | 本番 UI / DB 実装 |
| 2D/3D プレビュー連携用 fixture | 作成 | 本番データ構造に合わせて接続 |
| RAG インデックス項目表 | 作成 | 検索基盤へ投入 |

本番移植前には、2D/3D プレビュー時と同様に、ナレッジシステム本番側の実データ構造、API 返却、画面表示項目を確認し、それを模した fixture / mock API をこちらで作る必要がある。

2026-07-14 時点の実画面確認では、図面、プロジェクト、製品・装置・ユニット、部品の各一覧にタグ/属性列は表示されていない。図面一覧には `紐づき概要` として PRJ / 製品 / 部品の関係だけが表示される。

本番フロント資産では `drawing_attributes` / `product_attributes` / `part_attributes` の API 参照を確認した。一方で `project_attributes` は確認できていない。図面詳細レスポンスには `tags` / `attributes` の受け口があるため、初期連携は図面詳細を最優先にし、製品・装置・ユニットと部品は既存属性 API への接続候補、プロジェクトは創屋への確認事項として扱う。

## 10. 推奨アーキテクチャ

```text
ICAD / sxnet.dll
  -> Windows Extractor CLI (.NET Framework)
    -> raw_3d.json / raw_2d.json
      -> Normalizer
        -> normalized_facts.json
          -> Rule Tagger
          -> Gemini Semantic Classifier
            -> tag_proposals.json
              -> Manual Review / Override
                -> production import package
```

本番ナレッジシステムへ直接書き込む処理は、この段階では作らない。

提供物は import package と API 契約に寄せる。創屋が本番側の保存先・画面・検索インデックスへ接続する。

## 11. 最初に作るべき v2 スキーマ

既存 schema は `texts`, `dimensions` が粗い。v2 では以下を分ける。

```json
{
  "source": {},
  "raw_3d": {
    "assemblies": [],
    "parts": [],
    "materials": [],
    "weights": [],
    "drawing_metadata_candidates": [],
    "element_stats": []
  },
  "raw_2d": {
    "sheets": [],
    "title_blocks": [],
    "drawing_body": [],
    "dimensions": [],
    "notes": [],
    "balloons": [],
    "tables": [],
    "manufacturing_symbols": [],
    "material_candidates": [],
    "surface_treatment_candidates": [],
    "paint_instruction_candidates": [],
    "personnel_candidates": [],
    "date_candidates": [],
    "weight_candidates": [],
    "prfx_candidates": [],
    "unit_number_candidates": []
  },
  "normalized_facts": {
    "drawing_identity": {},
    "project_context": {},
    "part_facts": [],
    "manufacturing_facts": [],
    "quality_facts": []
  },
  "cross_source_reconciliation": [],
  "tag_proposals": [],
  "manual_overrides": []
}
```

## 12. 検証計画

一社・一案件だけで検証しない。

最低限、以下を混ぜる。

- 組立図
- 部品図
- 外部参照がある 3D
- 未解決参照がある 3D
- バルーン付き 2D
- 溶接記号付き 2D
- 幾何公差付き 2D
- 表面粗さ付き 2D
- 図枠形式が違う 2D
- 客先名・案件名がファイル名にしか無い図面
- 図面内に客先名・案件名がある図面

評価指標:

- 図番抽出率
- 図名抽出率
- 改訂抽出率
- 3D 部品階層抽出率
- 外部参照 / 未解決参照検出率
- 寸法・公差分類率
- バルーン抽出率
- 加工指示抽出率
- タグ候補の妥当率
- 要レビュー候補の適切率
- 別案件混線率

## 13. 実装順序

1. SXNET HTML に基づく v2 raw schema を確定する
2. 3D 抽出を `assembly / part / material / element_stats` へ分離する
3. 2D 抽出を `title_block / drawing_body / dimensions / notes / balloons / manufacturing_symbols` へ分離する
4. 2D/3D 共通属性の候補 schema を追加する
5. 図枠領域検出を実装する
6. 2D から材質、重量、担当者、承認者、日付、尺度、図面サイズ、表面処理、塗装指示、PRFX、ユニット番号を抽出する
7. 3D から図面名、図面サイズ、重量、PRFX、ユニット番号の候補を抽出できるか実サンプルで確認する
8. 寸法値属性 `SxDimValueAtr` を正しく取り込む
9. 溶接・幾何公差・表面粗さ・仕上げ記号を summary ではなく構造化する
10. 2D/3D 照合 layer を作る
11. 正規化 layer を作る
12. ルールベース tagger を作る
13. Gemini classifier を optional plugin として作る
14. 創屋提供用 import package / fixture を作る
15. 実サンプルで評価表を作る

## 14. 創屋へ確認すべきこと

- 本番ナレッジシステムの図面管理に、図面・部品・タグ・属性をどの粒度で保存できるか
- タグは図面単位のみか、部品・寸法・注記単位にも持てるか
- プロジェクトに属性/タグを保存する既存 API または詳細画面の受け口があるか
- 製品・装置・ユニット、部品の属性 API に自動抽出タグを載せる場合、登録権限と手動補正履歴をどこに持つか
- 検索インデックスへ投入できるフィールドと型
- RAG の事前フィルタに使える属性
- 手動補正履歴を保存できるか
- 2D/3D プレビュー画面の詳細 API に渡せる項目
- 本番側で辞書/ルールを管理画面化するか、こちらのファイルを取り込むだけにするか

## 15. 完了チェックリスト

- [x] SXNET の一次 HTML を確認した
- [x] 2D と 3D の抽出対象を分けた
- [x] 図枠・中央図面・寸法情報の扱いを分けた
- [x] 2D からも材質、重量、担当者、承認者、日付、尺度、図面サイズ、表面処理、塗装指示、PRFX、ユニット番号を取得対象にした
- [x] 3D からも図面名、図面サイズ、重量、PRFX、ユニット番号を候補取得対象にした
- [x] 2D/3D のどちらかを固定の正本にせず、照合 layer を持つ方針にした
- [x] タグ付与対象を図面単位だけに閉じない方針にした
- [x] 一社固有 schema を避ける方針にした
- [x] Gemini API の使用範囲を曖昧分類に限定した
- [x] 創屋との責任分界を整理した
- [ ] 実サンプル CAD で v2 schema の抽出結果を作る
- [ ] 本番ナレッジシステムの実データ構造を確認して fixture を作る
- [ ] API 名 / 引数名を実装時に SXNET HTML と再照合する
- [ ] エラーハンドリングを「握り潰さず、抽出不能理由を warning/error に残す」方針で実装する
