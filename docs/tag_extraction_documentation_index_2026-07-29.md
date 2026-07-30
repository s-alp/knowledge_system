# タグ抽出・付与関連ドキュメント索引

- 文書状態: **現行索引**
- 基準日: 2026-07-30
- 現行仕様の正本: [`tag_extraction_and_assignment_current_spec_2026-07-29.md`](tag_extraction_and_assignment_current_spec_2026-07-29.md)

## 1. 読む順序

1. 現行全体仕様: `tag_extraction_and_assignment_current_spec_2026-07-29.md`
2. 創屋へ切り出す最小パッケージ: `souya_tag_extraction_minimal_handoff_2026-07-30.md`
3. 独立Python処理結果・canonical・タグpayload: `extraction_result_schema_2026-05-28.md`
4. Windows agentとC#入出力: `windows_extraction_agent_api_design_2026-07-29.md`
5. 創屋向け抽出元カタログ: `cad_tag_extraction_sources_for_souya_2026-07-28.md`
6. 取得可否と未確認事項: `icad_2d_3d_extraction_capability_matrix_2026-07-14.md`、`windows_confirmation_items_2026-07-17.md`
7. Cloud検証へ渡す場合: `../handoff/claude_cloud/README.md`、`VALIDATION_CHECKLIST.md`、`PROMPT_FOR_CLAUDE.md`
8. 履歴や監査結果が必要な場合だけ、調査・計画・handoff snapshotを読む

## 2. 文書分類

### 2.1 現行の正本

| 文書 | 正本範囲 |
|---|---|
| `docs/tag_extraction_and_assignment_current_spec_2026-07-29.md` | 抽出からタグ付与、補正、API、UI、運用までの全体 |
| `docs/souya_tag_extraction_minimal_handoff_2026-07-30.md` | 創屋へ渡す最小ソース、Docker、辞書、Schema、テスト、対象外範囲 |
| `docs/extraction_result_schema_2026-05-28.md` | 独立Python処理結果、Django保存、canonical属性、derived tags、manual overrides |
| `docs/windows_extraction_agent_api_design_2026-07-29.md` | Windows agent HTTP、C# raw JSON、起動設定 |
| `docs/cad_tag_extraction_sources_for_souya_2026-07-28.md` | 創屋向けに渡す抽出元・具体例・供給範囲 |
| `docs/icad_dxf_step_standalone_conversion_guide_2026-07-29.md` | Django非依存のICAD→DXF/STEP変換 |

### 2.2 現行の補足資料

| 文書 | 用途 | 注意 |
|---|---|---|
| `docs/icad_2d_3d_extraction_capability_matrix_2026-07-14.md` | SXNET根拠と取得可否 | 実装状態は更新日を確認 |
| `docs/icad_tag_selection_and_viewer_ui_spec_2026-07-15.md` | タグ選定とviewer表示 | API/画面の全体正本ではない |
| `docs/icad_entity_operations_and_quality_handoff_2026-07-16.md` | 登録単位、分類、品質、移植境界 | 共有39件を基準にした補足 |
| `docs/windows_confirmation_items_2026-07-17.md` | Windows実機でしか確定できない項目 | 実装済みと要確認を分離 |
| `docs/drawing_entity_name_extraction_investigation_2026-07-29.md` | 名称未抽出の原因と実装結果 | 調査・再監査記録 |

### 2.3 現行のCloud検証パッケージ

| 文書 | 用途 | 制約 |
|---|---|---|
| `handoff/claude_cloud/README.md` | seed DBと監査JSONを使うCloud検証手順 | ICAD/SXNET実抽出は対象外 |
| `handoff/claude_cloud/VALIDATION_CHECKLIST.md` | UI、データ、API、禁止事項の確認 | 創屋本番DBへ書き込まない |
| `handoff/claude_cloud/PROMPT_FOR_CLAUDE.md` | Cloud Claude Codeへ渡す依頼文 | 外部AI APIを追加・利用しない |

このパッケージの`manifest.json`、`sql/`、`data/`は文書の説明対象となる検証資材である。seed SQLはraw抽出を省略した固定データであり、正規化再実行の入力には使わない。

### 2.4 履歴として残す設計・調査資料

次の文書は設計判断の経緯を残すために保持する。現在の実装状態やコマンドを判断する正本にはしない。

| 文書 | 位置づけ |
|---|---|
| `docs/icad_tag_attribute_investigation_2026-05-26.md` | 実装前の初期調査 |
| `docs/icad_tag_attribute_design_plan_2026-05-26.md` | 初期設計計画 |
| `docs/icad_tag_attribute_implementation_backlog_2026-05-26.md` | 初期バックログ |
| `docs/icad_csharp_python_architecture_2026-05-27.md` | C#/Python分担の設計理由 |
| `docs/django_integration_plan_2026-05-28.md` | Django統合の初期計画 |
| `docs/tag_attribute_management_ui_plan_2026-05-28.md` | 管理UIの初期計画 |
| `docs/icad_extraction_poc_setup_2026-05-28.md` | 初期PoCセットアップ |
| `docs/icad_tag_attribute_report_2026-05-26.html` | 2026-05-26時点の説明用報告 |
| `docs/icad_cad_tag_attribute_redesign_2026-07-14.md` | 7月再設計の判断記録 |

