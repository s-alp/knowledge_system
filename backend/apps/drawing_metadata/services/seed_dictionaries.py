from __future__ import annotations


CUSTOMER_KEYWORDS = {
    "コマツ小山": ["コマツ小山", "komatsu koyama"],
    "広島アルミ": ["広島アルミ", "hiroshima alumi"],
    "澁谷工業": ["澁谷工業", "shibuya"],
}

EQUIPMENT_CATEGORY_KEYWORDS = {
    "ガントリー": ["ガントリー", "gantry"],
    "治具": ["治具", "jig"],
    "ロボット": ["ロボット", "robot"],
}

MAKER_KEYWORDS = {
    "SMC": ["smc"],
}

SPEC_KEYWORDS = {
    "SES": ["ses"],
}

MATERIAL_CLASSIFICATION_RULES = {
    "SUS304": {"status": "formal", "aliases": ["SUS304", "ＳＵＳ３０４"]},
    "SUS316": {"status": "formal", "aliases": ["SUS316", "ＳＵＳ３１６"]},
    "SUS440C": {"status": "formal", "aliases": ["SUS440C", "ＳＵＳ４４０Ｃ"]},
    "SUS": {
        "status": "formal",
        "aliases": ["SUS", "ＳＵＳ", "03ステンレス鋼", "04ステンレス鋼", "06ステンレス鋼", "ステンレス鋼", "ステンレス鋼材", "ステンレス鋼(機械加工)"],
    },
    "SS400": {
        "status": "formal",
        "aliases": ["SS400", "ＳＳ４００", "一般構造用鋼", "一般構造用鋼_MISUMIFA", "一般構造用圧延鋼材", "一般構造用圧延鋼材(機械加工)"],
    },
    "S45C": {"status": "formal", "aliases": ["S45C", "Ｓ４５Ｃ", "S45C相当"]},
    "炭素鋼": {"status": "formal", "aliases": ["00炭素鋼", "炭素鋼"]},
    "S65C": {"status": "formal", "aliases": ["S65C", "Ｓ６５Ｃ"]},
    "SPCC": {"status": "formal", "aliases": ["SPCC", "ＳＰＣＣ", "冷間圧延鋼板"]},
    "SUS303": {"status": "formal", "aliases": ["SUS303", "ＳＵＳ３０３"]},
    "FC300": {"status": "formal", "aliases": ["FC300", "ＦＣ３００"]},
    "FC250": {"status": "formal", "aliases": ["FC250", "ＦＣ２５０"]},
    "A5052P": {"status": "formal", "aliases": ["A5052P", "A5052", "AL", "Ａ５０５２Ｐ", "Ａ５０５２", "ＡＬ", "アルミ板", "アルミニウム板"]},
    "13クロム系ステンレス": {"status": "formal", "aliases": ["13クロム系ステンレス", "13クロム系ステンレス_MISUMIFA"]},
    "合金工具鋼": {"status": "formal", "aliases": ["合金工具鋼"]},
    "ねずみ鋳鉄": {"status": "formal", "aliases": ["ねずみ鋳鉄"]},
    "PPS": {"status": "formal", "aliases": ["PPS", "ＰＰＳ", "ポリフェニレンサルファイド樹脂"]},
    "PVC": {"status": "formal", "aliases": ["PVC", "ＰＶＣ", "ポリ塩化ビニル"]},
    "H-PVC": {"status": "formal", "aliases": ["H-PVC", "Ｈ－ＰＶＣ", "硬質塩化ビニル"]},
    "PTFE": {"status": "formal", "aliases": ["PTFE", "ＰＴＦＥ", "テフロン(フッ素樹脂)", "フッ素樹脂"]},
    "PET": {"status": "formal", "aliases": ["PET", "ＰＥＴ", "ポリエチレンテレフタレート"]},
    "PETG": {"status": "formal", "aliases": ["PETG", "ＰＥＴＧ"]},
    "POM": {"status": "formal", "aliases": ["POM", "ＰＯＭ"]},
    "PP": {"status": "formal", "aliases": ["PP", "ＰＰ", "ポリプロピレン"]},
    "NBR": {"status": "formal", "aliases": ["NBR", "ＮＢＲ", "ニトリルゴム"]},
    "EPDM": {"status": "formal", "aliases": ["EPDM", "ＥＰＤＭ", "エチレンプロピレンゴム"]},
    "FKM": {"status": "formal", "aliases": ["FKM", "ＦＫＭ", "フッ素ゴム(バイトン)"]},
    "AU": {"status": "formal", "aliases": ["AU", "ＡＵ", "ウレタンゴム"]},
    "SI": {"status": "formal", "aliases": ["SI", "ＳＩ", "シリコンゴム"]},
    "ZZZ": {"status": "unresolved", "aliases": ["ZZZ", "ＺＺＺ"]},
    "75": {"status": "unresolved", "aliases": ["75", "７５"]},
    "CDQ": {"status": "unresolved", "aliases": ["CDQ", "ＣＤＱ", "CDQSB20M"]},
    "RM": {"status": "excluded", "aliases": ["RM", "ＲＭ"]},
    "ZZ購入品": {"status": "excluded", "aliases": ["ZZ購入品", "LMレール", "LMブロック"]},
}
