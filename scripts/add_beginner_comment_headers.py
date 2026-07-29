"""自作ソースの冒頭へ、初心者が役割を把握するための日本語説明を一括追加する。

大量のファイルへ同じ形式のヘッダーを安全に加えるための保守用スクリプトである。
既に日本語ヘッダーがあるファイルは変更せず、改行コードとUTF-8 BOMも維持する。
個々の難しい判断理由はこのスクリプトで自動生成せず、対象コード内へ手作業で補う。
"""

from __future__ import annotations

import re
from pathlib import Path

from audit_beginner_source_comments import _comment_lines, _tracked_files


REPO_ROOT = Path(__file__).resolve().parents[1]

CSHARP_PURPOSES = {
    "CliArgumentsParserTests": "Runnerへ渡すコマンド名とオプションの解析規則を検証する",
    "ExtractionConditionOptions": "2D・3D抽出で有効にする走査条件を既定値とJSON指定から組み立てる",
    "ExtractionConditionOptionsTests": "抽出条件の既定値とJSON上書きが想定どおりに合成されることを検証する",
    "GeometryMapper": "SXNETが返す2D図形を文字・寸法・公差・溶接記号などの共通JSON形式へ変換する",
    "GeometryMapperTests": "代表的なSXNET図形が共通JSON項目へ正しく変換されることを検証する",
    "Icad2DExtractor": "ICAD図面の全ビュー・レイヤー・印刷枠と2D要素を読み取り専用で抽出する",
    "Icad2DPrintProbe": "ICADの印刷設定と印刷枠APIを調査し、利用可能な値を診断情報として返す",
    "Icad3DExtractor": "ICADモデルのパーツ構成・材質・質量・付加情報とプレビュー資産を抽出する",
    "IcadCadFormatExporter": "ICADモデルをDXFまたはSTEPへ変換し、変換結果と警告を共通形式で返す",
    "IcadCadFormatExporterTests": "CAD形式ごとのSXNET出力種別と変換引数が正しく選ばれることを検証する",
    "IcadMassPropertyProbe": "SXNETの複数API候補から質量・重心・慣性モーメントを安全に取得する",
    "IcadMassPropertyProbeTests": "質量特性のAPI差異や欠損値を安全に扱えることを検証する",
    "IcadMaterialProbe": "トップパーツと構成パーツから材質候補を収集し、取得元とともに返す",
    "IcadMaterialProbeTests": "材質候補の取得と重複除去が想定どおりに動くことを検証する",
    "IcadPresenceDetector": "1つのICADファイルに2D実体と3D実体が存在するかを判定する",
    "IcadPreviewAssetExporter": "3D表示用STLを作業領域へ出力し、配信に必要なメタデータを作る",
    "IcadProcessStarter": "ICADの起動状態を判定し、必要な場合だけ起動して所有関係を記録する",
    "IcadWindowCloser": "自動起動したICADへ保存しない終了操作を送り、既存起動分を保護する",
    "IcadWindowCloserTests": "保存確認ダイアログとICAD終了操作の選択規則を検証する",
    "Models": "C# RunnerとDjango間で受け渡すCLI入力・抽出JSON・警告の公開契約を定義する",
    "PartTreeFlattener": "SXNETの階層パーツツリーを親子関係と階層パスを保った一覧へ変換する",
    "PartTreeFlattenerTests": "パーツツリーの親子関係・深さ・外部参照判定を検証する",
    "PrintAreaClassifier": "2D要素の代表座標が印刷枠の内側・外側・不明のどれかを判定する",
    "PrintAreaClassifierTests": "境界を含む印刷枠内外判定と座標欠損時の扱いを検証する",
    "Program": "IcadExtraction.RunnerのCLI入口として、抽出・変換・診断・常駐agentへ処理を振り分ける",
    "ReflectionHelpers": "SXNETのバージョン差を吸収し、実行時に存在するプロパティやメソッドから値を読む",
    "RunnerSmokeTests": "Runnerのコマンド振り分けと主要な失敗応答を実行入口から検証する",
    "SchemaVersions": "Django側が判定できるよう、C#抽出JSONのスキーマ版番号を一か所で定義する",
    "SxNetCommandController": "SXNETへキャンセル・クリアなどの制御コマンドを送る小さな境界を提供する",
    "SxNetInputFileLease": "長いパスや非ASCIIパスを短い一時領域へ退避し、SXNET入力を安全に貸し出す",
    "SxNetOpenContext": "SXNETアセンブリの読込、モデルの読み取り専用オープン、後片付けを一つの寿命で管理する",
    "SxNetRuntimeGuard": "指定DLLが必要なSXNET型を持つか検証してから抽出処理へ渡す",
    "WindowsExtractionAgent": "Windows上でDjangoの抽出ジョブを取得し、C# Runner実行と結果返却を繰り返す",
}

