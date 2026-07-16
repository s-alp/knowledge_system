# Design QA

- 実施日: 2026-07-16
- 対象: 統合2D・3Dビューワー内の「製品・装置・ユニット」「部品」一覧・詳細・編集・根拠・図面紐づけ
- 参照画面:
  - `C:\Users\s-iwata\AppData\Local\Temp\codex-clipboard-666a5dd9-0691-4173-ac64-6cac7ab21396.png`
  - `C:\Users\s-iwata\AppData\Local\Temp\codex-clipboard-c30a4603-28a9-4d08-92f2-47dc75ae2658.png`
- ローカル証跡: `output\entity_ui_2026-07-16`
- 比較viewport: 1708 x 920

## 確認結果

| 観点 | 結果 | 証跡 |
| --- | --- | --- |
| 基本情報 | 白枠、2列項目、ver.1、スター、編集・削除アイコンを再現 | `product-detail.png`, `part-detail.png` |
| 属性情報 | 基本情報内の表として表示し、質量・重量をkg小数点以下2桁で表示 | `product-detail.png`, `part-detail.png` |
| 関連情報 | 創屋画面と同じ固定タブ構成を対象別に表示 | `product-detail.png`, `part-detail.png` |
| 図面紐づけ | 検索、複数選択、保存、解除の専用画面を表示。実候補67件の読み込み完了を確認 | `product-drawing-link.png`, `result.json` |
| 取得根拠 | 属性・タグの取得元、信頼度、根拠位置、採用理由を同じダイアログで表示 | `product-provenance.png`, `result.json` |
| システム設定 | 旧Django画面へ遷移せず、5173内の同一UIでタグ自動取得設定を表示 | `system-settings.png`, `result.json` |
| 変更履歴 | 白枠の履歴表として抽出更新と手動更新を表示 | `product-detail.png`, `part-detail.png` |
| 取得根拠 | 通常詳細を煩雑にせず、専用ダイアログから取得元、証拠、信頼度を確認 | `product-provenance.png` |
| 業務状態 | 抽出内部状態の「確認待ち」を利用者向けステータスへ表示しない | `result.json` |
| ブラウザ品質 | console/page/HTTPエラー0件 | `result.json` |

統合ビューワーの左メニューと上部ヘッダーは既存2D・3Dビューワーの操作体系として維持した。参照画像より実属性・タグ・履歴が多いことはデータ量の差であり、レイアウト逸脱ではない。P0、P1、P2の視覚不具合は確認されなかった。

Result: passed
