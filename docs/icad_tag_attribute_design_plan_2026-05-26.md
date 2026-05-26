# ICADタグ・属性 設計計画書

- 作成日: 2026-05-26
- 対象: ナレッジシステムの `図面管理`、図面詳細 viewer、RAG 検索
- 前提: タグ・属性は `図面管理` を正本とし、viewer と RAG はそこから参照・利用する

## 1. 参照ドキュメント一覧

| 参照元 | この設計で使う観点 |
| --- | --- |
| `C:\Users\s-iwata\Desktop\knowledge_system\docs\icad_tag_attribute_investigation_2026-05-26.md` | 調査結果の事実、推測、未確認事項 |
| `C:\Users\s-iwata\Desktop\knowledge_system\AGENTS.md` | プロジェクト前提、RAG 課題、作業制約 |
| `C:\Users\s-iwata\Desktop\knowledge_system\docs\PDMナレッジシステム見積調査まとめ_2026-04-27.md` | 図面登録/タグ自動取得/CAD 連携の想定 |
| `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR\docs\viewer-specification.md` | viewer bootstrap metadata と mock detail の現状 |
| `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR\frontend\src\shared\types\viewer.ts` | 現行 API 型 |
| `C:\Users\s-iwata\Desktop\2D_3D_CAD_VIEWR\frontend\src\shared\mock\drawingKnowledge.ts` | viewer に見せたい詳細情報の形 |

## 2. 抽出内容

- `図面管理` で正本化すべき項目の単位
- `sxnet` から抽出する 2D/3D ネイティブ情報の扱い
- viewer に残す軽量項目と detail API へ分ける項目
- RAG の事前フィルタと再ランキングに使う属性群
- 形式別の責務分離
  - ICAD 3D
  - ICAD 2D
  - STEP
  - PDF
  - 画像/OCR

## 3. 目的と非目的

### 3.1 目的

- `図面管理` に、タグ・属性の正本として使える保存モデルを定義する。
- ICAD 2D/3D の抽出結果を、RAG と viewer の両方で再利用できる canonical attribute に正規化する。
- 次会話以降で、PoC 実装と保存/API 連携を迷わず始められる粒度まで設計の枠を固める。

### 3.2 非目的

- この文書時点で本番 API や DB スキーマを断定しない。
- OCR や STEP 抽出の最終精度を保証しない。
- viewer 単体の見た目改善を主目的にしない。
- タグを自然言語だけで自動生成する方式を主軸にしない。

## 4. 設計原則

1. タグより属性を先に定義する。
2. `図面管理` を正本とし、viewer と RAG は消費側に寄せる。
3. 生抽出値を捨てずに保持し、正規化結果と分離する。
4. 自動生成タグは再生成可能にする。
5. 手動補正を前提にし、補正履歴を持てる構造にする。
6. 形式別に精度保証範囲を分ける。
7. RAG の負例制御に効く属性を優先して整備する。

## 5. データモデル

## 5.1 基本レイヤ

### `raw_extract`

- 役割: 形式別抽出結果の原文・原値を保持する。
- 目的:
  - 再抽出比較
  - デバッグ
  - 正規化ロジック改善
  - 手動補正時の元値確認

想定項目:

- `drawing_id`
- `source_format`
- `source_kind`
- `extractor_name`
- `extractor_version`
- `executed_at`
- `status`
- `payload`
- `warnings`

### `canonical_attributes`

- 役割: 一覧、絞り込み、viewer 詳細、RAG 前処理で使う正規化済み項目を持つ。
- 目的:
  - 画面横断の共通属性化
  - 辞書ベースの別名吸収
  - 条件付き検索の安定化

### `derived_tags`

- 役割: `canonical_attributes` と辞書から導出した UI/検索補助用のラベルを持つ。
- 目的:
  - UI で見やすい多値ラベル化
  - ユーザーの別名入力吸収
  - 手動検索補助

### `manual_overrides`

- 役割: 手動で修正・追加・削除した属性/タグを持つ。
- 目的:
  - 自動抽出の誤りを補正
  - 運用上必要な上書き
  - 誰が何を直したかの追跡

## 5.2 canonical attribute の最小単位

### 共通属性

