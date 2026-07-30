# CADタグ抽出・属性正規化・タグ付与 現行仕様

- 文書状態: **現行コード準拠の正本**
- 基準日: 2026-07-29
- 対象コード:
  - `src/IcadExtraction.*`
  - `backend/apps/drawing_metadata`
  - `integrations/2D_3D_CAD_VIEWR/frontend/src`
- スキーマバージョン: `1.0.0`
- 正規化ルールバージョン: `1.1.0`
- タグルールバージョン: `1.1.0`

この文書は、CADからの情報抽出、Djangoでの属性正規化、2D/3D照合、タグ付与、手動補正、レビュー、画面/API連携の現行仕様をまとめた正本である。調査時点の事実、旧計画、実データ監査記録は別文書に残すが、現在の挙動を判断するときは本書とコードを優先する。

関連文書の位置づけは [`tag_extraction_documentation_index_2026-07-29.md`](tag_extraction_documentation_index_2026-07-29.md) を参照する。

## 1. 正本と責務境界

| 層 | コード上の正本 | 責務 |
|---|---|---|
| C#契約 | `src/IcadExtraction.Contracts/Models.cs` | raw抽出JSON、検出結果、印刷確認結果の型 |
| ICADネイティブ抽出 | `src/IcadExtraction.SxNet/Icad2DExtractor.cs`、`Icad3DExtractor.cs` | SXNETから2D/3Dの事実を型付きで取得 |
| Windows実行入口 | `src/IcadExtraction.Runner/Program.cs`、`WindowsExtractionAgent.cs` | CLI、ICAD起動、agent常駐、HTTP連携 |
| 保存モデル | `backend/apps/drawing_metadata/models.py` | 登録図面、ジョブ、snapshot、監査ログ、辞書、agent heartbeat |
| 正規化 | `services/normalization.py` | raw抽出を共通canonical属性へ変換 |
| 2D/3D合成 | `services/composition.py` | mode別snapshotの照合、競合記録、最終属性・タグの生成 |
| タグ生成 | `services/tag_builder.py` | canonical属性から検索用タグを生成 |
| 辞書 | `services/dictionaries.py`、`seed_dictionaries.py` | DB辞書優先、初期seed辞書 |
| 手動補正 | `services/overrides.py`、`persistence.py` | 属性上書き、タグ追加・削除、再抽出後の再適用 |
| 非同期処理 | `tasks/extraction_tasks.py` | 抽出結果の正規化、タグ生成、保存、完了処理 |
| API | `api/urls.py`、`api/views.py`、`api/agent_views.py` | 登録、抽出、補正、レビュー、辞書、agent、viewer/RAG payload |
| 統合フロント | `integrations/2D_3D_CAD_VIEWR/frontend/src` | 抽出管理、レビュー、辞書管理、製品・部品表示 |

本リポジトリのDjango appは、創屋側の本番ナレッジシステムへ後で移植しやすい独立モジュールである。ローカルDB、fixture、画面は連携仕様の検証用であり、創屋側本番DBの保存先やAPI名を確定したものではない。

## 2. 現行処理フロー

1. `RegisteredDrawing`へICAD、STEP、DXFを登録する。
2. 形式に応じた抽出modeで`DrawingMetadataExtractionJob`を起票する。
3. ICADはWindows agentまたはWindows上のworkerがC# Runnerを実行する。STEP/DXFはDjango側generic workerが処理する。
4. C#またはgeneric抽出器が、意味付け前のraw JSONを返す。
5. `normalize_raw_extract()`が共通canonical属性へ変換する。
6. 名称・図枠候補は、ICAD原文、印刷枠、ビュー、レイヤー、文字座標、明示ラベル、タグ辞書だけで分類する。Geminiを含む外部AIは使用しない。
7. `build_derived_tags()`が検索価値のある確定属性だけをタグ化する。
8. `save_extraction_snapshot()`がraw、canonical、タグを同一処理で保存し、保存済み手動補正を再適用する。
9. `compose_drawing_metadata()`が2D/3Dを照合し、採用値、競合、診断差分、最終タグを返す。
10. viewer、製品・部品画面、fixture、RAG payloadは合成結果を参照する。

不正な入力、未対応形式、抽出器失敗、agent所有権不一致、パス制約違反は失敗として終了する。取得できない値を推測や既定値で埋めない。

## 3. 対応形式と抽出実行場所

