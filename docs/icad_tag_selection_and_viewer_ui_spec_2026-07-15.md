# ICADタグ選定・2D/3Dビューワー連携仕様

更新日: 2026-07-15 09:25:33 +09:00

## 位置づけ

この文書は、ICAD 2D/3D抽出結果から「何をタグにするか」「何を属性に留めるか」「どの対象へ渡すか」を決めるための仕様である。

完成版の表示UIは、既に創屋へ提出済みの `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR` を基準にする。`knowledge_system` 側の `/drawing-metadata/` と `/drawing-metadata/handoff/` は、抽出結果、正規化結果、viewer bootstrap、RAG payload、本番ナレッジシステム向けpayload候補を確認するための内部検証画面であり、創屋へ見せる完成UIの土台にはしない。

## 2D/3D有無判定の意味

2D/3Dの有無は、用途ごとに意味を分ける。

| 判定 | 意味 | 使い道 |
| --- | --- | --- |
| `detect.has_2d` | SXNET上で2D図面として使える実体を検出できたか | 抽出前の実データ判定 |
| `detect.has_2d_container` | VSや印刷枠など2Dコンテナらしきものがあるか | 2Dなし/空図面/検出不足の切り分け |
| `detect.has_3d` | SXNET上で3D部品ツリーを検出できたか | 抽出前の実データ判定 |
| `viewerBootstrap.availability.has2d` | viewerが2D表示用sourceまたは2D snapshotを持つか | 2D/3Dビューワーのタブ表示 |
| `viewerBootstrap.availability.has3d` | viewerが3D表示用sourceまたは3D snapshotを持つか | 2D/3Dビューワーのタブ表示 |

`viewerBootstrap.availability.has2d=false` かつ `has3d=false` は、ICADファイルに2D/3Dが存在しないという意味ではない。登録だけ済んで抽出snapshotが無い場合も同じ表示になるため、検証画面では「未抽出」と表示する。

## 完成版UIの基準

完成版UIは2D/3Dビューワーの流れへ寄せる。

1. 図面詳細または図面一覧から `drawingId` でビューワーを開く。
2. `GET /api/v1/drawings/{drawingId}/bootstrap` で、2D/3D表示可否、図面基本情報、タグ、主要属性を取得する。
3. `availability` と `defaultMode` で2D/3Dタブを決める。
4. 2D側は既存の `viewer2d/open`、3D側は `viewer3d/open` の流れを使う。
5. タグ・属性はビューワー内の補助情報として、図面の視認や類似検索の補助に使う。
6. 本番ナレッジシステムへの登録、更新、削除はこのPoC側からは行わない。創屋へ渡すのは読み取り用API契約、fixture、payload仕様である。

### bootstrap拡張

提出済み2D/3Dビューワーの既存契約を壊さないため、既存キーは維持する。

- `metadata.tags`: 既存ビューワーでも表示できる単純なタグ名配列。
- `metadata.tagAttributes`: タグ・属性補助パネル用の追加payload。既存ビューワーが未知キーを無視しても、2D/3D表示は壊れない。
- `metadata.knowledgeDetail`: 改訂履歴、関連情報、変更履歴、属性情報、備考を表示する補助セクション用payload。固定モックではなく、ICAD抽出snapshot、訂正候補、監査ログ、創屋連携payload候補から作る。
- `metadata.extractionDiagnostics`: 未抽出・部分抽出を放置しないための診断payload。ビュー差、レイヤー差、印刷枠差、パーツ付加情報差を再試行条件として明示する。

`metadata.tagAttributes` の形:

```json
{
  "schemaVersion": "viewer_tag_attributes.v1",
  "sourceSchemaVersion": "knowledge_system_payload_preview.v1",
  "displayPolicy": "2D/3Dビューワー内の補助パネル表示用。ここから本番登録・更新・削除は行わない。",
  "targetCount": 4,
  "reviewRequired": true,
  "targets": [
    {
      "targetKey": "drawing",
      "label": "図面",
      "tagApiStatus": "candidate_existing",
      "writePolicy": "preview_only_no_production_write",
      "tags": ["材質:SUS304"],
      "attributes": [
        {
          "name": "図面名",
          "value": "BRACKET",
          "sourcePath": "canonicalAttributes.drawing_name",
          "entityHint": null,
          "bindingStatus": "needs_attribute_master_binding"
        }
      ],
      "reviewRequired": true,
      "notes": ["図面の tags は既存表示口があるため第一優先の連携候補。"]
    }
  ]
}
```

