# 製品・装置・ユニット・部品とタグ付けシステム 改善点洗い出し

- 作成日: 2026-07-17
- 対象: `backend/apps/drawing_metadata`(Django) と `src/IcadExtraction.*`(C#) の現行実装
- 前提:
  - セキュリティ観点は今回対象外とする。
  - 本システムは創屋株式会社へ引き渡して本体ナレッジシステムへ統合する前提である。
  - したがって「契約(スキーマ・API)の明確さ」「データとコードの分離」「移植時に説明できる一貫性」を重視して洗い出す。
- 凡例:
  - [重大] 挙動として誤り、または引き渡し後に確実に問題化する
  - [高] 設計目的(RAG精度・図面管理正本化)を満たせていない
  - [中] 品質・保守性の問題
  - [低] 細かい整理事項

## 0. 要約(優先度順)

| # | 区分 | 改善点 | 優先度 |
| --- | --- | --- | --- |
| 1 | ライフサイクル | 再抽出で手動タグ・タグ削除が消える(手動補正が再適用されない) | 重大 |
| 2 | ライフサイクル | 削除したはずの自動タグが統合結果で復活する | 重大 |
| 3 | ライフサイクル | 属性の手動補正を項目ごとに保存すると、以前の補正記録が丸ごと置き換わる | 重大 |
| 4 | ドメインモデル | 製品・装置・ユニット・部品のエンティティが存在せず、全てが図面単位のJSON文字列 | 高 |
| 5 | タグモデル | タグの正体が「表示文字列(`客先:xxx`)」で、名前空間・値・辞書との対応を持たない | 高 |
| 6 | 辞書 | 客先・装置・メーカー・規格辞書がPythonコード内のハードコード定数 | 高 |
| 7 | 正規化 | 表記ゆれ吸収が `.lower()` のみ。全角半角・カナ・NFKC正規化が無い | 高 |
| 8 | 正規化 | 部分文字列一致による誤ヒット(`ses` が `hoses` 等に一致)と先勝ち単一値マッチ | 高 |
| 9 | 正規化 | `project_name`・`equipment_name`・`module_name`・`drawing_number`・`title_block_fields` 等が一切埋まらない | 高 |
| 10 | 根拠 | 「どのトークンからどのタグが付いたか」の根拠(evidence)が保存されない | 高 |
| 11 | 部品情報 | 部品の name/comment/tree_path の対応関係が正規化時に分解され、部品単位の情報が消える | 高 |
| 12 | 合成 | 2D/3D競合時の `chosenMode` 記録が実際の採用値と食い違う。競合属性はタグ自体が消える | 中 |
| 13 | API/UI | 一覧のフィルタ・ページネーション未実装。タグ・属性での絞り込みができない | 中 |
| 14 | 契約 | ドキュメント(snake_case)と実装(camelCase)のスキーマ乖離、`attributeGroups` の型不整合 | 中 |
| 15 | 運用 | 辞書・ルール改訂後に再抽出なしで再正規化する手段(コマンド)が無い | 中 |

---

## 1. ドメインモデル: 製品・装置・ユニット・部品

### 1.1 [高] 階層エンティティが存在しない

- 現状: `RegisteredDrawing` と `DrawingMetadataSnapshot` のみで、製品(案件)・装置・ユニット・部品はすべて
  `canonical_attributes_json` 内のフラットな文字列/文字列リストである
  (`backend/apps/drawing_metadata/models.py:16`, `models.py:69`)。
- 問題:
  - 「この部品はどのユニットの下で、どの装置・どの案件に属するか」を問い合わせる手段が無い。
  - CLAUDE.md の検証所見にある「BOM/部品 -> 案件名の変換が弱い」というRAG課題は、
    構造化された `部品 -> ユニット -> 装置 -> 案件` の対応表なしには解決できない。
  - 図面と装置・案件がN:1で暗黙に結合しており、同一部品が複数案件で使われるケース(流用設計)を表現できない。
- 改善案:
  - 最低限、以下のマスタ/リンクテーブルをDjangoモデルとして起こす。
    - `Customer`(客先) / `Project`(案件) / `Equipment`(装置) / `Unit`(ユニット) / `Part`(部品)
    - `DrawingLink`(図面と上記エンティティの関連。関連根拠と信頼度を持つ)
  - 3D抽出の `tree_path` は既に階層を持っている(`src/IcadExtraction.Contracts/Models.cs:57`)。
    中間ノードをユニット候補、末端を部品候補として構造のまま保存すれば、追加抽出なしで階層化できる。

### 1.2 [高] `part_tree_paths` の文字列化で構造が失われる

- 現状: `" > ".join(part.get("tree_path", []))` で1本の文字列に潰している
  (`backend/apps/drawing_metadata/services/normalization.py:97`)。
- 問題:
  - 部品名に `>` や空白が含まれると復元不能。
  - 「Top直下の第2階層だけ(=ユニット層)を集計する」といった問い合わせができない。
- 改善案: `tree_path` は文字列配列の配列のまま保持する。表示用文字列は表示層で組み立てる。

### 1.3 [高] 部品単位の属性対応が分解される

- 現状: `part_names` / `part_comments` / `ref_model_names` を別々にflattenしており、
  空値を除去するため添字の対応も崩れる(`normalization.py:95-99`)。
- 問題:
  - 「PART-A のコメントは何か」「PART-B は外部参照か」を後段(根拠表示・RAG)で復元できない。
  - `is_external` / `is_mirror` / `is_unloaded` は `〜exists` の図面単位boolに縮約され、どの部品がそうなのか消える。
- 改善案: `canonical_attributes` に部品単位のレコード配列
  (`parts: [{name, comment, tree_path, ref_model_name, is_external, ...}]`)を残し、
  横断検索用のトークンリストはそこからの派生値として持つ。

### 1.4 [中] 図面の同一性・重複登録の制御が無い

- 現状: `RegisteredDrawing` に `source_path` / `host_drawing_id` の一意制約が無い(`models.py:16-29`)。
  1つの `source_path` に対し 2D/3D 両モードのスナップショットがぶら下がる設計だが、
  実際のICAD運用では 2D図面と3Dモデルは別ファイルであることが多い。
- 問題:
  - 同一図面の重複登録が可能で、タグ・属性の正本が複数できる。
  - 「同じ設計対象の2Dと3D」を同一 `RegisteredDrawing` に束ねる手段が登録時に存在しない
    (登録APIは単一 `sourcePath` のみ受ける。`api/serializers.py:14-22`)。
- 改善案:
  - `source_path` に一意制約(または正規化済みパスのハッシュ)を付ける。
  - 「設計対象(製品/装置)」と「ファイル(図面/モデル)」を分け、2D/3Dのペアリングを明示的な関連として持つ。

## 2. タグ付けの仕組み

### 2.1 [高] タグの正体が表示文字列でしかない

- 現状: タグは `{"tag": "客先:コマツ小山", "source": "customer_name", ...}` という形で、
  識別子が表示文字列そのものである(`services/tag_builder.py:10-21`)。
- 問題:
  - 名前空間(`客先`)と値(`コマツ小山`)がコロン区切りの文字列に埋め込まれており、
    値側にコロンが入ると壊れる。全角コロンとの揺れも防げない。
  - タグ名の改名(例: `客先`→`顧客`)が全図面の文字列書き換えになる。
  - 統合先(創屋側)のタグ体系とマッピングする際、文字列パース以外の手段が無い。
- 改善案:
  - タグを `{namespace, value, display, dictionary_entry_id, source, confidence, manual_flag, rule_version}` に分解する。
  - できれば `TagDefinition`(タグ辞書)テーブルと図面-タグの中間テーブルを持ち、JSONは表示キャッシュ扱いにする。

### 2.2 [高] 辞書がコードにハードコードされている

- 現状: 客先3件・装置3件・メーカー1件・規格1件が `seed_dictionaries.py` の定数
  (`services/seed_dictionaries.py:4-22`)。
- 問題:
  - 客先・装置カテゴリの追加のたびにデプロイが必要。引き渡し後、創屋側で運用者が育てられない。
  - 辞書のバージョン・改訂履歴が持てず、`tag_rule_version` (settings固定値 "1.0.0")と辞書実体が対応しない。
- 改善案:
  - 辞書をDBテーブル化(`DictionaryEntry {kind, canonical_value, aliases[], enabled, updated_at}`)し、
    Django admin で編集可能にする。seed はfixture/管理コマンドで投入。
  - 辞書改訂時に `tag_rule_version` を自動採番し、スナップショットに記録済みのバージョンと差分比較できるようにする。

### 2.3 [高] マッチングが部分文字列一致で誤ヒットする

- 現状: 全トークンを空白連結して小文字化した1本の文字列に対し `candidate in lowered` で判定
  (`services/normalization.py:26-31`, `:160-166`)。
- 問題:
  - `ses` は `hoses` / `processes` 等の英単語に、`smc` も任意の部分文字列に誤ヒットする。
    「SESが一般語に誤解されやすい」というRAG検証所見と同種の誤りを、メタデータ側で再生産してしまう。
  - トークンを連結しているため、トークン境界をまたいだ一致も起こり得る。
- 改善案:
  - トークン単位の完全一致・語境界付き一致を基本にし、部分一致はあえて使う場合のみ信頼度を下げて区別する。
  - どのトークンがどの候補語に一致したかを結果(根拠)として返す(→ 2.6)。

### 2.4 [高] 表記ゆれ吸収が `.lower()` のみ

- 現状: 正規化は小文字化だけで、全角/半角(`ＳＥＳ`/`SES`、`ｶﾞﾝﾄﾘｰ`/`ガントリー`)、
  ひらがな/カタカナ、長音・中黒などの吸収が無い(`normalization.py:27-29`)。
- 問題: 設計計画書(`docs/icad_tag_attribute_design_plan_2026-05-26.md` §5.3-4)が掲げる
  「表記ゆれ、別名、略語、全角半角差を辞書で吸収」が実装されていない。
  日本語CAD文字列では全角英数が頻出するため、実データで辞書がほぼ効かない恐れがある。
- 改善案: マッチング前に NFKC 正規化 + カナ統一を必ず通す共通関数を用意し、
  辞書側 alias も同じ正規化を通して保存する。

### 2.5 [中] 単一値・先勝ちマッチで複数候補を扱えない

- 現状: `_match_dictionary` は辞書の定義順で最初に一致した1件だけ返す(`normalization.py:26-31`)。
- 問題:
  - 1図面に複数客先語(流用元と流用先など)が含まれると、辞書の並び順という無関係な要因で決まる。
  - 複数候補があった事実自体が失われ、確認UIにも出せない。
- 改善案: 全一致候補を収集し、`customer_name_candidates[]` として保持した上で
  優先順位ルールで主候補を選ぶ。複数候補時は `confidence` を下げ、確認UIに出す。

### 2.6 [高] タグ・属性の根拠(evidence)が保存されない

- 現状: 正規化・タグ生成のどこにも「どの元テキスト・どの部品名から判定したか」が残らない。
  タグの `source` は属性名(`customer_name` 等)だけである(`tag_builder.py:23-33`)。
- 問題:
  - UI計画(`docs/tag_attribute_management_ui_plan_2026-05-28.md` §3.5)の「抽出根拠セクション」が
    raw_extract の生データ一覧しか出せず、「なぜこのタグが付いたか」に答えられない。
  - 誤タグの原因調査(辞書の悪いalias特定)が手作業になる。
- 改善案: マッチ結果に `{matched_token, matched_alias, source_field, part_index}` を持たせ、
  `derived_tags[].evidence` として保存する。

### 2.7 [中] `spec_tokens` の意味が混在している

- 現状: 2Dでは `spec_tokens` に「全テキスト+公差文字列」を代入した後(`normalization.py:141`)、
  辞書一致した規格正規名(`SES`)を同じリストへ追記する(`normalization.py:164-166`)。
  さらに `tag_builder` 側はハードコードの集合 `{"SES"}` に入っているものだけをタグ化する(`tag_builder.py:32`)。
- 問題:
  - 「生トークン」と「正規化済み規格名」が同一属性に混ざり、フィルタ・RAG投入で使い物にならない。
  - タグ化対象の規格集合が `SPEC_KEYWORDS` と `{"SES"}` の二重管理になっている。
- 改善案: `spec_tokens`(生)と `spec_names`(正規化済み)を分離し、タグ化は `spec_names` 全件を対象にする。

### 2.8 [中] 未実装の業務補助属性が「常に空」で契約上は存在する

- 現状: `material_keywords` / `process_keywords` / `heat_treatment_keywords` / `inspection_keywords` /
  `change_keywords` / `issue_keywords` / `surface_treatment_tokens` / `title_block_fields` 等は
  初期化されるだけで、どのコードパスでも値が入らない(`normalization.py:38-87`)。
  設計計画書の例(`heat_treatment_keywords` あり -> `工程:熱処理` タグ)も未実装。
- 問題: 統合先から見ると「空なのか未実装なのか」が区別できず、RAG側でフィルタに使うと全件除外になる。
- 改善案: 未実装項目はスキーマから外すか、`canonical_attributes` に実装状況を注記した契約書
  (`docs/extraction_result_schema_2026-05-28.md`)を実態に合わせて改訂する。実装する場合は辞書テーブルに
  `kind=material|process|heat_treatment...` を追加して同一機構で処理する。

## 3. 手動補正・再抽出・統合のライフサイクル

### 3.1 [重大] 再抽出すると手動タグとタグ削除が消える

- 現状: `save_extraction_snapshot` は `derived_tags_json` を自動生成タグで丸ごと上書きする
  (`services/persistence.py:64`)。`manual_overrides_json` は残るが、
  保存時にも統合時にも `manual_overrides.derivedTags`(added/removed)は再適用されない。
  統合処理が拾う手動タグは「スナップショットの `derived_tags_json` 内の `manual_flag=True` の行」だけである
  (`services/composition.py:111-116`)。
- 問題: 利用者が付けた手動タグ・消した誤タグが、再抽出1回で全て巻き戻る。
  「手動補正を前提にし、補正履歴を持てる構造にする」(設計原則5)に反し、運用に乗せると確実に信頼を失う。
- 改善案: タグの最終状態を「自動タグ(毎回再生成) + overrides.added - overrides.removed」の合成として
  保存/表示の両方で一貫して計算する。手動情報の正本は `manual_overrides_json` に一本化する。

### 3.2 [重大] 削除した自動タグが統合結果(composedMetadata)で復活する

- 現状: `apply_manual_overrides` はスナップショットの `derived_tags_json` からは削除するが
  (`persistence.py:119-122`)、`compose_drawing_metadata` は統合属性から
  `build_derived_tags` でタグを再生成するため(`composition.py:116`)、
  属性(例: `equipment_category`)が残っている限り削除済みタグが統合結果に再出現する。
  `manual_overrides.derivedTags.removed` は統合時に一切参照されない。
- 問題: 詳細API(`composedMetadata`)・一覧・RAG投入のいずれも統合結果を使う想定のため、
  利用者からは「消しても消えない」ように見える。
- 改善案: 統合時に全モードの `manual_overrides.derivedTags.removed` を集約し、再生成タグから除外する。

### 3.3 [重大] 属性補正を項目ごとに行うと以前の補正記録が置き換わる

- 現状: `manual_overrides.update({"canonicalAttributes": payload.get("canonicalAttributes", ...)})` により、
  ペイロードに `canonicalAttributes` があると補正マップ全体が置換される(`persistence.py:106-112`)。
- 問題:
  - 「属性Aを補正 → 後日属性Bを補正」とすると、Aの補正記録が `manual_overrides_json` から消える。
  - 統合処理は `manual_overrides_json` を見て手動値を優先するため(`composition.py:39-46`)、
    Aの手動優先が効かなくなり、その後の再抽出でAの補正値も実質失われる。
- 改善案: `canonicalAttributes` はキー単位でマージし、削除は明示的な `null`/`removed` 指定で行う。
  `derivedTags.added/removed` も累積集合としてマージする。

### 3.4 [中] 2D/3D競合の記録が実態と食い違う・競合するとタグが消える

- 現状:
  - 競合記録の `chosenMode` は常に `"3d"` 固定だが、実際の採用値は
    `manual_3d > manual_2d > value_3d > value_2d` の順で決まる(`composition.py:75-94`)。
    手動2D補正が採用されても記録は「3Dを採用」となる。
  - 競合したキーは `excluded_sources` としてタグ生成から除外されるため(`composition.py:116`,
    `tag_builder.py:23-33`)、例えば客先名が2D/3Dで食い違うと、統合属性には3D値が入るのに
    `客先:` タグだけが消える。
- 改善案: `chosenMode` は実際の採用元(manual_2d/manual_3d/3d/2d)を記録する。
  競合時もタグは採用値から生成し、`confidence` を下げて競合フラグを付ける方が一覧・RAGには有用。

### 3.5 [中] `process_job` の統合呼び出しが結果を捨てている

- 現状: `compose_drawing_metadata(job.drawing)` を呼ぶが戻り値を捨てており、副作用も無い
  (`tasks/extraction_tasks.py:97`)。統合結果はリクエストのたびに再計算され、どこにも永続化されない。
- 問題:
  - 統合結果(RAG投入や一覧絞り込みの本命データ)がインデックス化できない。
  - 詳細取得のたびに全スナップショットを読んで再計算するため、一覧+詳細系のコストが図面数に比例して悪化する。
- 改善案: 統合結果スナップショット(`composed` レイヤ)をテーブルとして永続化し、
  抽出成功時・補正保存時に更新する。RAG投入・一覧フィルタはそこを読む。

### 3.6 [中] 辞書・ルール改訂後の再正規化コマンドが無い

- 現状: `raw_extract_json` は保存されているのに、ICAD再抽出(Windows + ICAD起動が必要で高コスト)を
  介さずに正規化・タグ生成だけをやり直す管理コマンドが存在しない。
- 問題: 辞書を直しても既存図面に反映する現実的な手段が無く、「自動生成タグは再生成可能にする」
  (設計原則4)が絵に描いた餅になる。
- 改善案: `re_normalize_snapshots` 管理コマンドを追加し、`normalizer_version`/`tag_rule_version` の
  差分があるスナップショットだけを raw_extract から再計算できるようにする。

### 3.7 [低] 監査ログが肥大化する構造

- 現状: 抽出のたびに `before_json`/`after_json` へ raw_extract 全文(2Dだと全テキスト・全寸法)を二重保存する
  (`persistence.py:55-83`)。
- 改善案: raw はジョブID参照に留め、監査ログには canonical/tags の差分だけを残す。

## 4. API・UI

### 4.1 [中] 一覧のフィルタ・ページネーション未実装

- 現状: 一覧API/一覧ページとも全件返しで、UI計画(§2.1, §4)の必須フィルタ
  (客先・案件・装置カテゴリ・文書種別・形式・抽出状態)が未実装
  (`api/views.py:21-30`, `views.py:16-24`)。
- 問題: タグ・属性がJSON列の中にあるため、現構造のままではフィルタ実装が全件スキャン+Python絞り込みになる。
  1.1/2.1 の正規化テーブル化とセットで解決すべき。
- 改善案: 統合結果スナップショット(3.5)に主要属性列(customer, project, equipment_category, document_kind,
  status)とタグ中間テーブルを持たせ、クエリパラメータでのフィルタ+ページネーションを実装する。

### 4.2 [中] 一覧シリアライザのN+1

- 現状: `get_latestJobStatusByMode` が図面ごと・モードごとに `obj.jobs.filter(...)` を発行し、
  prefetch が効かない(`api/serializers.py:126-131`)。
- 改善案: prefetch済み `obj.jobs.all()` をPython側でモード別に振り分けるか、モード別最新ジョブを
  annotate で取る。

### 4.3 [中] HTML補正フォームの入力検証が無い

- 現状: `json.loads(raw_payload)` を try/except なしで実行(`views.py:83`)。不正JSONで500になる。
  `extraction_mode` もPOST値をそのまま使い、choices検証なしで `enqueue_extraction_job` へ渡る
  (`views.py:69-79`)。
- 改善案: Django Form/DRFシリアライザを通し、エラーは messages で返す。mode は choices 検証する。
  そもそも「補正 = 生JSONを手書き」というUI自体を、属性行ごとの編集+タグチップ操作(UI計画§3.4, §3.6)へ
  置き換えるのが本筋。

### 4.4 [低] 契約の細かい不整合

- `attributeGroups` の `attributes` が、他グループは dict なのに `conflicts` グループだけ list
  (`composition.py:122-143`)。消費側の型定義が壊れる。
- スキーマ文書は `manual_overrides.canonical_attributes`(snake_case)だが実装は
  `canonicalAttributes`(camelCase)(`docs/extraction_result_schema_2026-05-28.md` §8 vs `persistence.py:108-111`)。
- 文書の必須項目にある `title_block_fields` 等が実装では常に空(2.8参照)。
- `derived_tags` 文書仕様に無い `tag_rule_version` がタグ行へ入る一方、evidence は無い。
- `MODE_PRIORITY` が定義のみで未使用(`composition.py:10`)。優先順は分岐にハードコードされている。
- 改善案: 引き渡し前に「スキーマ文書と実装の突き合わせ表」を作り、文書を正として実装を寄せるか、
  実装を正として文書を改訂するかを項目ごとに確定する。

## 5. 信頼度・品質表示

### 5.1 [中] confidence が実質固定値

- 現状: `confidence_summary` は 2D=medium / 3D=high の固定(`normalization.py:56`, `:168-169`)。
  タグの confidence も source 種別ごとの固定値(`tag_builder.py:10-33`)で、
  スキーマ文書§9の「OCR起点・曖昧一致は低め」等のルールが反映されない。
  `extraction_status` も warnings の有無にかかわらず常に `success`(`normalization.py:54`)。
- 改善案: マッチ方式(完全一致/部分一致/複数候補)・抽出元(3Dネイティブ/2D文字/OCR)から信頼度を算出する
  関数を1箇所に集約し、`extraction_status` は warnings/欠損項目から `partial` を判定する。

## 6. 創屋への引き渡しを見据えた進め方(提案)

1. **正しさの回復(3.1〜3.3)を最優先で直す。** 手動補正が消える挙動のまま統合すると、
   統合後の不具合として発覚し切り分けが難しくなる。
2. **タグ・辞書のデータモデル化(2.1, 2.2)を次に行う。** コード内辞書のままだと、
   引き渡し後の運用主体(創屋/アルパイン)がどちらであっても辞書を育てられない。
3. **正規化の底上げ(2.3〜2.6, NFKC)** はRAG精度検証の観点と直結するため、
   実サンプル(コマツ小山ガントリー、広島アルミ)での回帰テストを先に固定してから改修する。
4. **エンティティ階層(1.1〜1.3)は統合先との契約論点。** 創屋側の本体に部品・装置マスタが
   ある可能性が高いため、「こちらで正本を持つ」か「本体マスタへ寄せてIDだけ持つ」かを
   開発先確認事項として起票してから実装する(勝手にマスタを二重化しない)。
5. **API契約(4.1, 4.4)は統合インターフェースそのもの。** フィルタ仕様・スキーマ文書を
   実装と一致させた状態で引き渡す。

## 7. 開発先(創屋)確認事項の候補

- 本体ナレッジシステム側に客先・案件・装置・部品のマスタは存在するか。存在する場合のID体系。
- タグの名前空間設計(客先/案件/装置/規格/工程/材料)を本体側の検索UI・RAGフィルタとどう対応させるか。
- 統合結果(composed)をRAGへ投入する際のインデックス項目と更新トリガ(抽出成功時/補正保存時)。
- 2D図面ファイルと3Dモデルファイルのペアリングを、本体の図面管理上どの単位で持つか。
