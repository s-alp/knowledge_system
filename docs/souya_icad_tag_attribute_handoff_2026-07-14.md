# 創屋向け ICADタグ・属性連携項目表

- 作成日: 2026-07-14
- 対象: ICAD 2D/3D 抽出結果、タグ候補、属性候補を本番ナレッジシステムへ連携するための受け渡し整理
- 前提: 本番ナレッジシステムへの登録、更新、削除は創屋側で実装する。こちらは抽出、正規化、候補生成、fixture/API契約案を提供する。

## 1. 本番実画面の確認結果

読み取り専用で確認した。登録、変更、削除は行っていない。

| 対象 | 一覧の見た目 | 詳細の見た目 | 既存受け口の見立て | 初期連携優先度 |
| --- | --- | --- | --- | --- |
| 図面 | タグ/属性列は未表示。`紐づき概要` に PRJ / 製品 / 部品関係が出る | 基本情報に `タグ` と `属性情報` が表示される。2D/3Dプレビュー切替あり | `tags` / `attributes` / `drawing_attributes` が初期受け口候補 | 高 |
| プロジェクト | タグ/属性列は未表示 | タグ/属性の表示口は見えない | `project_attributes` は未確認。追加APIまたは補助タブが必要 | 中 |
| 製品・装置・ユニット | タグ/属性列は未表示 | `属性情報` は表示されるがタグ欄は見えない | `product_attributes` が属性受け口候補 | 中 |
| 部品 | タグ/属性列は未表示 | `属性情報` は表示されるがタグ欄は見えない | `part_attributes` が属性受け口候補 | 中 |

図面詳細の3D表示へ切り替えた際、`/web/public/models/test_000445.gltf` の読み込みで `Unexpected token '<'` エラーを確認した。抽出器とは別件だが、2D/3Dプレビュー fixture 作成時の確認事項として創屋へ共有する。

## 2. こちらが提供するデータ単位

| 提供単位 | 主なキー | 内容 | 備考 |
| --- | --- | --- | --- |
| `source_file` | `full_path`, `directory_path`, `file_name`, `extension` | 保存フォルダ、ファイル名、拡張子 | ユーザー要望により検索・追跡用属性として保持 |
| `raw_extract_2d` | `view_sheets`, `print_frames`, `layers`, `texts`, `dimensions`, `geometry_primitives` | SXNETから取得した2D証拠 | 図枠外/印刷枠外は削除せず `inside_print_area` で判定 |
| `raw_extract_3d` | `top_part`, `parts`, `mass_properties`, `mass_probe_status`, `materials`, `material_probe_status` | SXNETから取得した3D証拠 | パーツ付加情報は `ex_info_fields` として保持 |
| `canonical_attributes` | 下表参照 | 2D/3D横断の正規化属性 | 本番DB/APIへ渡す属性候補 |
| `derived_tags` | `tag`, `source`, `confidence`, `manual_flag`, `tag_rule_version` | 自動タグ候補 | 採用前にレビュー可能 |
| `conflicts` | `key`, `value2d`, `value3d`, `reason` | 2D/3D差異 | どちらかを正本に固定しない |

## 3. 図面へ連携する項目

図面は初期連携の最優先対象。詳細画面に `タグ` と `属性情報` の表示口がある。

| 分類 | 項目 | source | 連携先候補 | 信頼度方針 |
| --- | --- | --- | --- | --- |
| ファイル | ファイル名、保存フォルダ、フルパス | `source_file` | 図面属性 | 高 |
| 識別 | 図番、図面名、改訂 | `title_block_fields`, ファイル名, 3Dモデル名 | 図面属性 | 中。図枠辞書拡充後に上げる |
| 図面条件 | 図面サイズ、尺度、ビュー/用紙数、印刷枠数 | `print_frames`, `view_sheets` | 図面属性 | 中 |
| 2D図枠 | 担当者、検図者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号 | `title_block_candidates`, `title_block_fields` | 図面属性、タグ候補 | 候補値。根拠文字と座標を保持 |
| 2D特徴 | ハッチング、表面粗さ、切断線、データム、幾何公差、長穴候補、穴候補 | `geometry_feature_candidates` | 図面タグ候補 | 候補。長穴/穴は低信頼 |
| 3D構成 | 最上位パーツ名、部品数、外部参照、ミラー、未解決参照 | `top_part`, `parts` | 図面属性、タグ候補 | 高 |
| 3D重量 | 質量、重量、体積、面積、密度、重心、単位、計算対象要素数 | `mass_properties` | 図面属性 | 中から高。`mass_probe_status` と warning を併記 |
| 3D材質 | 材質ID、材質名、比重、対象要素数 | `materials` | 図面属性、材質タグ候補 | 中。日本語材質名は文字コード揺れがあるため材質IDを主キー寄りに扱う |
| パーツ付加情報 | 客先固有フィールド、PRFX候補、材質候補、ユニット候補 | `parts[].ex_info_fields` | 図面属性、部品属性 | 中。客先ごとの辞書化が必要 |

