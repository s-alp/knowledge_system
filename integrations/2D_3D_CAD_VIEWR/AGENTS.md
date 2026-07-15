# Repository Rules

## 目的

このリポジトリは PDM の図面詳細画面へ埋め込む 2D/3D ビューア専用です。標準の入口は `drawingId` ベースとし、業務ロジックや認証機能を混在させず、ビューア機能を中心に保守します。

## 実装方針

- Django View と React Page は薄く保ち、処理を service/hook/adapter に分離する
- 1 ファイル 1 責務を徹底し、肥大化したら責務単位で分割する
- URL 取得、変換、保存、時刻取得などの副作用は境界に閉じ込める
- 将来の形式追加を見据え、判定や変換は抽象インターフェース経由で扱う
- フロントは viewer core、adapter、control、shared api に分離する

## テスト方針

- バックエンドは service 層を優先して単体テストし、API テストで結線を確認する
- STEP 変換はテスト用 backend に差し替えられる構造を維持する
- フロントは state と control を優先してテストし、重い描画はモックで検証する

## 文書更新

- `README.md` は入口文書として扱い、概要、セットアップ、起動、検証手順、文書索引を最新化する
- 画面・API・変換をまたぐ流れを変更したら `docs/viewer-flow.md` を更新する
- `docs/viewer-flow.md` のコンセプト説明、全体像 Mermaid 図、2D/3D 詳細 Mermaid 図は実装フロー変更時に必ず同期する
- 提出先向けの README 原本は `docs/handover-readme.md` に置き、提出先へ渡す説明を変更したら必ず同期する
- 提出先向けの組み込み手順原本は `docs/handover-integration-manual.md` に置き、提出先へ渡す手順を変更したら必ず同期する
- 提出先向けの技術概要原本は `docs/handover-technology-summary.md` に置き、提出先へ渡す構成説明を変更したら必ず同期する
- 外部共有する仕様は `docs/viewer-specification.md` に集約し、API 契約や制約を変更したら必ず同期する
- 提出先向けの技術概要は `docs/technology-summary.md` に集約し、使用言語・主要モジュール・DB・処理方式を変更したら必ず同期する
- `docs/code-map.md` は提供先にも共有する前提とし、主要ファイルの責務や配置を変えたら必ず同期する
- 組み込み手順や納品手順を変えたら `docs/integration-manual.md` と `docs/handover-package-manual.md` を更新する
- 提出用パッケージの同期手順や同梱対象を変えたら `docs/handover-package-manual.md` と `README.md` を更新する
- Docker / docker-compose の起動方法、配布構成、永続化方針を変えたら `README.md`、`docs/integration-manual.md`、`docs/handover-readme.md`、`docs/handover-package-manual.md` を更新する
- frontend と backend の接続方法を変えたら、proxy の有無も含めて `README.md`、`.env.example`、`docs/handover-readme.md` を更新する
- 作業フェーズや保留事項が変わったら `tasklist.md` を更新する
- ライセンス対象や同梱物が変わったら `docs/THIRD_PARTY_NOTICES.md` と `docs/licenses/README.md` を更新する
- TIFF/3D 表示方針を変えたら `docs/tiff-handling-notes.md`、`docs/3d-performance-notes.md`、`docs/3d-section-cap-notes.md`、`docs/step-backend-replacement.md` の整合を確認する
- 文書更新時は、実装コード・`.env.example`・依存定義を確認してから記述する
- 実装に存在しない用語や形式は文書へ書かない

## ライセンス対応

- OCCT を使う場合は通知文書と LGPL 本文の同梱を維持する
- STEP 依存は `requirements-step.txt` と差し替え手順書に分離する
- UI のライセンス導線を削除しない
