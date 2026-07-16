# 創屋向け ICADタグ・属性連携項目表 - 7B. 検証ログ

[7章目次へ戻る](souya_icad_tag_attribute_handoff_2026-07-14_07_api_fixture_contract.md)

2026-07-15 に 2D の全ビュー、レイヤー、印刷枠内外判定を確認するため、詳細画面へ `ビュー別取得状況` と `レイヤー別取得状況` を追加した。文字、寸法、図形をまとめて、ビュー別/レイヤー別に何件取れているか、印刷枠内/外/不明が何件あるかを表示する。

同日に `scripts\summarize_2d_extraction_coverage.py` を追加し、共有済み2D抽出JSONを集計した。2026-07-17 時点では、古い途中抽出JSONではなく、現行runnerで再抽出した `output\live_extracts\all_shared_2d_reextract_current` を正の確認対象にしている。

```powershell
python scripts\summarize_2d_extraction_coverage.py `
  --input-root output\live_extracts\all_shared_2d_reextract_current `
  --output output\souya_handoff\icad_2d_extraction_coverage_manifest_2026-07-15.json
```

現行再抽出結果:

- 2D対象: 39ファイル
- ビュー/用紙数: 210
- 印刷枠数: 32
- レイヤー数: 9,945
- 取得対象要素: 30,105件
- 文字: 1,752件
- 寸法: 2,404件
- 図形primitive: 25,903件
- 印刷枠内: 5,088件
- 印刷枠外: 23,849件
- 印刷枠判定不明: 1,168件
- ビュー情報なし: 0件
- レイヤー未設定要素: 1,168件
- 印刷枠情報なし: 10ファイル
- `unsupported_geometry` / `Unhandled geometry`: 0件

全量ディレクトリ確認の結果は `output\souya_handoff\icad_2d_extraction_coverage_summary_2026-07-15.json` に保存した。2026-07-17 時点では、同ファイルも現行再抽出結果に更新済みであり、古い途中抽出JSONを品質判断に使わない。

2026-07-17 に共有manifestの2D対象39件を最新runnerで再抽出し、旧coverage JSONを置き換えた。

- 実行スクリプト: `scripts\run_manifest_2d_reextract_2026_07_15.ps1`
- 再抽出出力先: `output\live_extracts\all_shared_2d_reextract_current`
- 再抽出manifest: `output\souya_handoff\icad_extract_import_manifest_reextract_2026-07-15.json`
- 2Dカバレッジ: `output\souya_handoff\icad_2d_reextract_coverage_selected_manifest_2026-07-15.json`
- 現行レビューサマリ: `output\souya_handoff\drawing_metadata_fixture_all_shared_review_summary_2026-07-17.json`

再抽出後の共有サンプル集計結果:

- 2D対象: 39ファイル
- ビュー/用紙数: 210
- 印刷枠数: 32
- レイヤー数: 9,945
- 取得対象要素: 30,105件
- 文字: 1,752件
- 寸法: 2,404件
- 図形primitive: 25,903件
- 印刷枠内: 5,088件
- 印刷枠外: 23,849件
- 印刷枠判定不明: 1,168件
- ビュー情報なし: 0件
- レイヤー未設定要素: 1,168件
- 印刷枠なし: 11ファイル
- `unsupported_geometry` / `Unhandled geometry`: 0件

旧manifestでは `ビュー情報なし17ファイル`、`印刷枠情報なし17ファイル`、`レイヤー情報なし17ファイル` だったため、最新抽出器で全ビュー・印刷枠・レイヤー取得は大きく改善した。`18T5-10BF(8).icd` は当初パスでは `file_not_found` だったが、同じ作業フォルダ配下の `OLD` フォルダで移動後パスを特定し、manifest/ローカルDBを明示的に付け替えて再抽出済みである。

同日さらに `SxGeomLine2D` の座標取得を見直し、scalar の `x1/y1/x2/y2` が無い線分でも `pnt1/pnt2`、`pos1/pos2`、`sp/ep`、`start/end` から開始点・終点を拾うようにした。改善前は `SxGeomLine2D` が印刷枠判定不明の大半を占めていたが、再抽出後は `unknownPrintArea=488` まで低下した。内訳分析は `output\souya_handoff\icad_2d_print_area_unknown_analysis_2026-07-15.json` に保存した。

- 分析対象要素: 23,279件
- 判定不明: 481件
- 座標欠落による不明: 481件
- 座標ありだが判定失敗: 0件
- 不明primitive型: `SxGeomHatch` 169件
- 残りは主に `SxGeomHatch` と、`Ｙ` など座標なし文字である