`tagAttributes.targets` は図面、プロジェクト、製品・装置・ユニット、部品を同時に返す。ビューワー側では初期表示で図面向けを開き、必要に応じて対象別タブまたは折りたたみで他対象候補を見せる。

`metadata.knowledgeDetail` の形:

```json
{
  "schemaVersion": "viewer_knowledge_detail.v1",
  "attributes": [
    {"label": "材質", "value": "SUS304"}
  ],
  "remarks": "2D/3D統合結果または設計目的",
  "revisionHistory": [
    {
      "version": "R1",
      "updatedAt": "2026-07-16T10:00:00+09:00",
      "updatedBy": "ICAD抽出",
      "summary": "A 寸法変更",
      "status": "印刷枠内 / 信頼度:medium"
    }
  ],
  "relatedTabs": [
    {
      "id": "drawing",
      "label": "図面",
      "items": [
        {
          "id": "drawing",
          "title": "図面",
          "subtitle": "図面詳細にタグと属性情報が表示される",
          "description": "図面のtagsは既存表示口があるため第一優先の連携候補。",
          "chips": ["材質:SUS304", "属性7件"]
        }
      ]
    }
  ],
  "changeHistory": [
    {
      "version": "2D",
      "changedAt": "2026-07-16T10:00:00+09:00",
      "changedBy": "ICAD抽出",
      "summary": "2D snapshotを更新"
    }
  ],
  "tagAttributeTargets": [],
  "tagAttributePolicy": "タグ・属性候補は図面管理で確認し、必要に応じて再抽出・手直しします。",
  "tagAttributeReviewRequired": true
}
```

`metadata.extractionDiagnostics` の形:

```json
{
  "schemaVersion": "viewer_extraction_diagnostics.v1",
  "status": "partial",
  "missingModes": ["2d"],
  "policy": "未抽出は確定不可ではなく、ビュー差・レイヤー差・印刷枠差・パーツ付加情報差を条件別に再試行する。",
  "requiredConditionChecks": [
    {
      "key": "allViews",
      "label": "全ビュー走査",
      "reason": "ICADは1データ内に複数枚・複数ビューを内包するため、初期ビューだけでは図枠・寸法・表題欄を取り逃がす。"
    },
    {
      "key": "allLayers",
      "label": "全レイヤー走査",
      "reason": "寸法、表題欄、訂正履歴、材質、パーツ付加情報が客先や図面種別で別レイヤーに分かれる可能性がある。"
    },
    {
      "key": "printFrame",
      "label": "印刷枠判定",
      "reason": "図枠外の作業メモや退避形状を本番タグ候補へ混入させないため、印刷範囲内外を分けて記録する。"
    },
    {
      "key": "partAttributes",
      "label": "パーツ付加情報",
      "reason": "2D/3D形状とは別の情報源として、ニッケ・澁谷などの客先データに存在する付加情報を個別に読む。"
    }
  ]
}
```

`status` は `extracted`、`partial`、`not_extracted` の3段階とする。`availability.has2d/has3d` が `false` の場合でも「存在しない」とは断定せず、`missingModes` と `requiredConditionChecks` を見て条件別再抽出へ回す。

## タグ化の基本方針

タグは検索、絞り込み、類似検索、設計レビューの入口として使う。すべての抽出値をタグにしない。

