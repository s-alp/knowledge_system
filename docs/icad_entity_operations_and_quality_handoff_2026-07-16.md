# ICAD登録情報・タグ品質・創屋移植引継ぎ

- 作成日: 2026-07-16
- 対象: 共有済みICAD 39件、統合2D・3Dビューワー、Django連携API、C#抽出器
- 境界: 創屋本番DBへの登録、変更、削除は一切行わない。本資料の保存・編集・紐づけはローカル検証DBだけを対象とする。

## 1. 登録単位と分類

- 登録単位は `1 ICD = 1件`。ICD内のパーツノードを製品・部品一覧へ展開しない。
- `製品・装置・ユニット` は、手動確定、保存名の組立・ユニット語、またはSXNETの外部参照パーツを根拠にする。
- `部品` は、部品・部品図フォルダの明示根拠、または外部参照構成を確認できないICDを候補にする。
- 子階層があることだけではアセンブリ、サブアセンブリと判定しない。
- `subassembly` は `is_external`、`ref_model_name`、`ref_model_path` のいずれかで親子の外部参照関係が確認できる場合、または手動確定が得られた場合だけ扱う。自動で捏造しない。
- 分類根拠、信頼度、理由は `classificationEvidence`, `classificationConfidence`, `classificationReason` で返す。

内部構成診断は `output/souya_handoff/icad_entity_classification_analysis_2026-07-16.json` に保存する。固定manifest 39件では内部パーツ出現4,051件、補正後の内部診断分類は `part=3782`, `assembly=177`, `subassembly=92`。これは内部ツリーの診断値であり、ナレッジシステム登録件数ではない。

## 2. 業務状態と抽出状態

- 利用者向けの `ステータス` は業務状態であり、未設定時は `-` と表示する。
- `確認待ち`、`未確認`、競合、再抽出要否は抽出レビュー状態であり、業務状態へ混ぜない。
- 抽出レビュー状態は取得根拠・管理導線だけで確認する。

## 3. 一覧・詳細・編集・紐づけ

| 機能 | API / 保存先 | 補足 |
| --- | --- | --- |
| ユーザー画面入口 | `http://127.0.0.1:5173/` | 2D・3Dビューワー統合フロント。図面管理、製品・装置・ユニット、部品、システム設定はここで見る |
| バックエンド入口 | `GET /` | API専用ステータスJSONを返す。`/drawing-metadata/` のDjango画面は通常導線から外し、404にする |
| 内部確認画面 | `GET /internal/drawing-metadata/` | 開発・検証用のDjango HTML。創屋へ見せる完成UIではない |
| 対象一覧 | `GET /api/v1/knowledge-entities?target=product|part` | 1 ICDを1行で返す |
| 対象詳細 | `GET /api/v1/knowledge-entities/{entity_id}` | 基本情報、属性、タグ、関連情報、履歴、根拠を返す |
| 図面候補 | `GET /api/v1/drawing-options?q=...&limit=100` | 図面名・保存先を検索する。API候補は固定manifest対象39件、詳細画面の紐づけ候補は自己図面を除く38件を実ブラウザで確認 |
| 編集・紐づけ保存 | `PATCH /api/v1/drawing-metadata/registrations/{drawing_id}/overrides` | `businessFields`, `relatedDrawingIds`, `knowledgeEntityTarget`, `knowledgeEntityKind` を受ける |
| システム設定表示 | `GET /api/v1/drawing-metadata/settings/tag-automation` | タグ自動取得設定、対象別ルール、システム設定内の管理導線を返す |
| 引継ぎ集計 | `GET /api/v1/drawing-metadata/handoff-summary` | システム設定内の `API仕様・引継ぎ資料` で使う登録ICAD、対象別payload、APIリンクの集計を返す |

編集値と紐づけIDは `manual_overrides_json` に保存し、抽出スナップショットのraw証拠を上書きしない。変更履歴には抽出更新と手動更新を分けて残す。

ローカルDBにはブラウザ検証アップロード、重複アップロード、途中検証用 `cad_data` 登録も残るため、利用者向け一覧、図面候補、製品・装置・ユニット、部品、引継ぎ集計は `DRAWING_METADATA_HANDOFF_MANIFEST` の固定manifestで共有39件へスコープする。2026-07-16時点の実DBは全登録68件、固定manifest対象39件、対象外29件。対象39件は2D/3D snapshotあり39件、未抽出0件である。対象外29件は検証登録として集計対象外にし、`scripts/audit_registered_drawings.py` で内訳を確認する。

## 4. 取得根拠

各属性・タグは以下を追跡できる。

- `source`: 2D図枠、3D材質、3D質量、パーツ付加情報、保存パス、手動補正など
- `evidence`: raw JSON内の参照位置または根拠文字
- `confidence`: high / medium / low
- `reason`: 採用または分類理由
- `reconciledAttributes`: 2D値、3D値、採用値、採用元、差異状態