| グループ | 項目 |
| --- | --- |
| 識別 | `drawing_id`, `drawing_number`, `drawing_name`, `revision` |
| 文書種別 | `source_format`, `source_kind`, `document_kind` |
| 業務文脈 | `customer_name`, `project_name`, `equipment_name`, `equipment_category`, `module_name` |
| 管理情報 | `status`, `owner`, `design_purpose`, `paper_size` |
| 抽出品質 | `extraction_status`, `ocr_used`, `confidence_summary`, `extraction_version` |

### 3D 寄り属性

| グループ | 項目 |
| --- | --- |
| トップ情報 | `top_part_name`, `top_part_comment`, `top_part_ex_info` |
| 部品構成 | `part_names[]`, `part_comments[]`, `part_tree_paths[]` |
| 外部参照 | `ref_model_names[]`, `ref_model_paths[]`, `external_part_exists` |
| その他 | `mirror_part_exists`, `unresolved_part_exists` |

### 2D 寄り属性

| グループ | 項目 |
| --- | --- |
| 文字 | `text_tokens[]`, `label_texts[]`, `title_block_fields` |
| 寸法 | `dimension_values[]`, `dimension_symbols[]`, `tolerance_texts[]` |
| 記号/注記 | `weld_note_texts[]`, `balloon_keys[]`, `surface_treatment_tokens[]`, `spec_tokens[]` |

### 業務補助属性

| グループ | 項目 |
| --- | --- |
| 部品/材料 | `part_keywords[]`, `material_keywords[]`, `maker_keywords[]` |
| 工程/処理 | `process_keywords[]`, `heat_treatment_keywords[]`, `inspection_keywords[]` |
| 変更/不具合 | `change_keywords[]`, `issue_keywords[]` |

## 6. タグと属性の役割分担

### 属性に寄せるもの

- 客先名
- 案件名
- 装置名
- 装置カテゴリ
- 図面番号
- 図面種別
- 文書種別
- 部品構成
- 寸法/公差/規格
- 材料/工程/処理

### タグに寄せるもの

- 表示用の簡潔なラベル
- 類義語吸収用ラベル
- 補助検索用の多値語
- 運用上のピン留め語

### ルール

- タグだけを正本にしない。
- 属性から再生成できないタグは手動タグとして明示する。
- タグ生成辞書は、別名・略語・部署内通称を吸収する用途に限定する。

## 7. 形式別の抽出方針

### 7.1 ICAD 3D

- 主入力:
  - `SxWF.getInfPartTree()`
  - `SxEntPart.getInfDetail()`
  - `SxWF.getInfExTopPart()`
- 優先抽出:
  - パーツ階層
  - パーツ名
  - コメント
  - 外部参照図面名
  - 参照パス
  - 最上位任意情報
- 正規化対象:
  - 案件名候補
  - 装置名候補
  - 部位名候補
  - BOM 連携キー

### 7.2 ICAD 2D

- 主入力:
  - `SxEntSeg.getGeom()`
  - `SxEntSeg.getGeomList()`
- 優先抽出:
  - 一般文字
  - 注記
  - 寸法値
  - 公差文字
  - 記号
  - 溶接注記
  - バルーン
- 正規化対象:
  - 図面番号
  - 案件/客先/装置関連語
  - 寸法/規格関連語
  - 材料/熱処理/表面処理関連語

### 7.3 STEP

- viewer の表示変換経路と、検索属性抽出経路を分けて考える。
- 本設計段階では、STEP からの canonical attribute 生成は要検証扱いとする。
- ICAD 3D と同じ精度を前提にしない。

### 7.4 PDF

- サーチャブル PDF は OCR より先にテキスト抽出を使う。
- 規格表や仕様書は、文書種別ごとに読み方を変える前提にする。
- 表構造復元が弱い場合は、列挙項目の信頼度を下げる。

### 7.5 画像/TIFF/JPEG/PNG

- OCR は補助手段とし、以下を明示する。
  - 使用したかどうか
  - どの項目が OCR 起点か
  - 信頼度
- OCR 起点項目は、図面管理で手動補正しやすい UI 前提にする。

## 8. 利用先別の設計方針

### 8.1 `図面管理`

`図面管理` を以下の責務で使う。