CONTRACT_CLASS_PURPOSES = {
    "CliCommand": "CLIで指定されたコマンド名と、--名前 値形式のオプションを保持します",
    "CliArgumentsParser": "文字列配列のCLI引数を、Runner内部で扱うCliCommandへ変換します",
    "WarningPayload": "処理を中断しない不足や制約を、機械判定用コードと説明文で返します",
    "TopPartPayload": "ICADモデルの最上位パーツに設定された名称・コメント・付加情報を表します",
    "PartPayload": "3Dパーツツリーの1ノードを、親子関係と外部参照状態を保って表します",
    "RawExtract3DPayload": "3D抽出で得た未正規化データをまとめ、取得できた値だけを保持します",
    "MaterialPayload": "SXNETから取得した材質候補と、その候補が属するパーツを表します",
    "ModelInfoPayload": "ICADモデル全体の名称・コメント・付加情報などの基本情報を表します",
    "MassPropertyPayload": "モデルまたはパーツの質量・重心・慣性モーメントを表します",
    "ViewerAssetPayload": "2D/3Dビューワーへ渡すプレビュー資産の場所・形式・生成状態を表します",
    "TextPayload": "2D図面上の文字要素を、表示内容・座標・ビュー・レイヤーとともに表します",
    "DimensionPayload": "寸法値と上下公差、配置先ビュー・レイヤーなどの抽出結果を表します",
    "WeldNotePayload": "溶接記号または溶接注記の候補を、取得元情報付きで表します",
    "BalloonPayload": "部品番号などを示すバルーン要素と、その図面上の位置を表します",
    "TolerancePayload": "幾何公差などの公差要素を、種別・値・配置情報とともに表します",
    "Referenced2DPartPayload": "2D図面から参照される外部部品と、参照先の識別情報を表します",
    "GeometryPrimitivePayload": "線・円・ハッチングなどの2D図形を共通形式で表します",
    "ViewSheetPayload": "ICADの1ビューについて、名称・種類・配置番号・要素数を表します",
    "PrintFramePayload": "印刷対象となる矩形範囲をICADモデル空間の座標で表します",
    "LayerPayload": "2Dレイヤーの番号・名称・表示状態・編集状態を表します",
    "RawExtract2DPayload": "2D抽出で得た要素・ビュー・レイヤー・印刷枠をまとめます",
    "SourceFilePayload": "抽出対象ファイルの表示名・元パス・サイズ・ハッシュを表します",
    "ExtractionEnvelope": "1回の抽出結果として、抽出種別・rawデータ・警告・実行条件をまとめます",
    "PreviewAssetOptions": "ビューワー資産の出力先と公開URLを組み立てる条件を表します",
    "DetectionEvidence2DPayload": "2D実体の有無を判断した根拠件数を表します",
    "DetectionEvidence3DPayload": "3D実体の有無を判断した根拠件数を表します",
    "DetectionPayload": "1ファイルに2D/3Dのどちらが存在するかと判定根拠を表します",
    "DetectionEnvelope": "2D/3D存在判定の結果と、判定中に発生した警告をまとめます",
    "PlotterPayload": "ICADに登録されたプロッター名・用紙・向きなどの印刷設定を表します",
    "PrintProbePayload": "印刷API調査で取得できたプロッターと印刷枠をまとめます",
    "PrintProbeEnvelope": "印刷設定調査の最上位結果と警告をまとめます",
}

