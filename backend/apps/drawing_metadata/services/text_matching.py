from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# 1つの正規値あたりに保存する根拠の上限。監査には十分で、JSON肥大を防ぐ。
EVIDENCE_LIMIT_PER_VALUE = 5

_ASCII_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def normalize_text(value: str) -> str:
    """辞書照合用の正規化。NFKC で全角英数・半角カナを畳み、casefold で大小文字を吸収する。"""
    return unicodedata.normalize("NFKC", value).casefold()


def _ascii_pattern(candidate_norm: str) -> re.Pattern[str]:
    pattern = _ASCII_PATTERN_CACHE.get(candidate_norm)
    if pattern is None:
        # 英数字の並びの途中を拾わない（"ses" が "hoses" に一致しない）ための語境界。
        pattern = re.compile(rf"(?<![0-9a-z]){re.escape(candidate_norm)}(?![0-9a-z])")
        _ASCII_PATTERN_CACHE[candidate_norm] = pattern
    return pattern


def token_matches(token_norm: str, candidate_norm: str) -> bool:
    if not candidate_norm or not token_norm:
        return False
    if candidate_norm.isascii():
        return bool(_ascii_pattern(candidate_norm).search(token_norm))
    # 日本語は分かち書きされないため、トークン内の部分一致を許す。
    return candidate_norm in token_norm


def build_token_sources(field_values: Iterable[tuple[str, Iterable[str | None]]]) -> list[dict]:
    """(field名, 値列) の並びから、照合用トークンと出所フィールドの組を作る。"""
    sources: list[dict] = []
    for field, values in field_values:
        for value in values:
            if not value:
                continue
            stripped = value.strip()
            if not stripped:
                continue
            sources.append({"field": field, "token": stripped, "token_norm": normalize_text(stripped)})
    return sources


def match_dictionary(token_sources: list[dict], mapping: dict[str, list[str]]) -> list[dict]:
    """辞書の全一致候補を、根拠(どのフィールドのどのトークンがどの別名に一致したか)付きで返す。

    返り値: [{"value": 正規値, "evidence": [{"field", "token", "alias"}, ...]}, ...]
    順序は辞書の定義順（=優先順）を保つ。
    """
    matches: list[dict] = []
    for canonical, candidates in mapping.items():
        evidence: list[dict] = []
        for candidate in candidates:
            candidate_norm = normalize_text(candidate)
            if not candidate_norm:
                continue
            for source in token_sources:
                if len(evidence) >= EVIDENCE_LIMIT_PER_VALUE:
                    break
                if token_matches(source["token_norm"], candidate_norm):
                    evidence.append({"field": source["field"], "token": source["token"], "alias": candidate})
            if len(evidence) >= EVIDENCE_LIMIT_PER_VALUE:
                break
        if evidence:
            matches.append({"value": canonical, "evidence": evidence})
    return matches


def flatten_match_evidence(matches: list[dict]) -> list[dict]:
    """match_dictionary の結果を canonical_attributes['match_evidence'] 用の平坦な形にする。"""
    flat: list[dict] = []
    for match in matches:
        for item in match["evidence"]:
            flat.append({"value": match["value"], **item})
    return flat
