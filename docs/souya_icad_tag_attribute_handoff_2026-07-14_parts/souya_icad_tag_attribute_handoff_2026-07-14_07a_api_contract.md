# 創屋向け ICADタグ・属性連携項目表 - 7A. API/fixture契約

[7章目次へ戻る](souya_icad_tag_attribute_handoff_2026-07-14_07_api_fixture_contract.md)

# 創屋向け ICADタグ・属性連携項目表 - 7. API/fixture の最小契約案

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 7. API/fixture の最小契約案

PoC側では、創屋確認用の fixture 出力として以下を用意した。

```powershell
python backend\manage.py export_drawing_metadata_fixtures --output output\souya_handoff\drawing_metadata_fixture.json
python backend\manage.py export_drawing_metadata_fixtures --profile review-summary --output output\souya_handoff\drawing_metadata_fixture_review_summary.json
```

`full` profile の fixture には、図面詳細API相当の `detailApiPayload`、2D/3Dビューワー初期表示用の `viewerBootstrap`、RAG投入用の `ragPayload`、本番タグ・属性連携候補の `knowledgeSystemPayloadPreview` を同梱する。登録、変更、削除は行わない読み取り専用の受け渡しJSONである。`viewerBootstrap.metadata.knowledgeDetail` には、固定サンプルではなく、ICAD抽出snapshot、訂正候補、監査ログ、創屋連携payload候補から作った補助セクション用データを含める。

ただし `full` profile は raw/detail を含むため大きくなり、人がレビューで開くファイルとして扱わない。仕様確認、創屋説明、差分レビューでは `review-summary` profile を使い、完全fixtureは必要時だけローカル生成する。

2026-07-15 に通常DBの登録済み図面で実生成した。

- 確認用サマリ出力先: `output\souya_handoff\drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json`
- 出力件数: 11図面
- full profile 契約チェック: 11件すべてに `detailApiPayload`, `viewerBootstrap`, `ragPayload`, `knowledgeSystemPayloadPreview` が存在
- 追加payload横断確認: ローカルDB内の11件は古い登録データが多く、10件は対象別属性候補0件。実抽出入りの `9NK452WX90-00-LINER-A3-3D-01.icd` では部品向け属性候補2件を確認。抽出済みJSONの再投入が進むほど候補数が増える想定
- 実抽出入り代表: `9NK452WX90-00-LINER-A3-3D-01.icd`
  - `viewerBootstrap.availability.has2d=true`
  - `viewerBootstrap.availability.has3d=true`
  - `ragPayload.schemaVersion=drawing_metadata_rag_payload.v1`

抽出済みJSONをローカルDBへ再投入するため、`import_drawing_metadata_extracts` 管理コマンドを追加した。既存の保存serviceを通すため、`RegisteredDrawing`、2D/3D snapshot、latest job、audit log が揃う。ICADを再起動せず、共有済み抽出JSONから詳細画面/API/fixtureを再検証できる。

```powershell
python backend\manage.py import_drawing_metadata_extracts path\to\sample_2d.json path\to\sample_3d.json
```

同日に代表3図面の2D/3D抽出JSONを取り込み直し、fixtureを再生成した。

- 再生成後の出力件数: 14図面
- `knowledgeSystemPayloadPreview` 候補あり: 4図面
- 代表候補数:
  - `CAA5012-02430002P1R1.icd`: 図面 attrs=1/tags=3、製品 attrs=1、部品 attrs=2、プロジェクト attrs=1
  - `DFR-CM1-AA0305300011.icd`: 図面 attrs=2/tags=2、製品 attrs=1、部品 attrs=3/tags=1、プロジェクト attrs=1
  - `TR1D9K99027.icd`: 図面 attrs=2/tags=4、製品 attrs=1、部品 attrs=7/tags=2、プロジェクト attrs=1

さらに、共有済み抽出JSONをそのまま全部取り込まず、客先差と2D/3Dペアを優先して代表を選ぶ `scripts\build_icad_extract_import_manifest.py` を追加した。

