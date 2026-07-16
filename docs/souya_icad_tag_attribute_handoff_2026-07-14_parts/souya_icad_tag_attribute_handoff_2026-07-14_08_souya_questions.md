# 創屋向け ICADタグ・属性連携項目表 - 8. 創屋への確認事項

[目次へ戻る](../souya_icad_tag_attribute_handoff_2026-07-14.md)

## 8. 創屋への確認事項

- 図面詳細の `tags` / `attributes` の保存先テーブルとAPI名
- `drawing_attributes`, `product_attributes`, `part_attributes` の登録/更新APIの有無
- プロジェクトに属性/タグを保存するAPIまたは詳細表示口の有無
- タグは図面単位だけか、製品・ユニット・部品にも保存できるか
- `drawing_attributes`, `product_attributes`, `part_attributes` はマスタ定義APIに見えるため、個別図面/製品/部品へ属性値を保存する際の payload 形式と更新API名
- 個別図面/製品/部品の属性値 payload で `attribute`, `attribute_option`, `attribute_value` を使う見立てが正しいか
- `attributeName` / `attributeValue` で渡した候補を、創屋側で本番属性マスタIDへ解決できるか。こちら側でマスタIDを事前fixture化する必要があるか
- 図面と文書には `tags` がある一方、製品・部品・プロジェクトのタグ保存口はフロント資産上では未確認のため、タグを属性として代替するか、タグ保存APIを追加するか
- 手動補正履歴をどのテーブルに保持するか
- RAG検索インデックスへ投入できるフィールド名、型、更新タイミング
- 2D/3Dプレビュー詳細APIへ追加項目を渡せるか
- 本番3Dプレビューの `test_000445.gltf` 読み込みエラーの原因
- 材質辞書の `formal` / `unresolved` / `excluded` を本番マスタとして持つか、こちらの抽出モジュール側だけで持つか

