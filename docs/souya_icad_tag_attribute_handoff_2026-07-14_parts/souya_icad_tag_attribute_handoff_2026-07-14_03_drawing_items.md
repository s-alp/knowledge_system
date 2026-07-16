# 創屋向け ICADタグ・属性連携項目表 - 3. 図面へ連携する項目

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 3. 図面へ連携する項目

図面は初期連携の最優先対象。詳細画面に `タグ` と `属性情報` の表示口がある。

| 分類 | 項目 | source | 連携先候補 | 信頼度方針 |
| --- | --- | --- | --- | --- |
| ファイル | ファイル名、保存フォルダ、フルパス | `source_file` | 図面属性 | 高 |
| 識別 | 図番、図面名、改訂 | `title_block_fields`, ファイル名, 3Dモデル名 | 図面属性 | 中。図枠辞書拡充後に上げる |
| 図面条件 | 図面サイズ、尺度、ビュー/用紙数、印刷枠数 | `print_frames`, `view_sheets` | 図面属性 | 中 |
| 2D図枠 | 担当者、検図者、承認者、日付、材質、重量、表面処理、塗装指示、PRFX、ユニット番号 | `title_block_candidates`, `title_block_fields` | 図面属性、タグ候補 | 候補値。根拠文字と座標を保持 |
| 2D図枠AI補助分類 | 曖昧な図枠候補の欄名 | `title_block_llm_classifications`, `title_block_candidates[].llm_*` | 図面属性候補の補助 | Gemini低温度JSON分類。既存候補値だけを分類し、CADに無い値は生成しない |
| 2D訂正内容 | 訂正、改訂、変更、修正、REV系の注記/表文字 | `revision_note_candidates`, `revision_note_count` | 図面属性、改訂履歴確認 | 改訂番号とは別に、根拠文字・座標・印刷枠内外を保持。本文や存在フラグはタグ化しない |
| 2D特徴 | ハッチング、表面粗さ、切断線、データム、幾何公差、長穴候補、穴候補 | `geometry_feature_candidates` | 図面証拠候補 | 自動タグには採用しない。根拠ジオメトリ、件数、概要、採用除外理由を保持 |
| 2D形状・記号属性 | 表面粗さ記号数/値、断面・切断表現数、仕上げ記号数/種別、長穴/楕円候補数、穴/円候補数、候補径 | `surface_roughness_*`, `section_feature_count`, `finish_mark_*`, `slot_candidate_*`, `hole_candidate_*` | 図面属性、類似検索フィルター補助 | 印刷枠外は除外。記号や円/楕円は形状候補として保持し、用途断定はしない |
| 3D構成 | 最上位パーツ名、部品数、外部参照、ミラー、未解決参照 | `top_part`, `parts` | 図面属性、タグ候補 | 高 |
| 3D重量 | 質量、重量、体積、面積、密度、重心、慣性モーメント、単位、計算対象要素数 | `mass_properties`, `inertia_moment_candidates[]` | 図面属性 | 中から高。`mass_probe_status` と warning を併記。慣性モーメントは検索タグではなく3D解析属性として扱う |
| 3D材質 | 材質ID、材質名、比重、対象要素数 | `materials` | 図面属性、材質タグ候補 | 中。日本語材質名は文字コード揺れがあるため材質IDを主キー寄りに扱う |
| 3D部品材質候補 | パーツ階層、材質ID/材質名、比重、根拠、信頼度、材質分類 | `part_material_candidates` | 図面属性、部品属性 | `formal` は通常材質、`unresolved` は要確認、`excluded` はタグ化しない。パーツ付加情報内の材質らしい値は中信頼 |
| パーツ付加情報 | 客先固有フィールド、PRFX候補、材質候補、ユニット候補 | `parts[].ex_info_fields` | 図面属性、部品属性 | 中。客先ごとの辞書化が必要 |