### 2.5 検証時点を固定したsnapshot

| 文書 | 固定時点 |
|---|---|
| `docs/icad_shared_sample_extraction_findings_2026-07-14.md` | 共有23件の初期抽出 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14.md` | 創屋向けhandoff入口 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/*` | 2026-07-14～17の契約案・検証ログ・共有39件状態 |

handoff分冊は、当時の実測件数、URL、fixture、確認事項を再現する記録である。現行コードのモデル、タグ規則、agent APIを判断するときは正本文書を優先する。

### 2.6 廃止・周辺資料

| 文書 | 位置づけ |
|---|---|
| `docs/cad_tag_extraction_sources_for_souya_2026-07-23.md` | 2026-07-28統合版により廃止。STEP/DXF経路の履歴 |
| `docs/PDMナレッジシステム見積調査まとめ_2026-04-27.md` | 見積・責任分界の周辺資料。タグ仕様の正本ではない |
| `docs/RAGチャット改善確認_2026-05-20.md` | RAG挙動の検証記録。抽出・タグ実装仕様の正本ではない |

## 3. handoff分冊一覧

`docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/`の全ファイルを対象に確認した。

| 分冊 | 内容 |
|---|---|
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_00_scope.md` | 前提と読み方 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_01_production_screen_check.md` | 創屋本番画面の確認結果 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_02_data_unit.md` | 提供データ単位 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_03_drawing_items.md` | 図面連携項目 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_04_project_items.md` | プロジェクト連携項目 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_05_product_unit_items.md` | 製品・装置・ユニット連携項目 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_06_part_items.md` | 部品連携項目 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_07_api_fixture_contract.md` | 7章入口 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_07a_api_contract.md` | API/fixture契約案 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_07b_verification_log.md` | 検証ログ |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_08_souya_questions.md` | 創屋への確認事項 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_09_operation_handover_items.md` | 運用・移植確認 |
| `docs/souya_icad_tag_attribute_handoff_2026-07-14_parts/souya_icad_tag_attribute_handoff_2026-07-14_10_shared_39_status.md` | 共有39件の固定状態 |

## 4. コードから文書への追跡表

| 仕様 | コード | 主文書 |
|---|---|---|
| C# raw JSON | `src/IcadExtraction.Contracts/Models.cs` | Windows agent仕様、抽出結果スキーマ |
| C#/Python境界Schema | `schemas/tag_extraction/*.schema.json` | 最小handoff、Windows agent仕様、抽出結果スキーマ |
| 2D抽出 | `src/IcadExtraction.SxNet/Icad2DExtractor.cs` | 能力マトリクス、現行仕様 |
| 3D抽出 | `src/IcadExtraction.SxNet/Icad3DExtractor.cs` | 能力マトリクス、現行仕様 |
| agent | `src/IcadExtraction.Runner/WindowsExtractionAgent.cs` | Windows agent仕様 |
| 独立処理入口 | `backend/icad_tag_extraction/pipeline.py` | 現行仕様、最小handoff、抽出結果スキーマ |
| 独立辞書 | `backend/icad_tag_extraction/dictionary_provider.py`、`seed_dictionaries.py` | 現行仕様、最小handoff |
| DBモデル | `backend/apps/drawing_metadata/models.py` | 現行仕様、Django統合履歴 |
| canonical | `backend/icad_tag_extraction/normalization.py` | 抽出結果スキーマ、現行仕様 |
| 2D/3D照合 | `services/composition.py` | 現行仕様、viewer UI仕様 |
| 派生タグ | `backend/icad_tag_extraction/tag_builder.py` | 現行仕様、創屋向けカタログ |
| Django辞書接続 | `services/dictionaries.py` | 現行仕様、Windows確認事項 |
| 補正 | `services/overrides.py`、`persistence.py` | 現行仕様、抽出結果スキーマ |
| HTTP API | `api/urls.py` | 現行仕様、Windows agent仕様 |
| 統合UI | `integrations/2D_3D_CAD_VIEWR/frontend/src/features` | 現行仕様、viewer UI仕様 |
| Cloud検証資材 | `handoff/claude_cloud` | Cloud検証README、チェックリスト、依頼文 |

## 5. 更新ルール

- コード変更時は、最初に本索引で影響文書を特定する。
- 現在の挙動は現行正本へ反映する。
- 調査・検証の数値は既存snapshotを上書きせず、新しい日付の結果として追記する。
- 旧文書に未実装記述が残る場合は、履歴文書であることと現行正本へのリンクを冒頭に明示する。
- API名、モデル名、設定名、コマンドは記憶で書かずコードから転記する。
- 更新後は`python scripts\audit_tag_documentation.py`を実行する。