`backend/apps/drawing_metadata/services/source_formats.py`の定義を正とする。

| 拡張子 | `source_format` | 既定mode | 抽出器 | 実行場所 |
|---|---|---|---|---|
| `.icd` | `icad` | `2d`と`3d` | SXNET/C# | Windows |
| `.step`、`.stp` | `step` | `3d` | generic CAD抽出器 | Django側worker |
| `.dxf` | `dxf` | `2d` | generic CAD抽出器 | Django側worker |

ICADは2D/3Dを別snapshotとして保持する。STEP/DXFは現行ではテキスト・構造候補を読む汎用抽出であり、ICADネイティブ抽出と同じ情報量を保証しない。

## 4. データの4層

| 層 | 保存先 | 内容 |
|---|---|---|
| raw | `DrawingMetadataSnapshot.raw_extract_json` | 抽出器が返した事実。意味付け前の監査証跡 |
| canonical | `canonical_attributes_json` | 形式差を吸収した属性。未抽出は`None`または空配列 |
| derived tags | `derived_tags_json` | canonical属性から規則で生成した検索用タグ |
| manual overrides | `manual_overrides_json` | 利用者が確定した属性上書き、タグ追加、タグ削除 |

最終表示・連携値はsnapshot単体ではなく、原則として`compose_drawing_metadata()`の`canonicalAttributes`、`derivedTags`、`conflicts`、`diagnosticConflicts`、`reconciledAttributes`を使用する。

## 5. Django保存モデル

現行モデルは次の6つである。

| モデル | 主な役割 |
|---|---|
| `RegisteredDrawing` | 1 CADファイルの登録情報と原本識別 |
| `DrawingMetadataExtractionJob` | mode別の非同期抽出ジョブ、lease、診断、バージョン |
| `DrawingMetadataAgentHeartbeat` | Windows agentの最終稼働状態 |
| `DrawingMetadataSnapshot` | 1図面・1modeのraw/canonical/タグ/補正/レビュー |
| `DrawingMetadataAuditLog` | 抽出、再起票、補正、レビューの変更履歴 |
| `TagDictionaryEntry` | タグ・属性正規化辞書のDB正本 |

最新マイグレーションは`0008_drawingmetadataagentheartbeat.py`である。`DrawingMetadataSnapshot`は`drawing + extraction_mode`で一意にする。

## 6. raw抽出の原則

### 6.1 共通エンベロープ

C#契約バージョンは`1.0.0`である。エンベロープは少なくとも入力パス、`source_file`、`source_format`、`source_kind`、抽出条件、抽出器名・版、経過時間、warning、`raw_extract`を持つ。

Windows agentのHTTP契約とC#入出力の詳細は [`windows_extraction_agent_api_design_2026-07-29.md`](windows_extraction_agent_api_design_2026-07-29.md) を正本とする。

### 6.2 3D

3D rawは、モデル情報、トップパーツ、パーツツリー、外部参照、付加情報、材質、質量特性、viewer asset、診断を保持する。

- `top_part.name`は識別子や図番相当になり得るため、製品名・装置名・ユニット名・部品名へ無条件に流用しない。
- パーツは内部パーツと外部参照パーツを分離する。
- 外部パーツの名称、材質、参照先、付加情報は検索・構成証跡として保持できるが、本体の正式名称・正式材質へ昇格させない。
- 部品数の業務表示は外部参照パーツ基準とし、内部パーツ数は診断・参考属性として扱う。

### 6.3 2D

2D rawは、ビュー、印刷枠、レイヤー、文字、寸法、幾何プリミティブ、溶接注記、バルーン、公差、2D参照部品を保持する。

- 座標、ビュー、レイヤー、印刷枠内外判定を監査証跡として保持する。
- 図枠ラベルと値の自動対応は、同一文字要素、同一要素内の次行、または名称欄で同一ビュー・同一レイヤー・近接整列を満たす限定候補にする。
- 別要素間の汎用座標ペアリングは実装しない。
- 印刷枠があり、枠内外を判定できる要素が1件以上ある場合は枠内を優先する。全文字が`unknown`の場合は、判定材料なしとして文字を全件捨てない。
- 未知の実型名でも非空の`txt`を持つ文字要素は救済する。

## 7. canonical属性

全形式で同じ空枠を作り、取得できた値だけを埋める。完全なキー一覧は`normalize_raw_extract()`冒頭の`canonical`辞書を正とする。

### 7.1 識別・業務分類

