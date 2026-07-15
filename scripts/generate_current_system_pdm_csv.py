from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SOURCE_DIR = Path(
    r"C:\Users\s-iwata\Desktop\knowledge_system\ナレッジシステムお披露目会向け\お披露目会_作成資料_20260601\pdm_csv_exhibition_2026-06-03\20260603_ナレッジシステム用CSV"
)
OUTPUT_PARENT = Path(
    r"C:\Users\s-iwata\Desktop\knowledge_system\ナレッジシステムお披露目会向け\お披露目会_作成資料_20260601\pdm_csv_current_system_2026-06-05"
)
OUTPUT_DIR = OUTPUT_PARENT / "20260605_ナレッジシステム用CSV"
ZIP_PATH = OUTPUT_PARENT / "20260605_ナレッジシステム用CSV.zip"


EXISTING_MASTERS = {
    "project_status": {"未着手", "着手中", "検証中", "完了"},
    "product_status": {"設計中", "承認待ち", "製作中", "完了"},
    "product_category": {"加工機", "コンベア", "搬送装置", "組立装置", "検査装置", "治具", "制御盤"},
    "product_type": {"標準品", "特注品", "試作"},
    "product_phase": {"企画", "設計", "製造・組立", "検査", "客先立ち上い", "据え付け", "保守"},
    "product_drive": {"ベルト", "ローラー", "チェーン"},
    "product_power": {"AC100V", "AC200V", "三相200V"},
    "part_status": {"下書き", "設計中", "レビュー待ち", "承認待ち", "承認済み", "試作", "量産", "使用中", "廃止予定", "廃止"},
    "part_category": {"ボルト", "ナット", "ワッシャー", "ギア", "ベアリング", "モーター", "センサー", "基板", "コネクタ", "樹脂部品"},
    "part_material": {"SS400", "SUS304", "アルミ", "樹脂"},
    "part_surface": {"塗装", "メッキ", "アルマイト"},
    "drawing_type": {"部品図", "サブアセンブリ図", "全体組立図", "ユニット図"},
    "drawing_usage": {"設計検討", "製造", "検査", "購買・外注", "保守", "承認用", "説明用"},
    "drawing_standard": {"JIS", "ISO", "社内規格"},
    "document_status": {"test"},
    "document_type": {"test"},
    "role_master": {"部長"},
    "department_master": {"管理部"},
    "user_permission": {"管理者"},
}


def read_csv(name: str) -> list[dict[str, str]]:
    path = SOURCE_DIR / name
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def normalize_phone(index: int) -> str:
    return f"00-0000-{index:04d}"


def customer_short_name(company_name: str) -> str:
    return (
        company_name.replace("株式会社", "")
        .replace("工業", "")
        .replace("システム", "")
        .replace("ファクトリーオート", "FA")
        .replace("ラインテック", "LT")
    )[:12]


def build_customer_rows(customers: list[dict[str, str]], contacts: list[dict[str, str]]) -> list[dict[str, str]]:
    contact_map = {row["顧客名"]: row for row in contacts}
    rows: list[dict[str, str]] = []
    for index, customer in enumerate(customers, start=1):
        contact = contact_map[customer["顧客名"]]
        rows.append(
            OrderedDict(
                [
                    ("顧客名", customer["顧客名"]),
                    ("顧客名（カナ）", "テスト"),
                    ("顧客名（略称）", customer_short_name(customer["会社名"])),
                    ("ランク", "A"),
                    ("担当者", contact["顧客担当者"]),
                    ("備考", customer["備考"]),
                    ("ステータス", "有効"),
                    ("郵便番号", "000-0000"),
                    ("住所1（都道府県・市区町村）", "テスト県テスト市"),
                    ("住所2（番地）", f"{index}-1-1"),
                    ("住所3（建物名など）", "テストビル"),
                    ("TEL", normalize_phone(index)),
                    ("FAX", normalize_phone(index + 100)),
                    ("WEBサイト", "https://example.com"),
                    ("請求先名", "テスト請求先"),
                    ("請求先住所", "テスト請求先住所"),
                ]
            )
        )
    return rows


