"""独立コアの初期辞書をDjango側の既存importへ公開する互換adapter。

初期辞書の正本は`icad_tag_extraction.seed_dictionaries`であり、
Django側に同じ辞書を複製しないことで創屋配布版との規則差を防ぐ。
"""

from icad_tag_extraction.seed_dictionaries import *  # noqa: F403
