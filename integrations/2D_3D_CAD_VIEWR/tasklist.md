# Task List

## 現在フェーズ

- [x] 初版ビューア機能を完成
- [x] バックエンド API とフロントエンド UI を接続
- [x] TIFF ページ画像化と STEP -> STL 変換を運用構成へ反映
- [x] テスト、ライセンス、納品文書の基本整備を完了
- [x] README / docs / AGENTS / tasklist の役割分担を整理
- [x] PDM 埋込向けに drawingId 起動と PDM API 解決を実装

## 今回までの完了項目

- [x] リポジトリ骨組みを作成
- [x] URL 取得と SSRF 対策を実装
- [x] 2D viewer の open/source/page-image API を実装
- [x] 3D viewer の open/job/model API を実装
- [x] ローカルファイル upload API と検証用 UI を追加
- [x] TIFF をバックエンドで PNG 化して表示する構成を採用
- [x] STEP を STL へ変換して表示する構成を採用
- [x] フロントエンドの状態管理とツールバー挙動を整備
- [x] テストを整備
- [x] ライセンス文書を整備
- [x] 納品パッケージ手順書を作成
- [x] 組み込み手順書を作成
- [x] 外部向け仕様書を整備
- [x] 内部向けコードマップを整備
- [x] 既存文書を現行実装へ同期
- [x] 社内 http/https URL を allowlist 方式で直接開けるようにした
- [x] 社内 URL 対応の設定例と運用手順を文書へ反映した
- [x] handover パッケージ同期スクリプトを追加した
- [x] handover 技術概要資料を追加した
- [x] handover README を社内用 README から分離した
- [x] 提出物からテストコードを除外し、受入確認手順へ置き換えた
- [x] 提出物のテスト設定とテスト依存を自動除外するようにした
- [x] Docker Compose による再現環境と開発環境を追加した
- [x] 2D / 3D の入力導線を共通 hook / component に整理した
- [x] 画面と API の流れを追える `docs/viewer-flow.md` を追加した
- [x] handover 向け理解用のコメントと文書を補強した
- [x] drawing bootstrap API と PDM resolver を追加した
- [x] frontend を drawingId 起動へ切り替えた
- [x] debug 用 URL / upload UI を本番表示から分離した
- [x] PDM 埋込前提で README / docs を同期した
- [x] ナレッジ画面に寄せた図面詳細 UI を追加した
- [x] 2D viewer のパン / ズーム時の再ラスタライズを抑制して操作体感を改善した
- [x] 2D viewer の操作 state を preview 内へ局所化し、PDF の軽量 scale 制御を追加した

## 継続運用タスク

- [ ] API 契約を変更したら `README.md`、`docs/viewer-specification.md`、`docs/integration-manual.md` を同期する
- [ ] 依存を追加・削除したら `docs/THIRD_PARTY_NOTICES.md` と `docs/licenses/README.md` を同期する
- [ ] 主要ファイルの責務や配置を変更したら `docs/code-map.md` を同期する
- [ ] TIFF / STEP / 断面キャップ方針を変えたら関連メモを同期する
- [ ] 納品前に `docs/handover-package-manual.md` と `.env.example` を再確認する
- [ ] 提出前に `scripts/sync_handover_package.ps1 -Mode update` と `-Mode check` を実行する

## 将来拡張候補

- [ ] PDM API の 2D/3D ソース解決契約を本番用に固定する
- [ ] 複数断面
- [ ] 巨大 CAD 向けの非同期ワーカー
- [ ] 注釈と計測
- [ ] DXF など追加形式
