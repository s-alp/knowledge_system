# 創屋向け ICADタグ・属性連携項目表 - 10. 共有39件の最終受け渡し状況

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 10. 共有39件の最終受け渡し状況

2026-07-15 に、ユーザーから共有された客先横断39件を固定manifestとして再整理し、ローカルDB、fixture、製品・装置・ユニット／部品画面へ反映した。本番ナレッジシステムへの登録、変更、削除は行っていない。

### 10.1 固定manifestとfixture

- manifest: `output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json`
- レビューサマリ: `output\souya_handoff\drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json`
- レビューサマリ検証: `output\souya_handoff\drawing_metadata_fixture_all_shared_review_summary_validation_2026-07-17.json`
- サンプル完了台帳: `output\souya_handoff\icad_shared_sample_completion_2026-07-15.json`
- 対象: 39図面、抽出JSON 78件（各図面に2D/3D各1件）
- 3D snapshot: 39/39
- 2D snapshot: 39/39
- レビューサマリ検証: `valid=true`、issue 0件、255.5KB
- 読み取り専用payload: 図面、製品・装置・ユニット、部品、プロジェクトを各39件
- 属性候補数: 図面158、部品363、製品・装置・ユニット43、プロジェクト43（合計607）
- タグ候補数: 対象別タグ227件。内訳は `scripts\audit_knowledge_payload_attribute_quality.py` と `output\souya_handoff\icad_handoff_numeric_consistency_audit_current.json` を正とする

### 10.2 3D構成からの実エンティティ生成

3D構成ノードに `nodeId`、`parentNodeId`、`depth`、`childCount`、`entityKind` を付ける。ただし、子を持つだけではサブアセンブリとは判定しない。`subassembly` は `is_external`、`ref_model_name`、`ref_model_path` など外部参照の根拠がある中間ノード、または手動確定がある場合だけ扱う。末端ノードは内部構成診断上の部品として集計するが、ナレッジシステムへの登録単位は1 ICD = 1件である。

| API | 用途 |
| --- | --- |
| `GET /api/v1/knowledge-entities?target=product` | アセンブリ／サブアセンブリ一覧 |
| `GET /api/v1/knowledge-entities?target=part` | 末端部品一覧 |
| `GET /api/v1/knowledge-entities/{entityId}` | 属性、タグ、根拠、競合、関連情報、レビュー状態を含む詳細 |

エンティティIDは図面IDと3DノードIDから安定生成する。同名部品が複数箇所に存在しても、階層位置の異なるノードとして扱う。

### 10.3 レビューと確定状態

抽出候補は表示しただけで確定扱いにしない。2D/3D snapshot単位に `pending`、`confirmed`、`needs_correction` を保持し、再抽出または手動上書き時は `pending` に戻す。レビュー操作はローカル監査ログへ記録する。

| API | 用途 |
| --- | --- |
| `PATCH /api/v1/drawing-metadata/registrations/{drawingId}/review` | 2Dまたは3D候補を確定／要手直しへ変更 |
| `GET /api/v1/drawing-metadata/settings/tag-automation` | AI、抽出対象、採用ルールの管理設定を取得 |
| `PUT /api/v1/drawing-metadata/settings/tag-automation` | ローカル管理設定を更新 |

Gemini APIキーは設定値そのものを返さず、設定済みかどうかだけを返す。本番DB向けendpointは実装せず、創屋へはfixtureとAPI契約を渡す。

### 10.4 2D再抽出の状態と理由

39件を同一条件で再抽出試行した。途中で終了コード1が連続した際は、Runnerの例外チェーンとstack traceを出すようにして、`SxFileModel` 生成時の `sxnet.SxException: コマンド実行中の為処理できません` まで原因を特定した。SXNET HTMLの `SxSys.cancel()` と `SxSys.getCommand()` を確認し、診断用の `cancel` / `clear-command` コマンドも追加したが、孤立したコマンド状態は解消しなかった。