```powershell
python scripts\build_icad_extract_import_manifest.py `
  --input-root output\live_extracts\shared_icad_probe_2026-07-14 `
  --input-root output\live_extracts\part_material_probe_2026-07-14 `
  --input-root output\live_extracts\mass_probe_2026-07-14 `
  --max-drawings 24 `
  --output output\souya_handoff\icad_extract_import_manifest_2026-07-15.json
```

manifestは112 JSONを確認し、24図面/43ファイルを選定した。選定後の分布は、2D/3Dペア19図面、3Dのみ5図面。客先ヒントは、ライズ5、ラップマスターウォルターズジャパン5、シブヤパッケージングシステム2、その他は SBY / NKS / ZCSET / DNPE / 宮本工業所 / 不二越などを1件ずつ含む。

manifest経由でローカルDBへ取り込み、fixtureを再生成した。ローカルDB上は35図面が登録済みだが、創屋へ渡すfixtureは実際に抽出snapshotがある図面だけを標準対象とする。抽出snapshotが無い10図面は、登録済みファイルの管理記録としては残すが、detail/viewer/RAG連携の実データ確認には使えないため除外した。

- 登録図面数: 35図面
- 創屋引き渡しfixture出力件数: 25図面
- 抽出snapshotなし除外: 10図面
- `knowledgeSystemPayloadPreview` 候補あり: 25図面
- 2D/3D両方あり: 20図面
- 契約検証: `output\souya_handoff\drawing_metadata_fixture_contract_validation_2026-07-15.json` で `valid=true`、issue 0件
- 検証内訳: 2D snapshot 20件、3D snapshot 25件、図面/製品・装置・ユニット/部品/プロジェクト各25件の読み取り専用payload
- 2D構造化セクション: 2D snapshot 20件すべてに `raw_2d_sections.v1` の6区画が揃う。契約検証スクリプトでも2D snapshotでは同セクションを必須チェックする
- 2D/3D照合: `reconciledAttributes` は全差分を保持する。`conflicts` は設計レビュー対象だけに絞り、内部品質・件数・抽出元差分は `diagnosticConflicts` へ分離する。2026-07-15 再生成fixtureではレビュー競合0件、診断差分93件。契約検証スクリプトでも診断専用キーが `conflicts` へ混入しないことをチェックする
- 代表候補数:
  - `03_20K03379P00_ｼｭｰﾄﾍﾞｰｽ(No.2FFS_XS).icd`: 図面 attrs=5/tags=2、製品 attrs=1、部品 attrs=5/tags=1、プロジェクト attrs=1
  - `217008-41J-3004.icd`: 図面 attrs=4/tags=2、製品 attrs=1、部品 attrs=7/tags=2、プロジェクト attrs=1
  - `474300AC219.icd`: 図面 attrs=5/tags=20、製品 attrs=1、部品 attrs=38/tags=20、プロジェクト attrs=1
  - `CAA5012-02434000K1R1.icd`: 図面 attrs=5/tags=9、製品 attrs=1、部品 attrs=27/tags=9、プロジェクト attrs=1

同日にローカルDjangoを `http://127.0.0.1:8001` で起動し、実HTTPでも確認した。なお、2026-07-16 時点ではユーザーが触る画面は `http://127.0.0.1:5173/` の2D・3Dビューワー統合フロントへ統一し、Django HTML は `/internal/drawing-metadata/` の内部確認画面へ退避している。