## 4. プロジェクトへ連携する項目

プロジェクト詳細にはタグ/属性の表示口が見えなかったため、創屋への確認事項にする。

| 項目 | source | 活用イメージ | 創屋確認事項 |
| --- | --- | --- | --- |
| 客先名 | 保存パス、図枠文字、3Dパーツ情報 | プロジェクト検索、絞り込み | プロジェクト属性APIの有無 |
| 案件名/プロジェクト名 | 保存パス、ファイル配置、図面紐づき | 案件単位の検索 | 既存プロジェクトとのID対応方法 |
| 装置カテゴリ | 保存パス、図枠文字、部品名 | ガントリー、ロボット、フィーダー等の絞り込み | タグとして持つか属性として持つか |
| 代表図面/代表ユニット | 図面と製品・部品の紐づき | 関連資料の入口 | 既存関連テーブルの更新方法 |

## 5. 製品・装置・ユニットへ連携する項目

詳細に `属性情報` が見えるため、タグ欄が未表示でも属性連携候補になる。

| 項目 | source | 活用イメージ | 注意 |
| --- | --- | --- | --- |
| 装置カテゴリ | パス、図枠、3D構成 | 装置・工程単位の検索 | 一社固定語にしない |
| ユニット番号 | 図枠、部品表、3Dパーツ名、パーツ付加情報 | ユニット単位の検索 | PRFXと混同しない |
| PRFX | 図枠、部品表、3D任意情報 | 客先固有の部品/装置紐づけ | 表記揺れ辞書が必要 |
| 代表材質/表面処理 | 図枠、注記、3D材質候補 | 製作・調達検索 | 部品単位材質と装置代表材質を分ける |

## 6. 部品へ連携する項目

詳細に `属性情報` が見えるため、パーツ付加情報と3D部品情報の受け口候補になる。

| 項目 | source | 活用イメージ | 注意 |
| --- | --- | --- | --- |
| パーツ名、階層パス | `parts[].name`, `parts[].tree_path` | 部品検索、BOM接続 | 同名部品があるため階層も渡す |
| 参照図面名、参照パス | `ref_model_name`, `ref_model_path` | 外部部品追跡 | 未解決参照は警告として残す |
| パーツ付加情報 | `ex_info_fields` | 材質、PRFX、客先固有分類 | 澁谷工業/ニッケ系で重要 |
| 外部参照、ミラー、読取専用、未解決 | `is_external`, `is_mirror`, `is_read_only`, `is_unloaded` | 流用/注意情報 | タグ化は中信頼 |
| 材質候補 | 2D図枠、2D注記、3D材質API、パーツ付加情報 | 加工・調達検索 | 3D材質APIは未実装 |

## 7. API/fixture の最小契約案

```json
{
  "drawingId": "host drawing id",
  "sourceFile": {
    "fullPath": "J:\\...",
    "directoryPath": "J:\\...",
    "fileName": "sample.icd",
    "extension": ".icd"
  },
  "canonicalAttributes": {
    "drawing_number": null,
    "drawing_name": null,
    "customer_name": "澁谷工業",
    "equipment_category": "ロボット",
    "mass_probe_status": "available",
    "weight_value": 0.00540269,
    "title_block_fields": {
      "material": "SUS304"
    },
    "geometry_feature_candidates": [
      {
        "feature": "surface_roughness",
        "tag": "加工指示:表面粗さ",
        "confidence": "medium",
        "count": 2
      }
    ]
  },
  "derivedTags": [
    {
      "tag": "客先:澁谷工業",
      "source": "customer_name",
      "confidence": "high",
      "manual_flag": false
    }
  ],
  "conflicts": []
}
```

## 8. 創屋への確認事項

- 図面詳細の `tags` / `attributes` の保存先テーブルとAPI名
- `drawing_attributes`, `product_attributes`, `part_attributes` の登録/更新APIの有無
- プロジェクトに属性/タグを保存するAPIまたは詳細表示口の有無
- タグは図面単位だけか、製品・ユニット・部品にも保存できるか
- 手動補正履歴をどのテーブルに保持するか
- RAG検索インデックスへ投入できるフィールド名、型、更新タイミング
- 2D/3Dプレビュー詳細APIへ追加項目を渡せるか
- 本番3Dプレビューの `test_000445.gltf` 読み込みエラーの原因

## 9. こちら側の残実装

- 3D材質APIの部品単位紐づけ。全体要素の材質一覧取得は実装済み
- 2D図枠欄名辞書の客先横断拡充
- Gemini API低温度JSON分類のジョブ組み込み。分類サービスの入口は実装済みだが、曖昧欄名の分類補助に限定し、CADに存在しない値を生成しない
- 長穴、穴数、断面、表面粗さ値を候補ではなく確定属性にする追加ロジック
- 2D/3D照合結果の採用値、差異、要確認理由の画面表示