DJANGO_SERVICE_PURPOSES = {
    "composition": "2D・3Dの正規化結果と手動補正を、最終表示・保存用の一つの結果へ合成する",
    "dictionaries": "DBで編集できるタグ辞書を読み込み、未登録時だけ初期辞書を利用する",
    "display": "保存済み抽出結果を、画面とAPIが扱いやすい表示用データへ整形する",
    "drawing_scope": "登録図面を共有対象・検証対象などの運用スコープへ分類する",
    "extraction_runner": "DjangoからC# Runnerを起動し、タイムアウト・一時入力・結果JSONを管理する",
    "failure_diagnostics": "長い抽出エラーを保存用全文と画面用要約へ分け、再確認情報を作る",
    "generic_cad_extractor": "STEPとDXFをPythonだけで解析し、ICAD抽出と同じraw形式へ変換する",
    "handoff_dashboard": "創屋引継ぎ画面で使う登録数・ジョブ状態・API一覧を集約する",
    "icad_entities": "ICADパーツ構成から製品・装置・ユニットと部品の表示情報を組み立てる",
    "knowledge_payload_preview": "ナレッジシステムへ渡す対象別タグ・属性payloadを読み取り専用で確認できる形へする",
    "normalization": "C#・STEP・DXFのraw抽出を、検索・タグ生成に使う共通canonical形式へ正規化する",
    "overrides": "自動抽出結果へ利用者の属性修正・タグ追加削除を再適用する",
    "path_constraints": "DB表示名とSXNET入力パスの長さ・文字種制約を判定する",
    "persistence": "抽出結果、snapshot、タグ、レビュー状態をトランザクション内で保存する",
    "rag_payload": "確定した図面メタデータをRAG投入用の小さなpayloadへ変換する",
    "reextract_planner": "未抽出や診断不足の状態から、必要な再抽出モードと条件を決める",
    "seed_dictionaries": "タグ正規化で最初に使う客先・案件・材質などの初期辞書を定義する",
    "source_formats": "拡張子からICAD・STEP・DXFの形式と2D/3D抽出対象を判定する",
    "tag_automation_settings": "タグ自動取得画面へ返す実行条件・採用規則・対象範囲を組み立てる",
    "tag_builder": "canonical属性から採用可能なタグを根拠・信頼度・理由付きで生成する",
    "viewer_preview": "2DメタデータSVGと3D資産URLを既存ビューワーのopen契約へ接続する",
    "worker_status": "抽出workerとWindows agentの生存状態を記録し、画面用状態へ判定する",
}

