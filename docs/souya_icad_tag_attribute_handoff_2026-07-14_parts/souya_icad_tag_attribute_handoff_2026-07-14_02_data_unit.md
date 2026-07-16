# 創屋向け ICADタグ・属性連携項目表 - 2. こちらが提供するデータ単位

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 2. こちらが提供するデータ単位

| 提供単位 | 主なキー | 内容 | 備考 |
| --- | --- | --- | --- |
| `source_file` | `full_path`, `directory_path`, `file_name`, `extension`, `sx_net_input_path`, `sx_net_input_strategy`, `used_sx_net_alternate_path` | 保存フォルダ、ファイル名、拡張子、SXNETへ実際に渡したパス | 原本パスは検索・追跡用属性として保持。SXNETの長パス制限を避けるため短縮パスまたは一時コピーを使った場合も診断できるようにする。ブラウザアップロード由来ICDは内部保存名を `input.icd` に固定し、`temporary_copy_forced` で短い一時パスを使う |
| `raw_extract_2d` | `view_sheets`, `print_frames`, `layers`, `texts`, `dimensions`, `geometry_primitives`, `referenced_parts` | SXNETから取得した2D証拠 | 図枠外/印刷枠外は削除せず `inside_print_area` で判定 |
| `raw_2d_sections` | `title_block`, `drawing_body`, `dimensions`, `notes`, `balloons`, `manufacturing_symbols` | 2D証拠を画面/fixture向けに6区画へ整理した要約 | `raw_2d_sections.v1`。印刷枠がある図面では `inside_print_area=true` の要素だけを自動利用数へ含める |
| `raw_extract_3d` | `top_part`, `parts`, `mass_properties`, `mass_probe_status`, `materials`, `material_probe_status` | SXNETから取得した3D証拠 | パーツ付加情報は `ex_info_fields` として保持 |
| `canonical_attributes` | 下表参照 | 2D/3D横断の正規化属性 | 本番DB/APIへ渡す属性候補 |
| `derived_tags` | `tag`, `source`, `evidence`, `confidence`, `reason`, `manual_flag`, `tag_rule_version` | 自動タグ候補 | 検索・分類に効く値だけを採用し、採用理由と根拠を追跡可能にする |

### 2.1 抽出失敗診断

`GET /api/v1/drawing-metadata/handoff-summary` の `recentFailedJobs[]` は、SXNETの生エラーだけでなく以下を返す。

| 項目 | 内容 |
| --- | --- |
| `errorClass` | `sxnet_rejected_as_not_drawing_file`, `path_length_limit`, `source_file_not_found`, `extractor_timeout`, `sxnet_open_failure` などの分類 |
| `sourcePreflight.sourcePathLength` | 登録されている原本ICADパスの文字数 |
| `sourcePreflight.sourcePathWithinSxnetLegacyLimit` | SXNETへ直接渡すには安全な長さか |
| `sourcePreflight.requiresSxnetStagedInput` | 抽出時に短い一時パスへ退避すべきか |
| `sourcePreflight.sxnetStagingReasons` | 短い一時パスへ退避する理由。`path_length` / `filename_length` を保持 |
| `sourcePreflight.sourceExistsFromCurrentMachine` | 現在のworker実行環境から原本ICADへアクセスできるか |
| `reextractCondition` | 再抽出前に確認する条件。長パス退避、ICAD対応版、外部参照不足、ファイル破損、ネットワークパス未接続などを切り分ける |

SXNETの `指定したファイルは図面ファイルではありません。` は、ICD拡張子そのものを否定する意味に固定しない。原本パス、長パス退避、ICAD/SXNET対応版、外部参照不足、2D/3Dデータ有無を分けて確認する。

登録時の `filename` は一覧・詳細画面で見せる表示名であり、DB上限に合わせて255文字以内へ丸める場合がある。抽出時は `source_path` を原本として保持し、SXNETへ直接渡すには危険な長パス/長ファイル名の場合だけ短い `input.icd` 相当の一時入力へ退避する。利用者に原本ファイル名の変更を求める運用にはしない。

既存DBに失敗ジョブが残っている場合は、`python manage.py backfill_drawing_metadata_failure_diagnostics` で過去分の `diagnostics_json.failure` を補完する。事前確認だけ行う場合は `--dry-run` を付ける。納品監査では `scripts/audit_drawing_metadata_job_state.py` が失敗ジョブの `failure diagnostics` 欠落をブロックする。

属性連携プレビュー `targets[].attributes[]` は `sourcePath`, `evidence`, `confidence`, `reason` を必須項目とする。対象別タグは、互換用の `targets[].tags` 文字列配列に加えて `targets[].tagEvidence[]` を持ち、`tag`, `source`, `evidence`, `confidence`, `reason`, `manualFlag`, `tagRuleVersion` を返す。`scripts/audit_knowledge_payload_attribute_quality.py` はmanifest対象の属性候補と対象別タグ候補を走査し、根拠・信頼度・採用理由の欠落をブロックする。2026-07-17時点の確認ではmanifest対象39件、属性候補607件、対象別タグ227件、issue 0件。
| `reconciledAttributes` | `attribute`, `value2d`, `value3d`, `chosenValue`, `chosenMode`, `status`, `reason` | 2D/3D照合結果 | 一致、片側のみ、統合、手動上書き、競合を全属性単位で保持 |
| `conflicts` | `attribute`, `mode2dValue`, `mode3dValue`, `chosenValue`, `chosenMode`, `reason` | 2D/3D差異のうち設計レビュー対象だけ | 材質、重量、図番、図面名など、採用値を人が見るべき差異に限定する |
| `diagnosticConflicts` | `attribute`, `mode2dValue`, `mode3dValue`, `chosenValue`, `chosenMode`, `reason` | 内部品質・件数・抽出元などの診断差分 | `source_kind`、`confidence_summary`、`*_count`、`*_exists` など。JSON証跡には残すがRAG投入前レビュー対象からは外す |
| `knowledgeSystemPayloadPreview` | `targets[].payloadPreview`, `targets[].attributes`, `targets[].tags`, `targets[].tagEvidence` | 本番タグ・属性連携の候補payload | 本番登録は行わない。図面/製品・装置・ユニット/部品/プロジェクト別に、既存受け口・未確定点・属性マスタID未解決・タグ根拠を明示 |

