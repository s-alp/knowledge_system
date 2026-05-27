# knowledge_system

ナレッジシステムの RAG 精度検証、ICAD 2D/3D からのタグ・属性抽出設計、Django 統合計画の整理用リポジトリです。

## 現在の位置づけ

- 共同開発先からナレッジシステム本体ソースコードは共有されていません。
- そのため本リポジトリは、本体へ後で移植しやすい形で
  - 調査
  - 設計
  - 実装準備
  - 検証資料作成
  を進めるための作業場です。

## 主な内容

- `docs/`
  - ICAD タグ・属性設計資料
  - Django 統合計画
  - 抽出結果スキーマ
  - タグ・属性管理 UI 計画
  - 外部共有向け HTML 要約報告
- `scripts/`
  - RAG 検証結果の集計・追記スクリプト
- `local_test_materials/`
  - 検証用に最小限コピーした元資料
- `output/`
  - 集計済み Excel、画像、検証成果物
- `sxnet/`
  - ICAD `sxnet` リファレンス一式

## 実装方針の要点

- ICAD ネイティブ抽出コアは `C#`
- 正規化、タグ生成、保存、RAG 連携は `Django(Python)` の service / task 層
- `Python -> C#` は `1図面 = 1回呼び出し` の一括実行
- `図面管理` をタグ・属性の正本とし、viewer と RAG は利用側に寄せる

## 重要ドキュメント

- [ICADタグ・属性 調査結果](./docs/icad_tag_attribute_investigation_2026-05-26.md)
- [ICADタグ・属性 設計計画](./docs/icad_tag_attribute_design_plan_2026-05-26.md)
- [ICADタグ・属性 実装引継ぎ](./docs/icad_tag_attribute_implementation_backlog_2026-05-26.md)
- [ICAD抽出の C# / Python 分担アーキテクチャ案](./docs/icad_csharp_python_architecture_2026-05-27.md)
- [Django統合計画](./docs/django_integration_plan_2026-05-28.md)
- [抽出結果スキーマ定義案](./docs/extraction_result_schema_2026-05-28.md)
- [タグ・属性管理UI計画](./docs/tag_attribute_management_ui_plan_2026-05-28.md)
- [HTML要約報告](./docs/icad_tag_attribute_report_2026-05-26.html)

## 次に進めること

1. ICAD 3D 抽出 PoC
2. ICAD 2D 抽出 PoC
3. C# 抽出コアの JSON schema 固定
4. Django app としての保存/API/task 実装設計
5. タグ・属性管理 UI の具体化

## 補足

- 現時点のプロジェクト前提・検証方針は [AGENTS.md](./AGENTS.md) を正とします。
- `CLAUDE.md` は `AGENTS.md` と同期維持します。