ICADへ通常の終了要求を送り、旧V8L2形式からV8L3形式への保存確認には「いいえ」を選んで原本を変更せず終了した。その後クリーンに起動し直して全39件を再実行試行した結果は次のとおりである。強制終了、原本保存、創屋本番DB操作は行っていない。

抽出器の自動起動leaseも同じ安全終了へ統一した。通常終了できない場合に `Process.Kill()` していた処理は廃止し、保存確認の「いいえ」を特定できた場合だけ押す。安全終了を完了できない場合は、強制終了せずICADを起動状態のまま残してエラーを出す。明示的な保守確認には次のコマンドを使用できる。

```powershell
src\IcadExtraction.Runner\bin\Debug\net48\IcadExtraction.Runner.exe `
  shutdown-icad `
  --timeout-seconds 20
```

- 最新2D抽出成功: 39/39
- 2D要素あり: 31件
- 2Dコンテナ／ビュー／レイヤーはあるが検査可能な2D要素なし: 8件
- 最新3D抽出利用可能: 39/39
- 共有元ファイル欠落: 0件
- 未解決: 0件

「2D要素なし」8件は抽出失敗ではない。VS/ビューとレイヤー情報は取得できた一方、文字・寸法・図形primitive・印刷枠が0件だったため、内容を捏造せずその状態を記録している。

全39件の2Dカバレッジは `output\souya_handoff\icad_2d_extraction_coverage_all_shared_2026-07-15.json` に保存した。全ビュー210、印刷枠32、レイヤー9,945、検査可能要素30,105、文字1,752、寸法2,404、図形primitive 25,903を取得した。要素のビュー未所属は0件、印刷枠内5,088、枠外23,849、判定不明1,168である。判定不明とレイヤー未所属は証拠として保持し、自動タグ採用では印刷枠内を優先する。

当初の参照先で見つからなかった `36555211A01.icd`、`32791729A01.icd`、`18T5-10BF(8).icd` は、同じ共有案件内または同じ作業フォルダ配下の移動後パスを特定した。`18T5-10BF(8).icd` は `J:\不二越5\260703_次期円筒研削盤開発(竹中様)\作業\OLD\18T5-10BF(8).icd` を正としてmanifestとローカルDBの保存パスを更新済みである。現時点で原本未アクセスとして残るファイルは0件である。

移動後パスの再紐付けには、同名図面がローカルDBに1件だけ存在する場合に限って使える明示オプションを追加した。同名図面が複数ある場合は処理を中断し、推測で付け替えない。

```powershell
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --filename 32791729A01.icd `
  --filename 36555211A01.icd `
  --rebind-moved-source
```

全件再取込時は、manifestの2D/3Dを分けて再現できる。移動元再紐付けは同名図面が一意の場合だけ許可し、曖昧なら中断する。

```powershell
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --manifest-mode 2d
python backend\manage.py import_drawing_metadata_extracts `
  --manifest output\souya_handoff\icad_extract_import_manifest_all_shared_2026-07-15.json `
  --manifest-mode 3d
```

### 10.5 創屋との責任境界

| 領域 | こちら | 創屋 |
| --- | --- | --- |
| ICAD 2D/3D/パーツ付加情報抽出 | 実装・検証 | 対象外 |
| 正規化、照合、候補生成、根拠・競合・信頼度 | 実装・fixture提供 | 受入確認 |
| 図面管理の抽出・レビュー導線 | ローカル統合版を提供 | 本番ナレッジシステムへ移植 |
| 図面／製品・装置・ユニット／部品への表示 | ローカル統合版とAPI契約を提供 | 本番UI・本番マスタIDへ接続 |
| 本番DB登録・更新・削除 | 実施しない | 創屋が仕様合意後に実装 |
| 本番画面・フロント資産確認 | 読み取り専用のみ | 変更管理 |
