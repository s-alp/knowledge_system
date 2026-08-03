# ソースコードの読み方・変更箇所

この資料は、変更したい機能から確認するファイルを選び、影響範囲を小さく保つための案内です。最初から全ファイルを読む必要はありません。

## 1. 最初に確認する入口

| 目的 | 最初に見るファイル | 主な役割 |
|---|---|---|
| Python処理を呼び出す | python/icad_tag_extraction/pipeline.py | 正規化とタグ生成を順に呼び出す公開処理 |
| CLIの引数を確認する | python/icad_tag_extraction/cli.py | 入力、辞書、出力の検証とファイルI/O |
| Python公開APIを確認する | python/icad_tag_extraction/__init__.py | 組み込み先からimportできる関数とクラス |
| ICAD抽出コマンドを確認する | csharp/src/IcadExtraction.Runner/Program.cs | extract、convert-cad、agentの入口 |
| SXNETで取得する項目を確認する | csharp/src/IcadExtraction.SxNet | ICAD 2D／3Dの実データ取得 |
| JSONの正確な型を確認する | schemas | C# raw、共通属性、タグ結果の機械契約 |

実際の入力と出力はexamples/rawとexamples/resultsを並べて確認してください。

## 2. Python正規化処理の分担

正規化処理は変更理由ごとに分かれています。外部からはnormalization.pyの公開関数を使い、内部ファイルを直接呼び出さないでください。

| ファイル | 変更する内容 |
|---|---|
| normalization.py | normalize_raw_extractとnormalize_identity_name_valueを再公開する入口。通常は変更しません |
| normalization_pipeline.py | 2D／3Dの入力を判定し、候補を統合してcanonical_attributesを組み立てる順序 |
| normalization_2d.py | 2D処理を再公開する内部入口。通常は変更しません |
| normalization_2d_sections.py | 印刷範囲の判定と、図枠・寸法・注記・製造記号などの用途別整理 |
| normalization_2d_identity.py | 図番、図面名、図枠値、改訂履歴の候補選択 |
| normalization_2d_geometry.py | 表面性状、穴、中心、断面など形状・製造属性の整理 |
| normalization_3d.py | 部品階層、外部参照、材質候補など3D固有の処理 |
| normalization_material.py | 2D／3D共通の材質コード、除外値、重量表記 |
| normalization_text.py | 文字列、図枠値、辞書照合前の共通整形 |
| normalization_rules.py | 正規表現、ラベル名、判定閾値などの規則値 |
| normalization_common.py | 形式に依存しない小さな共通処理 |

たとえば図番の誤判定を直す場合はnormalization_2d.pyとnormalization_text.pyを確認します。材質コードを増やす場合は、まずdictionaries/initial-dictionaries.jsonの運用語彙か、normalization_material.pyの形式判定かを切り分けます。

## 3. タグ生成と辞書

| ファイル | 主な役割 |
|---|---|
| tagging.py | 共通属性と辞書照合結果から、根拠付きタグを生成 |
| dictionary_provider.py | 辞書の取得方法と7種別の契約 |
| seed_dictionaries.py | 同梱初期辞書の正本となる初期値 |
| configuration.py | Schema、正規化、タグ規則のバージョン |

語彙の追加だけで対応できる場合は、処理コードを変更せず運用辞書を更新します。正規化前の値の読み方や、タグ採用条件を変える場合だけコードを変更します。

## 4. C#の読み進め方

1. IcadExtraction.Runner/Program.csで対象コマンドの引数と処理順序を確認します。
2. IcadExtraction.SxNetで2Dまたは3Dの抽出クラスを確認します。
3. IcadExtraction.Contractsで出力DTOとJSON名を確認します。
4. 対応するcsharp/testsのテストで既存条件を確認します。
5. DTOやJSON名を変更する場合は、schemasとexamplesも同時に更新します。

Windows agentの通信処理はIcadExtraction.Runner/WindowsExtractionAgent.csにあります。ICADからの抽出規則とHTTP通信を混ぜず、通信だけを変更する場合はこのファイルを中心に確認します。

## 5. 変更後に確認すること

| 変更内容 | 最低限の確認 |
|---|---|
| Python正規化 | tests/python、2D／3Dのexamples/results、対象Schema |
| タグ規則・辞書 | derived_tagsの値・evidence・confidence・reason |
| C# DTO・JSON名 | C#テスト、C# raw Schema、2D／3D raw例 |
| ICAD抽出 | 対応するICAD版とsxnet.dll、2D／3Dの実行結果、標準エラー |
| Windows agent | claim、heartbeat、complete、failとジョブ所有者 |
| PowerShell | Get-Help .\scripts\対象スクリプト.ps1 -Full、-ValidateOnlyがある処理は設定確認 |

不明な値を推測で補完したり、エラー後に空の結果で続行したりしないでください。入力、抽出候補、警告、最終タグを順に確認すると、どの段階で差が生じたかを切り分けられます。
