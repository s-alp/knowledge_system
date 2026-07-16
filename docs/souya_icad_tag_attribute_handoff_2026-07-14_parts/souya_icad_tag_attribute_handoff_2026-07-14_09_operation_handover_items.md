# 創屋向け ICADタグ・属性連携項目表 - 9. 運用・創屋側確認事項

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 9. 運用・創屋側確認事項

- 3D材質APIの部品単位紐づけは候補生成まで実装済み。材質ID辞書も初期実装済みで、共有39件では要確認材質を `ZZZ`, `CDQ`, `75` まで絞り込めている。正式材質マスタとの突合は、創屋側の属性マスタID・材質マスタ運用が確定してから実施する。
- 2D図枠欄名辞書は客先横断で継続拡充する。未知の図枠欄名は値を捏造せず、根拠文字・座標・候補分類状態を残してレビューできるようにする。
- Gemini API低温度JSON分類は2D抽出ジョブへ組み込み済み。APIキー未設定時はスキップし、API失敗時は `title_block_llm_classification_failed` warning として記録する。既存候補値の欄名分類補助に限定し、ルール抽出済みの属性は上書きしない。2026-07-15 に `backend\.env` よりOS環境変数が優先されて古いキーを読んでいた問題を修正し、実API疎通を確認した。`gemini-flash-latest` を主モデル、`gemini-3.1-flash-lite` / `gemini-3.5-flash` をフォールバックにして、現行正規化後の代表5件すべてで分類応答を取得した。結果は `output\live_extracts\title_block_llm_probe_2026-07-14\gemini_probe_current_normalization_2026-07-17.json` に保存し、評価では classification precision 1.0000、positive recall 1.0000、誤分類0、誤採用0、accepted uplift 0 を確認した。運用監査は `scripts/audit_llm_title_block_guardrails.py` と `scripts/evaluate_title_block_llm_probe.py` で行い、分類漏れや誤採用が残る場合は納品監査を失敗させる
- 長穴、穴数、断面、表面粗さ値は属性化済み。円/楕円を穴・長穴として断定できない場合は、形状候補として保持し、用途断定タグには採用しない。
- 2D/3D照合結果の採用値、差異、要確認理由は画面表示とAPI/fixtureへ実装済み。本番API/fixture名の最終合わせは、創屋側の受け入れAPI名と属性マスタが確定してから実施する。