- `GET /internal/drawing-metadata/`: HTTP 200
- `GET /drawing-metadata/`: 現行通常導線では使用しない
- `GET /api/v1/drawing-metadata/registrations/`: 11件取得
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/`: `viewerBootstrap` あり
- `GET /api/v1/drawing-metadata/registrations/{drawingId}/rag-payload/`: `schemaVersion=drawing_metadata_rag_payload.v1`
- 末尾スラッシュあり/なしの両方をAPIルーティングで受ける。フロント実装差で404にならないようにするため。

提出済みの 2D/3D ビューワー側では、初期表示情報を `GET /api/v1/drawings/{drawingId}/bootstrap` で取得する契約になっている。こちらの detail API に含めている `viewerBootstrap` と同一形状で返せるよう、読み取り専用の互換APIを追加した。

- `GET /api/v1/drawings/{drawingId}/bootstrap`: 2D/3Dビューワー互換の `DrawingBootstrapResponse`
- `GET /api/v1/drawings/{drawingId}/bootstrap/`: 末尾スラッシュありも許容
- 返却項目: `drawingId`, `title`, `version`, `defaultMode`, `availability.has2d`, `availability.has3d`, `metadata.drawingNumber`, `metadata.drawingName`, `metadata.drawingType`, `metadata.paperSize`, `metadata.status`, `metadata.owner`, `metadata.designPurpose`, `metadata.tags`, `metadata.tagAttributes.targets[].tagEvidence`
- 方針: 本番データ登録は行わず、既存ビューワーが図面詳細から起動されたときの初期表示だけを支える。2D/3Dファイルオープン処理そのものは、創屋側の既存 viewer 連携口と接続する。

2026-07-15 にローカル詳細画面へ `創屋連携・viewer/RAG 受け渡し確認` 欄を追加した。初心者でも確認できるよう、詳細API、RAG投入payload API、タグレビュー画面へのリンク、viewer初期化情報、RAG事前フィルタ、RAGランキング信号、投入前レビューを表形式で表示する。

同欄へ `本番タグ・属性 payload プレビュー` を追加した。図面、製品・装置・ユニット、部品、プロジェクトの各対象について、既存受け口、タグAPI状態、タグ候補、タグ根拠、属性候補数、payloadキー、候補endpointを表示する。`attribute` / `attribute_option` は本番マスタIDが必要なため、プレビューでは `null` とし、`bindingStatus=needs_attribute_master_binding` として創屋側確認事項を明示する。

同じ検証用画面群の入口として、現行では `GET /internal/drawing-metadata/handoff/` を使う。これは本番ナレッジシステムへ組み込む完成UIではなく、こちら側で抽出・正規化・タグ生成・payload受け渡しを横断確認するためのローカル検証画面である。登録済み図面数、抽出済み図面数、2D/3D両方あり、payload候補あり、レビュー競合、診断差分を集計し、図面別に詳細画面、タグレビュー、viewer bootstrap API、RAG payload APIへ遷移できる。

- ローカル確認URL: `http://127.0.0.1:8001/internal/drawing-metadata/7d47aa93-de58-467d-a145-4a584cd6c52b/`
- 画面確認画像: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-metadata-handoff-viewport.png`
- DOM確認: `創屋連携・viewer/RAG 受け渡し確認`, `詳細API`, `RAG投入payload API`, `viewer 初期化情報`, `RAG 事前フィルタ`, `RAG ランキング信号`, `投入前レビュー`, `本番タグ・属性 payload プレビュー` が表示されることを確認

manifest取込後の代表図面として、2D/3D両方があり、かつpayload候補が多い `CAA5012-02434000K1R1.icd` をローカル詳細画面で見た目確認した。

- ローカル確認URL: `http://127.0.0.1:8001/internal/drawing-metadata/0e04246b-e8a2-4b46-a485-9312f6112d33/`
- 画面上部: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-top-caa5012.png`
- payloadプレビュー: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-payload-preview-caa5012.png`
- DOM/寸法確認: `output\knowledge_ui_screenshots_2026-07-15\local-drawing-detail-payload-preview-caa5012.metrics.json`
- 確認結果: 図面、製品・装置・ユニット、部品、プロジェクトの4対象が表示される。`登録・変更・削除は行わず` の注意文も表示される。payload表は横長の保存パス、endpoint、候補タグを扱うため、専用の横スクロール枠と折り返しを付けた。Chrome実画面ではpayloadセルの文字あふれ0件を確認した。
- 代表候補数: 図面 attrs=5/tags=9、製品 attrs=1、部品 attrs=27/tags=9、プロジェクト attrs=1。

