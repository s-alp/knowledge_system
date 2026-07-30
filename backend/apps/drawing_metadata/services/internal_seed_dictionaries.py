"""当社内のDjango環境だけで使用する客先seedを定義する。

独立コアと創屋向けパッケージには実顧客名を含めない。既存Django環境では、
DB辞書が未投入の間も現行挙動を保つ必要があるため、本ファイルをadapter側だけで合成する。
本ファイルは創屋向けパッケージの収集対象外であり、外部へ配布しない。
"""

from __future__ import annotations


INTERNAL_CUSTOMER_KEYWORDS = {
    "コマツ小山": ["コマツ小山", "komatsu koyama"],
    "広島アルミ": ["広島アルミ", "hiroshima alumi"],
    "澁谷工業": ["澁谷工業", "shibuya"],
}

# 顧客固有規格も一般配布seedへ入れず、当社内adapterだけで既存挙動を保つ。
INTERNAL_SPEC_KEYWORDS = {
    "SES": ["ses"],
}