- `drawing_number`、`drawing_name`
- `part_name`、`product_name`、`equipment_name`、`unit_name`
- `revision`
- `customer_name`、`project_name`、`equipment_category`
- `document_kind`、`module_name`

名称と識別子は分離する。`SFF-424 L=1572`のような型式・寸法トークンだけの値、`型式`のような見出し、ファイル名由来の識別子は名称として確定しない。`★`、`※`等の先頭注記記号はraw原文に残し、表示名称からだけ除去する。

図面番号は、図枠明示値、図面文字とファイル名の一致候補、ファイル名の順で決める。部品の`part_number`は現行表示契約では図面番号と整合させる。

### 7.2 3D構成・材質・質量

- `internal_part_*`と`external_part_*`を分離する。
- `part_material_candidates`は本体側候補、`external_part_material_candidates`は外部側候補とする。
- `internal_part_material_keywords`と`external_part_material_keywords`を分離する。
- `mass_value`、`weight_value`、`volume_value`、`area_value`、`density_value`
- `center_of_gravity`、`global_moment`、`gravity_moment`、`main_moment`
- `inertia_moment_candidates`

材質は正式、未解決、除外を分ける。未解決材質を正式材質タグへ昇格させない。

### 7.3 2D図枠・製作指示

- `title_block_candidates`、`title_block_fields`
- `revision_note_candidates`
- `dimension_*`
- `geometric_tolerance_count`
- `weld_*`
- `surface_treatment_tokens`
- `heat_treatment_keywords`、`hardness_spec_values`
- `scale_candidates`、`scale`
- `raw_2d_sections`

尺度は`S=1:6`と`1:6`を候補化し、異なる候補が1種類だけの場合に確定する。テーパ等の比率表記と競合する場合は確定しない。

## 8. 自動生成するタグ

`services/tag_builder.py`の`build_derived_tags()`を正とする。現行タグは次のとおりである。

| 条件 | タグ形式 | 信頼度 |
|---|---|---|
| 客先確定 | `客先:{customer_name}` | high |
| 案件確定 | `案件:{project_name}` | high |
| 装置カテゴリ確定 | `装置:{equipment_category}` | high |
| 寸法あり | `寸法あり` | high |
| 寸法公差あり | `寸法公差あり` | high |
| 幾何公差あり | `幾何公差あり` | high |
| 溶接指示あり | `溶接指示あり` | high |
| すみ肉または全周を明示分類 | `溶接:すみ肉`、`溶接:全周` | medium |
| メーカー辞書一致 | `メーカー:{値}` | medium |
| 正式材質 | `材質:{値}` | medium |
| 表面処理 | `表面処理:{値}` | medium |
| 塗装指示 | `塗装:{値}` | medium |
| 熱処理 | `熱処理:{値}` | medium |
| HRC/HV硬度尺度 | `硬度:HRC`、`硬度:HV` | medium |
| PRFX候補 | `PRFX:{値}` | medium |
| ユニット番号候補 | `ユニット:{値}` | medium |
| SES明示 | `規格:SES` | medium |

タグpayloadは`tag`、`source`、`evidence`、`confidence`、`reason`、`manual_flag`、`tag_rule_version`を持つ。

次の情報は現行コードでは自動タグ化しない。

- 図面名、部品名、製品名、装置名、ユニット名
- 図番、改訂、尺度、用紙サイズ
- 件数そのもの
- 形状候補だけで用途を断定した穴、長穴、断面、表面粗さ
- 未解決材質
- 2D/3D競合中の属性

## 9. タグ辞書

DBの`TagDictionaryEntry`を正本とし、種別単位で有効なDB行が0件の場合はコード内seedを使用する。

| kind | 用途 |
|---|---|
| `customer` | 客先 |
| `equipment_category` | 装置カテゴリ |
| `project` | 案件 |
| `maker` | メーカー |
| `spec` | 規格 |
| `heat_treatment` | 熱処理 |
| `part_name` | 部品名候補 |

各行は`canonical_value`、`aliases_json`、`priority`、`enabled`、`note`を持つ。小さい`priority`を優先する。

初期投入:

```powershell
Set-Location backend
.venv\Scripts\python.exe manage.py seed_tag_dictionaries
```

更新後の既存snapshot反映:

```powershell
.venv\Scripts\python.exe manage.py renormalize_drawing_metadata_snapshots
```

