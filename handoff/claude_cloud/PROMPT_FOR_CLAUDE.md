# Cloud Claude Code への依頼文

このリポジトリは ICAD 2D/3D からタグ・属性候補を抽出し、ナレッジシステム風の図面管理、製品・装置・ユニット、部品ページへ表示する検証実装です。

あなたには Cloud 環境で検証してほしいです。Cloudでは ICAD/SXNET/社内ファイルサーバ/Jドライブ/Tドライブ/本番ナレッジシステムDB にはアクセスできません。したがって `.icd` の再抽出は検証対象外です。

## セットアップ

1. `handoff/claude_cloud/README.md` に従って backend/frontend を起動してください。
2. `handoff/claude_cloud/sql/seed_drawing_metadata_minimal.sql` を `tools/apply_seed_sql.py` で投入してください。
3. `handoff/claude_cloud/data/*.json` を、実ICAD抽出済みの監査根拠として読んでください。

## 検証してほしいこと

- `handoff/claude_cloud/VALIDATION_CHECKLIST.md` の項目を確認してください。
- UIが創屋ナレッジシステム風の一覧/詳細/関連情報の構造になっているか見てください。
- 製品・装置・ユニット/部品/図面管理でタグ・属性・根拠・履歴が自然に確認できるか見てください。
- タグ生成ルールが材質だけ、または意味の薄い加工指示タグに偏っていないか確認してください。
- 1 ICD = 1登録単位の考え方が壊れていないか確認してください。
- Cloudで実抽出できない箇所と、既存抽出結果から検証できる箇所を分けて報告してください。

## 絶対にしないこと

- 創屋本番DB、本番ナレッジシステムへの書き込み
- APIキーや `.env` の要求
- ICAD/SXNET再抽出がCloudでできる前提の評価

## 報告形式

重大な問題、仕様と違う問題、見た目/UXの問題、残リスク、追加でローカルWindows環境に確認してほしいこと、の順で簡潔に報告してください。