| 分類 | タグ化 | 属性化 | 理由 |
| --- | --- | --- | --- |
| 客先名 | する | する | プロジェクト横断検索に効く |
| 装置/ユニット種別 | する | する | 製品・装置・ユニット単位の検索に効く |
| 材質 | する | する | 加工、購買、類似部品検索に効く |
| 要確認材質 | 低信頼タグにする | する | `ZZZ`, `75`, `CDQ` などを正式材質へ混ぜない |
| 表面処理/塗装 | する | する | 外注、加工条件、類似検索に効く |
| 図面サイズ/尺度 | 原則タグにしない | する | 検索タグより属性フィルタ向き |
| 重量/質量 | 原則タグにしない | する | 数値範囲検索、レビュー向き |
| 担当者/承認者 | 原則タグにしない | する | 人名タグはノイズと権限面の懸念がある |
| 日付 | 原則タグにしない | する | 期間フィルタ向き |
| PRFX/ユニット番号 | 条件付きでタグ化 | する | 客先運用上の検索キーなら有効 |
| 2D訂正内容本文 | しない | 根拠として保持 | 本文タグ化はノイズが大きい |
| 改訂情報あり | する | する | レビュー入口として有効 |
| 形状特徴 | 条件付きでタグ化 | する | 長穴、穴、表面粗さ、断面などは類似検索補助に効く |
| 図枠外/印刷枠外情報 | 自動タグ化しない | raw証跡に保持 | 図面外メモや古い残骸の誤採用を避ける |

## 対象別のタグ・属性適用

### 図面

図面は最優先の連携対象である。本番画面上でもタグ欄と属性情報欄が確認できている。

| 項目 | タグ | 属性 | 根拠 |
| --- | --- | --- | --- |
| 図面名/図番 | 原則タグにしない | する | 2D図枠、3D部品名、ファイル名 |
| 客先名 | する | する | 保存パス、図枠、プロジェクト文脈 |
| 装置/ユニット | する | する | 保存パス、図枠、3Dトップ部品名 |
| 材質 | する | する | 2D材質欄、3D材質API、パーツ付加情報 |
| 表面処理/塗装 | する | する | 2D注記、図枠、加工指示 |
| 図面サイズ/尺度 | しない | する | 2D印刷枠、図枠 |
| 重量/質量 | しない | する | 3Dマスプロパティ、2D図枠 |
| 改訂情報あり | する | する | 2D訂正欄/REV/変更/修正文字 |
| 形状特徴 | 条件付きでタグ化 | する | 2D primitive、表面粗さ、切断線、長穴候補 |

### プロジェクト

プロジェクト詳細ではタグ/属性欄の表示口は未確認であるため、初期連携は候補扱いにする。

| 項目 | タグ/属性候補 | 注意 |
| --- | --- | --- |
| 客先名 | タグ候補 | 既存プロジェクト情報と重複しやすい |
| 案件名/装置系統 | 属性候補 | 保存パスから推定する場合は根拠を残す |
| 主要ユニット | タグ候補 | 複数図面から集計して付与する |
| 材質/加工特徴 | 原則プロジェクトには付けない | 図面/部品へ寄せる |

### 製品・装置・ユニット

製品・装置・ユニット詳細には属性情報欄が確認できている。タグ欄は未確認のため、初期は属性中心にする。

| 項目 | タグ/属性候補 | 根拠 |
| --- | --- | --- |
| ユニット番号 | 属性候補、必要ならタグ | 2D図枠、3D部品名、パーツ付加情報 |
| PRFX | 属性候補、必要ならタグ | パーツ付加情報、ファイル名、図枠 |
| 装置カテゴリ | タグ候補 | 保存パス、図面名、トップ部品名 |
| 主要材質 | 属性候補 | 配下図面/部品から集計 |
| 主要形状特徴 | 属性候補 | 配下図面から集計 |

### 部品

部品詳細には属性情報欄が確認できている。パーツ付加情報と3D部品材質候補の主な受け先にする。

| 項目 | タグ | 属性 | 根拠 |
| --- | --- | --- | --- |
| 部品名/部品番号 | 原則タグにしない | する | 3D部品ツリー、2D図枠、ファイル名 |
| 材質 | する | する | 3D材質API、パーツ付加情報、2D材質欄 |
| 要確認材質 | 低信頼タグ | する | 未解決材質ID |
| 表面処理/塗装 | する | する | 2D加工指示、パーツ付加情報 |
| PRFX/ユニット | 条件付きでタグ | する | パーツ付加情報 |
| 外部参照パス | しない | する | 3D参照情報。パスはタグにしない |