`raw_extract_json`を省略した検証用seed DBでは再正規化を実行しない。raw由来の属性・タグを再構築できず、値が消えるためである。

## 10. 2D/3D照合

`services/composition.py`の規則を正とする。

1. 3D側手動補正
2. 2D側手動補正
3. 図面識別属性は2D明示値
4. その他のscalarは原則3D
5. 配列は重複排除して統合
6. 辞書は2Dを入れた後に3D同名キーで上書き
7. 図面特徴件数は2D/3Dの大きい値

図面識別属性は`drawing_number`、`drawing_name`、`part_name`、`product_name`、`equipment_name`、`unit_name`である。

レビュー対象の競合は`conflicts`、内部件数や診断差は`diagnosticConflicts`へ分離する。レビュー対象競合の属性からは自動タグを作らない。

## 11. 手動補正と再抽出

### 11.1 属性

`manual_overrides_json.canonicalAttributes`はキー単位でマージする。新しい補正payloadでマップ全体を置換しない。値に`null`を指定したキーだけ補正記録を解除する。

### 11.2 タグ

最終タグは次の式である。

```text
自動タグ - removed + added
```

追加と削除は累積集合として保持し、追加後の削除、削除後の再追加は相殺する。再抽出、再正規化、タグ再生成後も手動タグと手動削除を維持する。

### 11.3 レビュー

snapshotの状態は`pending`、`confirmed`、`needs_correction`である。抽出または補正後は`pending`へ戻し、確定操作で`reviewed_at`と`reviewed_by`を保存する。

## 12. API

すべて`/api/v1/`配下である。末尾スラッシュあり・なしの両方を持つ主要APIもある。

### 登録・抽出・補正

- `GET/POST /api/v1/drawing-metadata/registrations`
- `POST /api/v1/drawing-metadata/registrations/upload`
- `GET /api/v1/drawing-metadata/registrations/{drawingId}`
- `POST /api/v1/drawing-metadata/registrations/{drawingId}/extract`
- `PATCH /api/v1/drawing-metadata/registrations/{drawingId}/overrides`
- `PATCH /api/v1/drawing-metadata/registrations/{drawingId}/review`
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/rag-payload`
- `GET /api/v1/drawing-metadata/jobs/{jobId}`

### 辞書・管理

- `GET/POST /api/v1/drawing-metadata/tag-dictionaries`
- `PATCH/DELETE /api/v1/drawing-metadata/tag-dictionaries/{entryId}`
- `GET /api/v1/drawing-metadata/settings/tag-automation`
- `GET /api/v1/drawing-metadata/handoff-summary`

### 製品・部品・viewer

- `GET /api/v1/knowledge-entities`
- `GET /api/v1/knowledge-entities/{entityId}`
- `GET /api/v1/drawing-options`
- `GET /api/v1/drawings/{drawingId}/bootstrap`
- `POST /api/v1/drawings/{drawingId}/viewer2d/open`
- `POST /api/v1/drawings/{drawingId}/viewer3d/open`

### Windows agent

- `POST /api/v1/drawing-metadata/agent/jobs/claim`
- `POST /api/v1/drawing-metadata/agent/heartbeat`
- `GET /api/v1/drawing-metadata/agent/jobs/{jobId}/source`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/assets`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/complete`
- `POST /api/v1/drawing-metadata/agent/jobs/{jobId}/fail`

## 13. UI

利用者が触る統合フロントは通常`http://127.0.0.1:5173/`である。

- `IcadExtractionReviewPage.tsx`: 登録、抽出、再抽出、タグ候補、手動補正、レビュー
- `TagAutomationSettingsPage.tsx`: 自動化設定、運用状態、タグ辞書CRUD
- `IcadEntityPages.tsx`: 製品・装置・ユニット、部品、属性、タグ、根拠、照合結果
- 2D/3D viewer詳細: タグ・属性対象、本体材質、外部パーツ名称・材質を分離表示

Django HTMLは開発・横断確認用であり、`/internal/drawing-metadata/`へ退避している。Djangoのルート`/`は`api-only` JSONを返す。

## 14. 運用コマンド

### worker

```powershell
Set-Location backend
.venv\Scripts\python.exe manage.py process_drawing_metadata_jobs --loop --mode all
```

Docker側でgeneric CADだけを処理する場合は`--extractor-scope generic`、Windows直結でSXNETジョブを処理する場合は`--extractor-scope sxnet`を指定できる。Docker/LinuxとWindows agentを分離する本番構成では、ICADジョブはWindows agentがclaimする。