FRONTEND_PURPOSES = {
    "App": "URLのdrawingIdからbootstrapを読み込み、2D・3D・設定・対象物画面を切り替える",
    "client": "フロントから呼ぶDjango APIを一か所へ集約し、成功・失敗の応答形をそろえる",
    "DrawingEntryPanel": "drawingId、URL、ローカルファイルからビューワーを開く開発用入口を表示する",
    "DrawingKnowledgeDetail": "図面bootstrapのタグ・属性・関連情報を表示用の共通部品へ渡す",
    "drawingKnowledge": "bootstrap内のナレッジ情報を、欠損に強い画面表示モデルへ変換する",
    "DrawingOverviewPanel": "図面の基本情報・属性・備考を2D/3D共通の骨格で表示する",
    "DrawingSupplementPanels": "タグ根拠、改訂履歴、関連情報などの補助パネルを表示する",
    "EntityPages": "製品・装置・ユニットと部品の一覧・詳細画面を共通入口から切り替える",
    "IconToolbarButton": "2D/3D操作アイコンの見た目とアクセシビリティ属性を共通化する",
    "IcadEntityPages": "ICADの構成情報から作った製品・装置・ユニットと部品を一覧・詳細表示する",
    "IcadExtractionReviewPage": "図面登録、2D/3D抽出、失敗確認、手動補正、レビュー確定を一画面で扱う",
    "LicensePanel": "ビューワーで使用する外部ライブラリのライセンス導線を表示する",
    "LoadingNotice": "読込・変換・描画の進行段階に応じた共通メッセージを表示する",
    "LocalFilePicker": "ブラウザーのファイル選択とキャンセル判定を共通化する",
    "MetadataBar": "ファイル名・形式・ページ数などの軽いメタ情報を横並びで表示する",
    "pdfAdapter": "PDF.jsを2Dビューワー共通adapterへ包み、ページ描画と解放を担当する",
    "rasterAdapter": "JPEGなどの単一画像を2Dビューワー共通adapterとして扱う",
    "TagAutomationSettingsPage": "タグ辞書、自動取得規則、抽出管理、引継ぎAPI情報を設定画面へ表示する",
    "ThreeDViewerScene": "Three.jsでSTL/GLBを描画し、カメラ・断面・輪郭・描画完了を管理する",
    "tiffAdapter": "DjangoがPNG化したTIFF各ページを2Dビューワー共通adapterへまとめる",
    "TwoDViewerCanvas": "2Dページのcanvas描画、パン、ズーム、回転、高解像度差し替えを管理する",
    "types": "同じ機能フォルダー内で共有するTypeScriptのデータ型を定義する",
    "useDrawingBootstrap": "drawingId変更に合わせてbootstrap APIを読み込み、状態とエラーを管理する",
    "useKnowledgeEntities": "対象物一覧・詳細APIの読込状態をReact hookとして管理する",
    "useViewer2DDocument": "2Dソース形式に合うadapterを作り、切替時に古い資源を解放する",
    "useViewer3DJob": "3D変換ジョブが完了するまでAPIを定期確認し、画面状態へ反映する",
    "useViewerSourceLoader": "2D/3D共通のURL・アップロード開始処理と読込段階を管理する",
    "Viewer2DPage": "2Dビューワー画面の入力、ページ、表示状態、ツールバーを統括する",
    "Viewer2DPreviewPane": "2Dツールバーとcanvasを結び、表示領域の大きさと操作状態を管理する",
    "Viewer2DToolbar": "2Dのページ移動、拡大縮小、回転、リセット操作を提供する",
    "Viewer3DPage": "3Dジョブ、描画Scene、断面・輪郭操作、完了表示を統括する",
    "Viewer3DSectionControls": "3D断面の軸・位置・有効状態を操作するUIを提供する",
    "viewer2dState": "2D表示のズーム・回転・パンを純粋な状態遷移として計算する",
    "viewer3dState": "3D断面表示の軸・位置・有効状態を純粋な状態遷移として計算する",
    "Viewer3DToolbar": "3Dの拡大縮小、断面、輪郭、リセット操作を提供する",
    "ViewerSourcePanel": "2D/3D共通のURL入力とローカルファイル選択を表示する",
}

SCRIPT_ACTIONS = {
    "analyze": "入力データを分析し、原因や分布を確認する",
    "append": "既存成果物へ検証結果を追記する",
    "audit": "保存済みデータや成果物が要件を満たすか監査する",
    "build": "複数の入力から共有・引継ぎ用成果物を組み立てる",
    "check": "ローカル環境の接続先と応答を確認する",
    "compare": "二つの抽出結果を比較し、差分を明示する",
    "convert": "CADデータを変換し、変換後の取得内容まで監査する",
    "copy": "許可された対象だけを別の作業領域へコピーする",
    "evaluate": "検証結果を正解条件と照合し、精度を評価する",
    "extract": "指定された元資料から必要なデータだけを抽出する",
    "generate": "入力データから報告書や検証用成果物を生成する",
    "inspect": "DB・JSON・図面などの中身を変更せず確認する",
    "list": "利用可能な候補を一覧表示する",
    "probe": "限定したAPIやデータ経路を試し、実値を確認する",
    "process": "抽出ジョブを限定回数だけ処理して状態を確認する",
    "requeue": "条件に合う抽出ジョブを再実行待ちへ戻す",
    "run": "決められた検証または再抽出手順を順番に実行する",
    "start": "必要な環境変数を確認して常駐プロセスを起動する",
    "summarize": "大量の抽出結果を件数と代表例へ要約する",
    "sync": "正本から配布用または許可済みツリーへ内容を同期する",
    "update": "既存のmanifestや成果物を最新の抽出結果へ更新する",
    "validate": "成果物の契約・必須項目・値の整合性を検証する",
}