`S45C相当` の確認例は `G1630-S3000-502_A3a1.icd`。図枠文字ではなく、3D材質APIの `mat_id=S45C相当`, `name=S45C相当_MisumiFA` と、パーツ付加情報 `User_MisumiFA_Material=S45C相当` が根拠である。

## 5. タグ採用規則

- 検索・分類に直接使える客先、装置カテゴリ、メーカー、正式材質、仕様値、図枠の表面処理・塗装値だけを自動タグ候補にする。
- 表面粗さ、データム、幾何公差、穴・長穴、ハッチング等は属性・raw証拠として保持し、汎用タグにはしない。
- `改訂情報あり` のような存在フラグはタグにしない。訂正内容は属性・変更根拠として保持する。
- 未解決材質コードは通常材質へ混ぜず、`材質要確認:<値>` として分離する。
- 2026-07-16 DB監査: snapshot 81件、タグ120件、禁止タグ0件、取得元欠落0件、採用理由欠落0件。

## 6. 質量・重量

- 表示単位はkgへ統一する。
- 小数点以下2桁で表示する。
- SXNETの質量と重量値、2D図枠のkg表記を区別して正規化する。
- 共有39件中38件は質量取得あり。`DFR-CM1-AA0305300011.icd` は3D質量を取得できず、値を捏造せず `massAvailable=false` とする。

## 7. Gemini実API評価

Geminiは低温度の図枠候補分類補助だけに使う。CADに存在しない値の生成、ルール値の上書き、値なし候補の採用は禁止する。

2026-07-16に共有抽出から17ファイル、正解値あり8候補、値なし52候補を実API評価した。プロンプトへ以下を追加した。

- 値がnull/空なら `field=null`
- 参考図番・元図を現在図番にしない
- 材質等級を含まない形鋼・寸法だけを材質にしない

再評価結果:

| 指標 | 結果 |
| --- | ---: |
| classification precision | 1.0000 |
| classification positive recall | 1.0000 |
| classification false positive | 0 |
| guardrail false positive | 0 |
| guardrail safety rate | 1.0000 |
| accepted uplift | 0 |

誤採用防止は確認できたが、ルール抽出を上回る新規採用値は0件である。したがってGeminiは任意補助のままとし、品質向上効果があるとは断定しない。

## 8. 共有39件監査

監査証跡: `output/souya_handoff/icad_shared_sample_current_audit_2026-07-16.json`

| 項目 | 件数 |
| --- | ---: |
| 登録済み | 39 / 39 |
| 2D snapshot | 39 / 39 |
| 3D snapshot | 39 / 39 |
| 2D内容あり | 31 |
| 2D要素なし | 8 |
| 内容ありでビュー取得 | 31 / 31 |
| 内容ありでレイヤー取得 | 31 / 31 |
| 印刷枠あり | 28 / 31 |
| 複数印刷枠 | 2 |
| 印刷枠未定義 | 3 |
| パーツ付加情報あり | 19 |
| 材質候補あり | 29 |
| 質量取得あり | 38 |
| snapshot欠落 | 0 |

印刷枠未定義3件は `U8718-S71-002_A3.icd`, `XH3001-M08007-01.icd`, `U8718-S71-149_A4.icd`。通常抽出と `probe-2d-print` の双方で印刷枠0件を確認した。抽出失敗ではなくデータ側の枠未定義として、座標・ビュー・レイヤーを保持し、`inside_print_area` は判定不明のままにする。

2D要素なし8件は空の成功として隠さず `no_2d_entities` と記録し、3D構成・材質・質量・パーツ付加情報は保持する。

## 9. 検証結果

- Django drawing_metadata: 71 passed
- Django system check: issue 0
- migration差分: なし
- 統合フロント: 58 passed
- TypeScript + Vite production build: 成功
- C# solution: 14 passed
- Chrome実操作: 製品・部品詳細、取得根拠、編集画面、図面紐づけ候補38件、抽出状態非表示、システム設定内の `API仕様・引継ぎ資料` / `ICAD抽出管理` 表示、旧Django画面や図面管理へ遷移しないことを確認
- 固定manifestスコープ監査: 全登録68件、対象39件、対象外29件。対象39件は2D/3D snapshotあり39件、未抽出0件
- ICAD構成分類監査: `subassembly` は外部参照根拠ありに限定。固定manifest39件の内部診断分類は `part=3782`, `assembly=177`, `subassembly=92`
- Chrome console / page / HTTP error: 0
- 視覚比較: `design-qa.md`, Result: passed

## 10. 創屋への引継ぎ境界

こちらが提供するのは、抽出器、正規化・照合・タグ生成、読み取りAPI、ローカル編集・紐づけ動作、fixture、API仕様、根拠・信頼度・差異情報である。本番ナレッジシステムのID解決、属性マスタ対応、DB保存、権限、監査ログ統合は創屋側で実装する。本番DBへこちらから書き込まない。