### 再計算

```powershell
.venv\Scripts\python.exe manage.py renormalize_drawing_metadata_snapshots
.venv\Scripts\python.exe manage.py rebuild_drawing_metadata_tags
```

- 正規化規則または辞書を変えた場合は`renormalize_drawing_metadata_snapshots`
- タグ生成規則だけを変えた場合は`rebuild_drawing_metadata_tags`

いずれも手動属性、手動タグ、手動削除を維持する。

## 15. RAGと創屋本番への境界

RAG payloadのスキーマは`drawing_metadata_rag_payload.v1`である。`preFilters`、`rankingSignals`、`searchTextChunks`、`reconciliation`、`sourceAttributes`を返す。

本リポジトリで確定しているのは、抽出・正規化・タグ候補・根拠・レビュー状態の連携payloadまでである。次は創屋側確認が必要である。

- 図面、製品、部品、プロジェクトの本番属性保存API
- 製品・部品・プロジェクトへのタグ保存口
- 属性マスタID、材質マスタIDの解決方法
- 手動補正履歴の本番保存先
- RAGインデックスのフィールド名、更新単位、更新タイミング

確認が終わるまで、ローカル画面やfixtureの保存を創屋本番DBへの保存と表現しない。

## 16. 未実装・実機確認中

実装済みと未確認を混同しない。

- 幾何公差は存在タグまで実装済み。SXNETの種別・値を使う`幾何公差:{種別}`は実機確認後。
- 溶接は存在、すみ肉、全周まで実装済み。開先、現場等の記号プロパティ分類は未実装。
- PRFXは明示ラベル・付加情報候補を使う。客先別の実フィールド名と値形式は継続確認。
- 図枠の別文字要素間汎用座標ペアリングは実装しない。
- 熱処理・硬度、尺度、外部参照部品数は実装済みだが、客先横断実例で取りこぼしを継続確認する。
- 創屋本番DB/APIへの書き込みは未接続。

### 16.1 廃止前の外部AI履歴

2026-07-29以前に保存されたsnapshot、ジョブwarning、監査JSON、履歴文書は、当時の検証証跡として更新・削除しない。現行処理では次の境界を守る。

- UI、API、2D/3D合成、RAG payloadへ`llm_*`互換項目を返さない。
- `title_block_llm_*`warningは現行API・内部画面・fixture集計から除外する。
- 手動補正APIは廃止済み外部AI互換項目を受け付けない。
- 既存manual overrideに旧項目があっても、再抽出・再正規化時にcanonical属性へ再適用しない。
- DB上の履歴値そのものは変更せず、廃止前の監査JSON・履歴文書も保持する。

## 17. 変更時の検証

タグ抽出・付与のコードまたは本書を変更した場合は、少なくとも次を確認する。

```powershell
Set-Location backend
.venv\Scripts\python.exe -m pytest apps\drawing_metadata\tests
.venv\Scripts\python.exe manage.py check
Set-Location ..
python scripts\audit_tag_documentation.py
python scripts\audit_retired_ai_database_history.py
python scripts\audit_beginner_source_comments.py
dotnet test IcadExtraction.sln
```

フロント変更を伴う場合は、`integrations/2D_3D_CAD_VIEWR/frontend`で対象Vitestとproduction buildも実行する。

### 17.1 2026-07-29確認結果

- `python scripts\audit_tag_documentation.py`: エラー0、警告0
- Django `pytest`: 175件成功
- Django `manage.py check`: 問題なし
- `.NET solution`: 41件成功
- Vitest: 62件成功
- frontend production build: 成功。500 kB超chunkの既知warningあり
- `python scripts\audit_beginner_source_comments.py`: 269ファイル合格、要補強0

### 17.2 2026-07-30 外部AI互換項目削除後の確認結果

- 現行runtime検索: `llm_*`、`title_block_llm_*`、旧AI列の一致0件
- Django `pytest`: 182件成功
- Django `manage.py check`: 問題なし
- Vitest: 63件成功
- frontend production build: 成功。500 kB超chunkの既知warningあり
- `python scripts\audit_tag_documentation.py`: エラー0、警告0
- `python scripts\audit_beginner_source_comments.py`: 270ファイル合格、要補強0
- 実DB read-only監査: 廃止前のジョブwarning 13件を保持。現行API・内部画面では非表示