LARGE_SCRIPT_PURPOSES = {
    "convert_and_audit_all_sample_icd_dxf": "共有ICADを全件DXFへ変換し、文字・寸法・公差・溶接などの取得率を監査する",
    "convert_and_audit_all_sample_icd_step": "共有ICADを全件STEPへ変換し、製品名・構成・材質・質量の保持率を監査する",
    "generate_current_system_pdm_csv": "現行PDMデータを外部共有可能なCSVへ整形し、列定義と件数を確認する",
    "generate_exhibition_pdm_csv": "展示説明用のPDM一覧CSVをExcel入力から組み立て、関連項目をそろえる",
}


def _purpose_for(relative_path: Path) -> str:
    """パスとファイル名から、初心者が最初に知るべき責務を日本語で返す。"""

    stem = relative_path.stem
    path_text = relative_path.as_posix()

    if relative_path.suffix == ".cs":
        return CSHARP_PURPOSES.get(
            stem,
            f"{stem}に関するC#処理を実装し、呼び出し側へ結果または明示的なエラーを返す",
        )
    if "/tests/" in f"/{path_text}" or ".test." in relative_path.name:
        target = stem.replace(".test", "")
        return f"{target}の正常系・境界値・失敗時の挙動が変わらないことを自動テストで確認する"
    if path_text.startswith("scripts/") or "/scripts/" in path_text:
        if stem in LARGE_SCRIPT_PURPOSES:
            return LARGE_SCRIPT_PURPOSES[stem]
        action = SCRIPT_ACTIONS.get(stem.split("_", maxsplit=1)[0], "限定した保守・検証作業を実行する")
        return f"`{stem}`として{action}補助スクリプトである"
    if path_text.startswith("backend/"):
        if "/services/" in path_text:
            return DJANGO_SERVICE_PURPOSES.get(
                stem,
                f"図面メタデータの{stem}に関する業務処理をDjangoのservice層へ閉じ込める",
            )
        if "/management/commands/" in path_text:
            return f"Django管理コマンド`{stem}`の入口として、対象選択・実行・結果表示をまとめる"
        if "/api/" in path_text:
            return f"図面メタデータAPIの{stem}を定義し、HTTP入出力をservice層へ接続する"
        if relative_path.name == "settings.py":
            return "Django backendの環境変数・DB・アプリ・ログなどの実行設定を定義する"
        return f"Django backendの{stem}に関する入口またはデータ定義を提供する"
    if "/frontend/src/" in path_text:
        purpose = FRONTEND_PURPOSES.get(stem)
        if purpose:
            return purpose
        return f"{stem}に関する画面表示・状態・型のいずれか一つの責務をReact側で担当する"
    if "/backend/apps/viewer/" in path_text:
        return f"2D/3Dビューワーバックエンドの{stem}を担当し、API層と変換・保存処理を分離する"
    if "viewer_backend" in path_text:
        return f"2D/3Dビューワー用Djangoプロジェクトの{stem}設定を定義する"
    return f"{stem}に関する限定した処理を担当し、他の層から再利用できる形で提供する"


def _header_lines(relative_path: Path) -> list[str]:
    """言語に合うコメント記号で、責務・読み方・保守上の注意を3行にまとめる。"""

    purpose = _purpose_for(relative_path)
    second = "初めて読むときは、公開されている入口から呼び出し先を順に追う。"
    third = "外部I/Oや状態変更は境界に寄せ、失敗時は既定値で続行せず呼び出し元へ伝える。"

    if ".test." in relative_path.name or "/tests/" in f"/{relative_path.as_posix()}":
        second = "テスト名は利用者から見た前提と期待結果を表し、失敗時は対象実装の契約違反を示す。"
        third = "外部API・時刻・ファイル操作はfixtureやmockへ置き換え、再現可能性を保つ。"

    if relative_path.suffix == ".py":
        # Python では既存のモジュール docstring と競合しない行コメントにする。
        # 文字列リテラルを二つ並べると、後続の future import が構文エラーになるためである。
        return [f"# このファイルは、{purpose}。", f"# {second}", f"# {third}", ""]
    marker = "#" if relative_path.suffix == ".ps1" else "//"
    return [
        f"{marker} このファイルは、{purpose}。",
        f"{marker} {second}",
        f"{marker} {third}",
        "",
    ]