SXNET の `SxGeomHatch` 公開フィールドは `pattern`、`angle`、`dist`、`pitch`、`ex_name`、`ex_scale`、`type` が中心で、直接の座標または外接矩形は確認できなかった。そのため、ハッチング座標は捏造しない。raw extract には証跡として保持し、印刷枠が取得できている図面では `inside_print_area=true` と判定できた要素だけを自動タグ・検索候補へ使う。

2026-07-15 に正規化層へ上記制御を追加した。印刷枠がある図面では、`inside_print_area=null` の文字、寸法記号、溶接注記、バルーン、幾何primitiveを `part_keywords`、`spec_tokens`、図枠候補、訂正内容候補、形状特徴候補から除外する。raw の `text_tokens` や `geometry_primitives` は削除せず、後から人が確認できる証跡として残す。印刷枠が取れない図面では従来どおり `null` を保持して、情報欠落で一律に捨てない。

比較結果は `output\souya_handoff\drawing_metadata_fixture_tag_diff_unknown_filter_2026-07-15.json` に保存した。旧fixture比で、2D/3D snapshot数は45件のまま、自動タグ9件、`part_keywords` 1,031件、`spec_tokens` 1,014件、ハッチング/断面カウント169件を削減した。削除されたタグは、座標不明ハッチング由来の `図面特徴:ハッチング` と、枠外/枠不明テキスト由来のユニット・装置タグであり、図枠外データの誤反映抑止として妥当である。

同日に本番ナレッジシステムの実画面もChromeで再確認した。登録、変更、削除は行っていない。

- プロジェクト一覧: `output\knowledge_ui_screenshots_2026-07-15\30-project-list-settled.png`
- 製品・装置・ユニット一覧: `output\knowledge_ui_screenshots_2026-07-15\31-product-unit-list-settled.png`
- 部品一覧: `output\knowledge_ui_screenshots_2026-07-15\32-part-list-settled.png`
- 部品詳細: `output\knowledge_ui_screenshots_2026-07-15\01-part-detail-start-viewport.png`
- 図面一覧: `output\knowledge_ui_screenshots_2026-07-15\33-drawing-list-settled.png`
- AI検索: `output\knowledge_ui_screenshots_2026-07-15\34-ai-search-settled.png`
- 類似検索: `output\knowledge_ui_screenshots_2026-07-15\35-similar-search-settled.png`
- 図面詳細2D: `output\knowledge_ui_screenshots_2026-07-15\03-drawing-detail-2d.png`
- 図面詳細3Dエラー: `output\knowledge_ui_screenshots_2026-07-15\04-drawing-detail-3d-error.png`
- ローカル詳細: `output\knowledge_ui_screenshots_2026-07-15\05-local-detail.png`
- ローカルタグレビュー: `output\knowledge_ui_screenshots_2026-07-15\06-local-tag-review.png`

確認結果:

- 本番部品詳細には `属性情報` 欄があり、サンプルでは空表示だった。部品タグ・属性の受け口として重要。
- 本番図面一覧には、検索条件、図面タイプ、ステータス、紐づき概要が見える。タグ列は未表示。
- 本番プロジェクト一覧、製品・装置・ユニット一覧、部品一覧にもタグ列は見えない。タグを活用するなら、一覧条件・詳細属性・関連情報のどこへ反映するかを創屋と確認する。製品・装置・ユニットは実メニュー遷移で `/web/product` を確認した
- 本番AI検索はチャット履歴と質問欄が中心で、タグを直接編集する場所ではない。タグは検索前フィルタ、RAG投入payload、ランキング信号として裏側で使うのが自然。
- 本番類似検索は2D/3Dチェック、検索ファイル、類似度、図面名、用途、規格、重要度フィルタが見える。ICAD抽出タグは類似検索フィルタや重みづけ補助にも使える。
- 本番図面詳細には `タグ` と `属性情報` 欄、2D/3D切替、2Dプレビューが見える。初期連携先は引き続き図面詳細を最優先にする。
- 本番図面詳細の3D切替では `/web/public/models/test_000445.gltf` がHTMLを返し、GLTFとして読めずアプリ全体がエラー画面になった。抽出器の問題ではないが、創屋への2D/3Dプレビュー連携確認事項に含める。
- ローカル詳細画面では `CAA5012-02434000K1R1.icd` について `2Dあり`、`3Dあり`、viewerタグ、保存フォルダ、パーツ付加情報数が表示される。
- ローカルタグレビュー画面では、図面/製品・装置・ユニット/部品/プロジェクトの適用先候補、統合タグ、2Dタグ、3Dタグ、競合が確認できる。
- ローカル詳細画面の `2D構造化セクション` では、図枠、中央図面、寸法、注記、バルーン、製造記号の6行が表示される。`schema=raw_2d_sections.v1`、印刷枠内/外/判定不明、自動利用件数、短いサンプルを確認できる。証跡は `output\knowledge_ui_screenshots_2026-07-15\68-local-drawing-detail-2d-structured-sections.png`

