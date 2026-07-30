"""Django側の既存importへ社内用seedを公開する互換adapter。

一般辞書は独立コアを正本とし、実顧客を含む客先辞書だけは外部配布対象外の
`internal_seed_dictionaries`から合成する。
"""

from icad_tag_extraction.seed_dictionaries import *  # noqa: F403
from apps.drawing_metadata.services.internal_seed_dictionaries import (
    INTERNAL_CUSTOMER_KEYWORDS,
    INTERNAL_SPEC_KEYWORDS,
)


CUSTOMER_KEYWORDS = INTERNAL_CUSTOMER_KEYWORDS
SPEC_KEYWORDS = INTERNAL_SPEC_KEYWORDS