def build_contact_rows(contacts: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        OrderedDict(
            [
                ("顧客名", row["顧客名"]),
                ("顧客担当者", row["顧客担当者"]),
                ("姓", row["姓"]),
                ("名", row["名"]),
                ("メールアドレス", row["メールアドレス"]),
                ("部署", row["部署"]),
                ("役職", row["役職"]),
                ("備考", row["備考"]),
            ]
        )
        for row in contacts
    ]


def build_user_rows(users: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        OrderedDict(
            [
                ("姓", row["姓"]),
                ("名", row["名"]),
                ("メールアドレス", row["メールアドレス"]),
                ("権限", "管理者"),
                ("備考", row["備考"]),
            ]
        )
        for row in users
    ]


def build_role_rows(users: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = []
    for row in users:
        role = row["役職"]
        if role not in seen:
            seen.append(role)
    return [OrderedDict([("役職", role), ("備考", "展示会向け創作ユーザー役職")]) for role in seen]


def build_department_rows(users: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = []
    for row in users:
        department = row["部署"]
        if department not in seen:
            seen.append(department)
    return [OrderedDict([("部署", department), ("備考", "展示会向け創作ユーザー部署")]) for department in seen]


def build_user_profile_rows(users: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        OrderedDict(
            [
                ("ユーザー名", row["ユーザー名"]),
                ("会社名", row["会社名"]),
                ("部署", row["部署"]),
                ("役職", row["役職"]),
                ("備考", row["備考"]),
            ]
        )
        for row in users
    ]


def map_drawing_type(old_type: str, title: str) -> str:
    if old_type == "部品図":
        return "部品図"
    if "ユニット" in title:
        return "ユニット図"
    return "全体組立図"


def map_drawing_usage(mapped_type: str) -> str:
    if mapped_type == "部品図":
        return "製造"
    if mapped_type == "ユニット図":
        return "設計検討"
    return "説明用"


def map_material(value: str) -> str:
    if value in EXISTING_MASTERS["part_material"]:
        return value
    if value.startswith("SUS"):
        return "SUS304"
    if value.startswith("A") or value in {"アルミ", "A5052", "A6063"}:
        return "アルミ"
    if value in {"ABS", "POM", "MCナイロン", "ウレタン", "ポリカーボネート", "UHMW-PE"}:
        return "樹脂"
    return "SS400"


def map_surface(value: str) -> str:
    if value in EXISTING_MASTERS["part_surface"]:
        return value
    if any(key in value for key in ("メッキ", "クロメート", "ニッケル", "クロム")):
        return "メッキ"
    if any(key in value for key in ("塗装", "粉体", "黒塗装")):
        return "塗装"
    if "アルマイト" in value:
        return "アルマイト"
    return ""


def load_all() -> dict[str, list[dict[str, str]]]:
    return {
        "customers": read_csv("01_顧客.csv"),
        "contacts": read_csv("02_顧客担当者.csv"),
        "users": read_csv("03_ユーザー.csv"),
        "part_categories": read_csv("04_部品カテゴリマスタ.csv"),
        "projects": read_csv("05_プロジェクト.csv"),
        "products": read_csv("06_製品・装置・ユニット.csv"),
        "parts": read_csv("07_部品.csv"),
        "drawings": read_csv("08_図面.csv"),
        "documents": read_csv("09_文書.csv"),
        "project_products": read_csv("10_プロジェクト_製品紐づけ.csv"),
        "product_hierarchy": read_csv("11_製品_親子紐づけ.csv"),
        "product_parts": read_csv("12_製品_部品紐づけ.csv"),
        "project_drawings": read_csv("13_プロジェクト_図面紐づけ.csv"),
        "product_drawings": read_csv("14_製品_図面紐づけ.csv"),
        "part_drawings": read_csv("15_部品_図面紐づけ.csv"),
        "project_documents": read_csv("16_プロジェクト_文書紐づけ.csv"),
        "product_documents": read_csv("17_製品_文書紐づけ.csv"),
        "part_documents": read_csv("18_部品_文書紐づけ.csv"),
    }


def transform_drawings(drawings: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in drawings:
        mapped_type = map_drawing_type(row["図面タイプ"], row["タイトル"])
        rows.append(
            OrderedDict(
                [
                    ("図面番号", row["図面番号"]),
                    ("タイトル", row["タイトル"]),
                    ("種別", mapped_type),
                    ("所有者", row["所有者"]),
                    ("備考", row["備考"]),
                    ("用紙サイズ", row["用紙サイズ"]),
                    ("用途", map_drawing_usage(mapped_type)),
                    ("規格", "社内規格"),
                    ("重要度", "A" if mapped_type == "部品図" else "B"),
                    ("元ファイルパス", row["元ファイルパス"]),
                ]
            )
        )
    return rows


def transform_parts(parts: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in parts:
        rows.append(
            OrderedDict(
                [
                    ("部品番号", row["部品番号"]),
                    ("部品名", row["部品名"]),
                    ("カテゴリ", row["カテゴリ"]),
                    ("ステータス", row["ステータス"]),
                    ("担当者", row["担当者"]),
                    ("材質", map_material(row["材質"])),
                    ("表面処理", map_surface(row["表面処理"])),
                    ("使用環境", row["使用環境"]),
                    ("重要度", row["重要度"]),
                    ("仕入先", row["仕入先"]),
                    ("単位", row["単位"]),
                    ("単価", row["単価"]),
                    ("備考", row["備考"]),
                ]
            )
        )
    return rows


def collect_master_usage(data: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    used: list[tuple[str, str, str]] = []

    for row in data["projects"]:
        used.append(("プロジェクト", "ステータスマスタ", row["ステータス"]))
    for row in data["products"]:
        used.extend(
            [
                ("製品・装置・ユニット", "ステータスマスタ", row["ステータス"]),
                ("製品・装置・ユニット", "カテゴリマスタ", row["カテゴリ"]),
                ("製品・装置・ユニット", "種別マスタ", row["種別"]),
                ("製品・装置・ユニット", "フェーズマスタ", row["フェーズ"]),
                ("製品・装置・ユニット", "属性:駆動方式", row["駆動方式"]),
                ("製品・装置・ユニット", "属性:電源", row["電源"]),
            ]
        )
    for row in data["parts"]:
        used.extend(
            [
                ("部品", "ステータスマスタ", row["ステータス"]),
                ("部品", "カテゴリマスタ", row["カテゴリ"]),
                ("部品", "属性:材質", row["材質"]),
                ("部品", "属性:表面処理", row["表面処理"]),
            ]
        )
    for row in data["drawings"]:
        used.extend(
            [
                ("図面", "種別マスタ", row["種別"]),
                ("図面", "属性:用途", row["用途"]),
                ("図面", "属性:規格", row["規格"]),
            ]
        )
    for row in data["documents"]:
        used.extend(
            [
                ("文書", "ステータスマスタ", row["ステータス"]),
                ("文書", "種別マスタ", row["種別"]),
            ]
        )
    for row in data["user_rows"]:
        used.append(("ユーザー", "権限", row["権限"]))
    for row in data["role_rows"]:
        used.append(("ユーザー", "役職マスタ", row["役職"]))
    for row in data["department_rows"]:
        used.append(("ユーザー", "部署マスタ", row["部署"]))

    mapping = {
        ("プロジェクト", "ステータスマスタ"): EXISTING_MASTERS["project_status"],
        ("製品・装置・ユニット", "ステータスマスタ"): EXISTING_MASTERS["product_status"],
        ("製品・装置・ユニット", "カテゴリマスタ"): EXISTING_MASTERS["product_category"],
        ("製品・装置・ユニット", "種別マスタ"): EXISTING_MASTERS["product_type"],
        ("製品・装置・ユニット", "フェーズマスタ"): EXISTING_MASTERS["product_phase"],
        ("製品・装置・ユニット", "属性:駆動方式"): EXISTING_MASTERS["product_drive"],
        ("製品・装置・ユニット", "属性:電源"): EXISTING_MASTERS["product_power"],
        ("部品", "ステータスマスタ"): EXISTING_MASTERS["part_status"],
        ("部品", "カテゴリマスタ"): EXISTING_MASTERS["part_category"],
        ("部品", "属性:材質"): EXISTING_MASTERS["part_material"],
        ("部品", "属性:表面処理"): EXISTING_MASTERS["part_surface"],
        ("図面", "種別マスタ"): EXISTING_MASTERS["drawing_type"],
        ("図面", "属性:用途"): EXISTING_MASTERS["drawing_usage"],
        ("図面", "属性:規格"): EXISTING_MASTERS["drawing_standard"],
        ("文書", "ステータスマスタ"): EXISTING_MASTERS["document_status"],
        ("文書", "種別マスタ"): EXISTING_MASTERS["document_type"],
        ("ユーザー", "権限"): EXISTING_MASTERS["user_permission"],
        ("ユーザー", "役職マスタ"): EXISTING_MASTERS["role_master"],
        ("ユーザー", "部署マスタ"): EXISTING_MASTERS["department_master"],
    }

    existing_rows: list[dict[str, str]] = []
    addition_rows: list[dict[str, str]] = []
    seen = set()
    for entity, master_name, value in used:
        if not value:
            continue
        key = (entity, master_name, value)
        if key in seen:
            continue
        seen.add(key)
        target_rows = existing_rows if value in mapping[(entity, master_name)] else addition_rows
        target_rows.append(
            OrderedDict(
                [
                    ("対象", entity),
                    ("マスター種別", master_name),
                    ("値", value),
                    ("対応方針", "既存マスターを使用" if target_rows is existing_rows else "マスターへ追加"),
                ]
            )
        )
    return existing_rows, addition_rows


def build_readme() -> str:
    return "\n".join(
        [
            "# 現行システム寄せ PDM CSVセット",
            "",
            "## 目的",
            "",
            "- 現行の `/masters` と `顧客管理` で確認できた項目粒度に寄せて、再投入用に整理した CSV セットです。",
            "- 展示会向けの自然な名称は維持しつつ、既存マスターを使えるものはそのまま使い、足りない値だけを追加候補へ分離しています。",
            "",
            "## 方針",
            "",
            "- `01_顧客.csv` は現行の顧客登録フォームに合わせて、住所・請求先をダミー値で補完しています。",
            "- `03_ユーザー.csv` は `姓 / 名 / メールアドレス / 権限` に寄せています。",
            "- `04_役職マスタ.csv` と `05_部署マスタ.csv` を分け、`06_ユーザー補足情報.csv` で補足対応を持たせています。",
            "- 既存マスターで足りる値は `91_既存マスター利用値一覧.csv` に、追加したい値は `90_追加したいマスター値一覧.csv` に整理しています。",
            "",
            "## 注意点",
            "",
            "- `顧客` と `ユーザー` は、展示会向けセットから構造を寄せ直しています。",
            "- `文書ステータス / 文書種別 / 部品カテゴリ / 役職 / 部署` などは、現状マスターへ値追加が必要です。",
            "- 元の展示会向けセットは別フォルダに残しています。",
            "",
            "## 主なファイル",
            "",
            "- `01_顧客.csv`",
            "- `02_顧客担当者.csv`",
            "- `03_ユーザー.csv`",
            "- `04_役職マスタ.csv`",
            "- `05_部署マスタ.csv`",
            "- `06_ユーザー補足情報.csv`",
            "- `07_プロジェクト.csv`",
            "- `08_製品・装置・ユニット.csv`",
            "- `09_部品.csv`",
            "- `10_図面.csv`",
            "- `11_文書.csv`",
            "- `90_追加したいマスター値一覧.csv`",
            "- `91_既存マスター利用値一覧.csv`",
            "",
        ]
    )


def zip_output() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(OUTPUT_PARENT))


def main() -> None:
    src = load_all()

    customer_rows = build_customer_rows(src["customers"], src["contacts"])
    contact_rows = build_contact_rows(src["contacts"])
    user_rows = build_user_rows(src["users"])
    role_rows = build_role_rows(src["users"])
    department_rows = build_department_rows(src["users"])
    user_profile_rows = build_user_profile_rows(src["users"])
    part_rows = transform_parts(src["parts"])
    drawing_rows = transform_drawings(src["drawings"])
    document_rows = [
        OrderedDict(
            [
                ("タイトル", row["タイトル"]),
                ("種別", row["文書タイプ"]),
                ("ステータス", row["ステータス"]),
                ("所有者", row["所有者"]),
                ("文書概要", row["文書概要"]),
                ("備考", row["備考"]),
                ("タグ", row["タグ"]),
                ("元ファイルパス", row["元ファイルパス"]),
            ]
        )
        for row in src["documents"]
    ]

    current_data = {
        "projects": src["projects"],
        "products": src["products"],
        "parts": part_rows,
        "drawings": drawing_rows,
        "documents": document_rows,
        "user_rows": user_rows,
        "role_rows": role_rows,
        "department_rows": department_rows,
    }
    existing_master_rows, addition_master_rows = collect_master_usage(current_data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(OUTPUT_DIR / "01_顧客.csv", customer_rows)
    write_csv(OUTPUT_DIR / "02_顧客担当者.csv", contact_rows)
    write_csv(OUTPUT_DIR / "03_ユーザー.csv", user_rows)
    write_csv(OUTPUT_DIR / "04_役職マスタ.csv", role_rows)
    write_csv(OUTPUT_DIR / "05_部署マスタ.csv", department_rows)
    write_csv(OUTPUT_DIR / "06_ユーザー補足情報.csv", user_profile_rows)
    write_csv(OUTPUT_DIR / "07_プロジェクト.csv", src["projects"])
    write_csv(OUTPUT_DIR / "08_製品・装置・ユニット.csv", src["products"])
    write_csv(OUTPUT_DIR / "09_部品.csv", part_rows)
    write_csv(OUTPUT_DIR / "10_図面.csv", drawing_rows)
    write_csv(OUTPUT_DIR / "11_文書.csv", document_rows)
    write_csv(OUTPUT_DIR / "12_プロジェクト_製品紐づけ.csv", src["project_products"])
    write_csv(OUTPUT_DIR / "13_製品_親子紐づけ.csv", src["product_hierarchy"])
    write_csv(OUTPUT_DIR / "14_製品_部品紐づけ.csv", src["product_parts"])
    write_csv(OUTPUT_DIR / "15_プロジェクト_図面紐づけ.csv", src["project_drawings"])
    write_csv(OUTPUT_DIR / "16_製品_図面紐づけ.csv", src["product_drawings"])
    write_csv(OUTPUT_DIR / "17_部品_図面紐づけ.csv", src["part_drawings"])
    write_csv(OUTPUT_DIR / "18_プロジェクト_文書紐づけ.csv", src["project_documents"])
    write_csv(OUTPUT_DIR / "19_製品_文書紐づけ.csv", src["product_documents"])
    write_csv(OUTPUT_DIR / "20_部品_文書紐づけ.csv", src["part_documents"])
    write_csv(OUTPUT_DIR / "90_追加したいマスター値一覧.csv", addition_master_rows)
    write_csv(OUTPUT_DIR / "91_既存マスター利用値一覧.csv", existing_master_rows)

    readme = build_readme()
    (OUTPUT_DIR / "00_README.md").write_text(readme, encoding="utf-8")
    OUTPUT_PARENT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_PARENT / "00_README.md").write_text(readme, encoding="utf-8")

    zip_output()
    print(str(OUTPUT_DIR))


if __name__ == "__main__":
    main()