def _decode_source(raw: bytes) -> tuple[str, bool, str]:
    """元ファイルのBOMと改行コードを記録し、追記以外の差分を作らない。"""

    has_bom = raw.startswith(b"\xef\xbb\xbf")
    if has_bom:
        raw = raw[3:]
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    return text, has_bom, newline


def _insert_header(relative_path: Path) -> bool:
    """既存ヘッダーを尊重し、必要なファイルだけへ説明を追加する。"""

    absolute_path = REPO_ROOT / relative_path
    raw = absolute_path.read_bytes()
    text, has_bom, newline = _decode_source(raw)
    lines = text.splitlines()
    comments = _comment_lines(lines, relative_path.suffix.lower())
    if any(line_number <= 20 for line_number, _ in comments):
        return False

    header = newline.join(_header_lines(relative_path))
    if relative_path.suffix == ".py" and lines and lines[0].startswith("#!"):
        updated = lines[0] + newline + header + newline.join(lines[1:])
    else:
        updated = header + text

    encoded = updated.encode("utf-8")
    if has_bom:
        encoded = b"\xef\xbb\xbf" + encoded
    absolute_path.write_bytes(encoded)
    return True


def _insert_csharp_class_summaries(relative_path: Path) -> bool:
    """C#の型宣言へ、その型が何を担当するかを示すXMLコメントを追加する。"""

    if relative_path.suffix != ".cs":
        return False

    absolute_path = REPO_ROOT / relative_path
    raw = absolute_path.read_bytes()
    text, has_bom, newline = _decode_source(raw)
    class_pattern = re.compile(
        r"^(?P<indent>\s*)(?P<access>public|internal)\s+"
        r"(?:(?:sealed|static|abstract)\s+)*class\s+(?P<name>[A-Za-z0-9_]+)",
        re.MULTILINE,
    )
    changed = False

    def add_summary(match: re.Match[str]) -> str:
        nonlocal changed
        line_start = match.start()
        previous_text = text[max(0, line_start - 300):line_start]
        if "/// <summary>" in previous_text.split(newline + newline)[-1]:
            return match.group(0)

        class_name = match.group("name")
        purpose = CONTRACT_CLASS_PURPOSES.get(class_name)
        if not purpose:
            purpose = CSHARP_PURPOSES.get(
                class_name,
                f"{class_name}に関する処理と状態を一つの責務としてまとめます",
            )
        indent = match.group("indent")
        changed = True
        return (
            f"{indent}/// <summary>{newline}"
            f"{indent}/// {purpose}。{newline}"
            f"{indent}/// </summary>{newline}"
            f"{match.group(0)}"
        )

    updated = class_pattern.sub(add_summary, text)
    if not changed:
        return False

    encoded = updated.encode("utf-8")
    if has_bom:
        encoded = b"\xef\xbb\xbf" + encoded
    absolute_path.write_bytes(encoded)
    return True


def main() -> int:
    """監査対象を一巡し、追加したファイル数を表示する。"""

    changed: list[str] = []
    class_documented: list[str] = []
    for relative_path in _tracked_files(REPO_ROOT):
        if _insert_header(relative_path):
            changed.append(relative_path.as_posix())
        if _insert_csharp_class_summaries(relative_path):
            class_documented.append(relative_path.as_posix())

    print(f"初心者向けヘッダーを追加したファイル数: {len(changed)}")
    for path in changed:
        print(f"- {path}")
    print(f"C#型のXML説明を追加したファイル数: {len(class_documented)}")
    for path in class_documented:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