## 自動タグ化しない情報

- 図枠外、印刷枠外、印刷枠判定不明の要素。ただし印刷枠が取得できない図面では、情報欠落としてraw証跡に残し、別途レビュー対象にする。
- Gemini APIが推測した値。Geminiは欄名分類の補助に限定し、CADに存在しない値は採用しない。
- 人名、メール、電話番号、社内メモ、議事録由来の文言。
- 数値だけの重量、寸法、日付。これらは属性または検索用レンジにする。
- 図面の訂正文本文。タグは `改訂情報あり` までに留める。

## 根拠と信頼度

各タグ・属性候補は、最低限以下を持つ。

| 項目 | 内容 |
| --- | --- |
| `value` | 候補値 |
| `target` | drawing / project / product_unit / part |
| `source` | 2d_title_block / 2d_note / 2d_geometry / 3d_part_tree / 3d_material / part_ex_info / path / filename |
| `confidence` | high / medium / low |
| `evidence` | 元文字、部品パス、座標、レイヤー、印刷枠内外、ファイルパスなど |
| `review_required` | 人の確認が必要か |

## 2D/3D照合

2Dと3Dのどちらかを正本に固定しない。

- 同じ値なら統合値として採用する。
- 片方だけに値がある場合は採用するが、根拠sourceを残す。
- 材質、重量、図面名、図面サイズ、PRFX、ユニット番号が不一致の場合は `conflicts` として設計レビュー対象にする。
- 件数、confidence summary、抽出元の存在フラグなど内部品質差分は `diagnosticConflicts` に分離し、設計レビュー対象へ混ぜない。

## 創屋への渡し方

創屋へは画面を丸ごと渡すのではなく、以下を渡す。

1. 2D/3Dビューワー基準の `bootstrap` 契約。
2. 図面/プロジェクト/製品・装置・ユニット/部品別のタグ・属性候補payload。
3. 2D/3D抽出snapshotを含むfixture。
4. タグ化しない情報と、レビュー必須情報のルール。
5. 本番ナレッジシステム側で既存のタグ/属性受け口へどう対応させるかの確認事項。

## 現時点の不足

- プロジェクト詳細のタグ/属性受け口は未確認。
- 製品・装置・ユニット、部品のタグ保存口は未確認。属性情報欄は確認済み。
- 2D/3Dビューワーfrontendには、図面向けタグ・属性パネル、ICAD登録・抽出・再抽出・手直し・候補確定画面を実装済み。
- 製品・装置・ユニット一覧/詳細と部品一覧/詳細は固定モックではなく、ICAD 3D構成から生成した実データを表示する。ただし、子ノードありだけではサブアセンブリと判定しない。`subassembly` は外部参照、参照モデル名/パス、または手動確定がある場合だけ扱う。
- `GET /api/v1/knowledge-entities?target=product|part` と `GET /api/v1/knowledge-entities/{entityId}` を読み取りAPIとして使用する。
- レビュー状態は2D/3D snapshotごとに `pending` / `confirmed` / `needs_correction` を保持する。再抽出または手直し後は `pending` へ戻す。
- `viewerBootstrap.availability.has2d/has3d` はviewer表示可否であり、ICADの実体検出結果ではない。この区別をAPI資料に明記する必要がある。

## 3D構成の対象分類

| ICAD構成 | ナレッジ画面 | 判定 |
| --- | --- | --- |
| ルートで子ノードあり | 製品・装置・ユニット | アセンブリ |
| 中間ノードで外部参照あり | 製品・装置・ユニット | サブアセンブリ |
| 中間ノードで外部参照なし | 製品・装置・ユニット | アセンブリ/内部構成診断 |
| 子ノードなし | 部品 | 末端部品 |

ファイル名や客先別命名規則だけで分類しない。新しい抽出結果では `node_id`、`parent_node_id`、`depth`、`child_count`、`entity_kind`、`is_external`、`ref_model_name`、`ref_model_path` を使い、旧抽出結果では `tree_path` の親子関係と外部参照情報から同じ分類を復元する。