2026-07-15 にさらに本番実画面をChromeで読み取り専用確認した。登録、変更、削除は行っていない。メニュー遷移で、統合検索の実URLは `/web/integrated_search`、類似検索の実URLは `/web/drawing/similar_search` と確認した。プロジェクト詳細はタグ/属性欄なし、製品・装置・ユニット詳細と部品詳細は `属性情報` 欄あり、図面詳細は `タグ` と `属性情報` 欄あり。

- 本番トップ: `output\knowledge_ui_screenshots_2026-07-15\70-production-home-screen.png`
- 本番統合検索: `output\knowledge_ui_screenshots_2026-07-15\78-production-integrated-search-menu-screen.png`
- 本番類似検索: `output\knowledge_ui_screenshots_2026-07-15\79-production-similar-search-menu-screen.png`
- 本番プロジェクト詳細: `output\knowledge_ui_screenshots_2026-07-15\84-production-project-detail-screen.png`
- 本番製品・装置・ユニット詳細: `output\knowledge_ui_screenshots_2026-07-15\85-production-product-detail-screen.png`
- 本番部品詳細: `output\knowledge_ui_screenshots_2026-07-15\86-production-part-detail-screen.png`
- 本番図面詳細: `output\knowledge_ui_screenshots_2026-07-15\87-production-drawing-detail-screen.png`
- ローカル診断差分表示: `output\knowledge_ui_screenshots_2026-07-15\88-local-diagnostic-conflicts-detail.jpg`

同じタグレビュー画面へ、`knowledgeSystemPayloadPreview` の対象別サマリを追加した。これにより、図面、製品・装置・ユニット、部品、プロジェクトごとに、既存受け口、タグAPI状態、タグ数、属性数、候補endpoint、属性候補、タグ候補を1画面で確認できる。創屋へ渡すJSONの見せる側の確認画面であり、本番保存操作は行わない。

- ローカルタグレビューpayload確認: `output\knowledge_ui_screenshots_2026-07-15\89-local-tag-review-payload-targets.jpg`

```json
{
  "drawingId": "host drawing id",
  "sourceFile": {
    "fullPath": "J:\\...",
    "directoryPath": "J:\\...",
    "fileName": "sample.icd",
    "extension": ".icd"
  },
  "canonicalAttributes": {
    "drawing_number": null,
    "drawing_name": null,
    "customer_name": "澁谷工業",
    "equipment_category": "ロボット",
    "mass_probe_status": "available",
    "weight_value": 0.00540269,
    "title_block_fields": {
      "material": "SUS304"
    },
    "geometry_feature_candidates": [
      {
        "feature": "surface_roughness",
        "label": "表面粗さ",
        "classification_label": "表面粗さ記号あり",
        "searchable_tag": false,
        "tag_adoption_status": "excluded",
        "tag_adoption_reason": "製造記号や形状候補の存在だけでは検索・分類タグとして粗いため、図面証拠として保持し、自動タグには採用しません。",
        "confidence": "medium",
        "count": 2
      }
    ]
  },
  "derivedTags": [
    {
      "tag": "客先:澁谷工業",
      "source": "customer_name",
      "confidence": "high",
      "manual_flag": false
    }
  ],
  "reconciledAttributes": [
    {
      "attribute": "material",
      "value2d": "SUS304",
      "value3d": "SUS304",
      "chosenValue": "SUS304",
      "chosenMode": "3d",
      "status": "matched",
      "reason": "2Dと3Dの抽出値が一致したため採用しました。"
    },
    {
      "attribute": "weight_value",
      "value2d": "2.1kg",
      "value3d": 2.08,
      "chosenValue": 2.08,
      "chosenMode": "3d",
      "status": "conflict",
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を採用候補として示し、確定値にはしません。"
    }
  ],
  "conflicts": [
    {
      "attribute": "weight_value",
      "mode2dValue": "2.1kg",
      "mode3dValue": 2.08,
      "chosenValue": 2.08,
      "chosenMode": "3d",
      "reason": "2Dと3Dの抽出値が異なるためレビュー対象です。表示上は3D値を採用候補として示し、確定値にはしません。"
    }
  ],
  "diagnosticConflicts": [
    {
      "attribute": "confidence_summary",
      "mode2dValue": "medium",
      "mode3dValue": "high",
      "chosenValue": "high",
      "chosenMode": "3d",
      "reason": "内部品質・件数・抽出元差分のため、自動タグ/RAG投入前レビュー対象からは除外しました。"
    }
  ]
}
```

