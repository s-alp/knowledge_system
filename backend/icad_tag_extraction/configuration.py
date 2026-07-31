"""Djangoに依存しない抽出・正規化・タグ生成のバージョン設定を定義する。

創屋側へ切り出すコアでは、Django settingsや環境変数を直接参照しない。
呼び出し側が本設定を明示的に渡すことで、同じ入力をどの実行環境でも同じ規則で処理できる。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionConfig:
    """C# raw契約からタグ生成までのバージョンを一括して保持する。

    値は生成結果へ記録される契約識別子であり、空文字では再現条件を特定できないため拒否する。
    このクラスは設定値だけを保持し、ファイル・DB・外部APIへのアクセスは行わない。
    """

    schema_version: str
    normalizer_version: str
    tag_rule_version: str

    def __post_init__(self) -> None:
        for field_name in ("schema_version", "normalizer_version", "tag_rule_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name}は空でない文字列を指定してください。")


# 現行の正本バージョン。Django adapterはsettingsの値から同じ型を作り、
# 独立CLIはこの値を既定契約として使用する。
DEFAULT_CONFIG = ExtractionConfig(
    schema_version="1.1.0",
    normalizer_version="1.2.0",
    tag_rule_version="1.1.0",
)