- 登録時:
  - ファイル登録
  - 抽出ジョブ起動
  - 抽出結果プレビュー
  - 手動補正
  - 保存
- 一覧:
  - `customer_name`
  - `project_name`
  - `equipment_category`
  - `document_kind`
  - `source_format`
  - `status`
  - `tags`
  で絞り込み
- 詳細:
  - 基本情報
  - 属性情報
  - 抽出根拠
  - 手動補正履歴
  - 抽出ステータス
  を表示

### 8.2 viewer

- bootstrap には軽量サマリだけを残す。
- 詳細情報は別 detail API で返す前提にする。
- viewer は read-only とし、属性編集責務は持たせない。

detail API で返したい最小単位:

- `tags[]`
- `attributeGroups[]`
- `remarks`
- `evidence[]`
- `manualOverrideSummary`

### 8.3 RAG

- 事前フィルタで強く使う属性:
  - `customer_name`
  - `project_name`
  - `equipment_category`
  - `document_kind`
  - `source_format`
- 再ランキングで使う属性:
  - `part_names`
  - `part_keywords`
  - `spec_tokens`
  - `material_keywords`
  - `process_keywords`
  - `dimension_values`
  - `weld_note_texts`
- 返答制御:
  - 条件不一致資料は候補から外す
  - 根拠不足時は「参考なし」または「案件未特定」で止める

## 9. 公開インターフェースとして定義すべきもの

### 9.1 図面属性保存スキーマ

- `drawing_id`
- `raw_extract`
- `canonical_attributes`
- `derived_tags`
- `manual_overrides`
- `updated_at`
- `updated_by`

### 9.2 viewer detail API 契約

- bootstrap と別に定義する。
- mock detail を置き換える単位で返す。

### 9.3 抽出結果 JSON 契約

PoC で先に固定したい最小形:

```json
{
  "drawing_id": "string",
  "source_format": "icad|step|pdf|tiff|jpeg|png",
  "source_kind": "2d|3d",
  "extractor_name": "string",
  "extractor_version": "string",
  "status": "success|partial|failed",
  "raw_extract": {},
  "canonical_attributes": {},
  "derived_tags": [],
  "warnings": []
}
```

### 9.4 RAG インデックス投入項目

- フィルタ用属性
- 検索拡張用タグ
- 根拠表示用の抽出断片
- 信頼度/抽出元情報

## 10. フェーズ分割

### Phase 1: 抽出 PoC

- ICAD 3D 抽出 PoC
- ICAD 2D 抽出 PoC
- 形式別サンプル収集
- 抽出結果 JSON 契約の仮固定

### Phase 2: 図面管理保存

- canonical attribute 定義確定
- 図面管理保存先確認
- 抽出プレビューと手動補正の要件整理

### Phase 3: viewer 詳細連携

- bootstrap 拡張範囲決定
- detail API 定義
- mock detail 差し替え

### Phase 4: RAG 連携

- インデックス投入項目整理
- フィルタ/再ランキング接続
- 既存失敗シナリオで再評価

## 11. リスク

- `図面管理` の保存先/API が固まらないと、設計だけ先行しても viewer/RAG へ接続できない。
- 2D の意味付けルールが弱いと、文字は取れても案件・装置・規格へ正規化できない。
- OCR を正式対象に広げすぎると、検収条件が曖昧になりやすい。
- STEP を ICAD 同等に扱う前提は危険で、別経路の検証が必要である。

## 12. 完了チェックリスト

- [ ] 調査結果と設計案を別文書に分離している
- [ ] 事実と改善提案を混在させていない
- [ ] `図面管理`, viewer, RAG の役割を分けている
- [ ] `3D ICAD`, `2D ICAD`, `STEP`, `PDF`, `画像/OCR` を分けている
- [ ] 属性を正本、タグを派生物として整理している
- [ ] viewer の mock detail 差し替え方針がある
- [ ] RAG の事前フィルタと再ランキングで使う属性が分かれている
- [ ] 開発先確認事項が独立している

## 13. 次に必要なこと

- 実サンプルを使った 3D/2D 抽出 PoC
- 図面管理の保存先と API 契約の確認
- 手動補正フローの要件整理
- RAG 側で canonical attribute をどう参照するかの設計着手
