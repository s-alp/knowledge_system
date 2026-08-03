"""2D図面の図番、図面名、図枠値、改訂履歴候補を整理する。

近傍探索は根拠座標と印刷範囲を確認し、別要素間の意味を無制限に推測しない。
入力dictだけを読み、候補と採用値を返す。
"""
from __future__ import annotations

from collections.abc import Iterable
import re
import unicodedata

from icad_tag_extraction.normalization_common import _merge_unique
from icad_tag_extraction.normalization_material import *  # noqa: F403
from icad_tag_extraction.normalization_rules import *  # noqa: F403
from icad_tag_extraction.normalization_text import *  # noqa: F403
from icad_tag_extraction.normalization_text import _SCALE_RATIO_TOKEN_RE
from icad_tag_extraction.normalization_2d_sections import *  # noqa: F403

def normalize_identity_name_value(value: str | None) -> str | None:
    """名称本体ではない先頭記号と寸法・型式トークンを表示名称から除く。

    `★ガイドレール`の★や`SFF-424 L=1572`は図面上の注記・仕様情報であり、
    原文はraw証跡に残しつつ、製品名・部品名へそのまま登録しない。
    """

    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    normalized = IDENTITY_NAME_PREFIX_MARKERS_RE.sub("", normalized)
    normalized = IDENTITY_SPEC_TOKEN_RE.sub(" ", normalized)
    # 「法兰(右)」のように名称本体の一部である括弧は残し、前後の区切り記号だけを除く。
    normalized = re.sub(r"[\s　,、，]+", " ", normalized).strip(" 　:：=＝-－_/／")
    if normalized.upper() in IDENTITY_NAME_NOISE_VALUES:
        return None
    return normalized or None


def _identity_name_value_is_usable(field: str, value: str | None) -> bool:
    normalized = normalize_identity_name_value(value)
    if (
        field not in IDENTITY_NAME_FIELDS
        or not _is_title_block_value_usable(
            normalized,
            max_length=int(TITLE_BLOCK_FIELD_RULES.get(field, {}).get("max_value_length", 80)),
        )
    ):
        return False
    normalized = str(normalized)
    if normalized.upper() in IDENTITY_NAME_NOISE_VALUES:
        return False
    if any(keyword in normalized for keyword in DRAWING_NUMBER_REFERENCE_KEYWORDS):
        return False
    if any(_normalize_for_match(keyword) in _normalize_for_match(normalized) for keyword in REVISION_NOTE_KEYWORDS):
        return False
    if not re.search(r"[A-Z\u3040-\u30ff\u3400-\u9fff]", normalized, re.IGNORECASE):
        return False
    if re.fullmatch(r"[A-Z0-9._/\-\s]+", normalized, re.IGNORECASE) and re.search(r"\d", normalized):
        return False
    return True


def _nearest_identity_name_value(
    *,
    label_text: dict,
    texts: list[dict],
    field: str,
    has_print_frames: bool,
) -> tuple[str | None, dict | None]:
    """名称ラベルの右または上下に整列する最短の文字要素だけを値候補にする。

    材質・日付などへ汎用化すると図枠レイアウト差で誤対応しやすいため、
    呼び出し元は製品・装置・ユニット・部品・図面の名称欄に限定する。
    """

    label_x = label_text.get("position_x")
    label_y = label_text.get("position_y")
    if not isinstance(label_x, (int, float)) or not isinstance(label_y, (int, float)):
        return None, None

    right_ranked: list[tuple[float, str, dict]] = []
    left_ranked: list[tuple[float, str, dict]] = []
    vertical_ranked: list[tuple[float, str, dict]] = []
    for candidate_text in texts:
        if candidate_text is label_text:
            continue
        if not _is_usable_print_area_item(candidate_text, has_print_frames=has_print_frames):
            continue
        if (
            label_text.get("view_name")
            and candidate_text.get("view_name")
            and label_text.get("view_name") != candidate_text.get("view_name")
        ):
            continue
        if (
            label_text.get("layer_no") is not None
            and candidate_text.get("layer_no") is not None
            and label_text.get("layer_no") != candidate_text.get("layer_no")
        ):
            continue
        candidate_x = candidate_text.get("position_x")
        candidate_y = candidate_text.get("position_y")
        if not isinstance(candidate_x, (int, float)) or not isinstance(candidate_y, (int, float)):
            continue
        lines = _text_lines_from_payload(candidate_text)
        if len(lines) != 1:
            continue
        raw_value = lines[0].strip()
        # 最短要素が無効な見出し・プレースホルダーでも順位付けには残す。
        # ここで捨てると、その奥の無関係な文字を名称として拾ってしまう。
        value = normalize_identity_name_value(raw_value) or unicodedata.normalize("NFKC", raw_value)
        delta_x = float(candidate_x) - float(label_x)
        delta_y = float(candidate_y) - float(label_y)
        right_horizontal = delta_x > 0 and abs(delta_y) <= max(0.5, abs(delta_x) * 0.15)
        # BOM欄では品名値が見出しの左側かつ行中央に置かれる実例がある。
        # 右側より少し広い行ずれを許容するが、同一ビュー・同一レイヤー・印刷枠内は必須とする。
        left_horizontal = delta_x < 0 and abs(delta_y) <= max(0.5, abs(delta_x) * 0.25)
        vertical = delta_y != 0 and abs(delta_x) <= max(0.5, abs(delta_y) * 0.15)
        if not right_horizontal and not left_horizontal and not vertical:
            continue
        distance = (delta_x**2 + delta_y**2) ** 0.5
        if right_horizontal:
            ranked_target = right_ranked
        elif left_horizontal:
            ranked_target = left_ranked
        else:
            ranked_target = vertical_ranked
        ranked_target.append((distance, unicodedata.normalize("NFKC", value), candidate_text))

    # 通常の右側配置、BOMで見られる左側配置、上下配置の順に確認する。
    # 同じ方向では最短要素だけを評価し、別欄を飛び越えて遠方文字を拾わない。
    for ranked in (right_ranked, left_ranked, vertical_ranked):
        if not ranked:
            continue
        ranked.sort(key=lambda item: item[0])
        _, value, candidate_text = ranked[0]
        if _identity_name_value_is_usable(field, value):
            return value, candidate_text
    return None, None


def _nearest_drawing_name_aligned_with_number(
    *,
    texts: list[dict],
    drawing_number: str | None,
    has_print_frames: bool,
) -> tuple[str | None, dict | None]:
    """図番と縦に揃った名称文字を、明示ラベルがない図枠の限定救済に使う。

    図番と同一ビュー・同一レイヤーで、短い距離に縦整列する4文字以上の名称だけを対象とする。
    日付、重量、尺度、材質、別図番は候補から除外し、検印欄等の誤採用を抑える。
    """

    drawing_number_key = _drawing_number_match_key(drawing_number)
    if not drawing_number_key:
        return None, None

    number_texts: list[dict] = []
    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
            continue
        for line in _text_lines_from_payload(text):
            if _drawing_number_match_key(_clean_drawing_number_value(line)) == drawing_number_key:
                number_texts.append(text)
                break

    ranked: list[tuple[float, str, dict]] = []
    for number_text in number_texts:
        number_x = number_text.get("position_x")
        number_y = number_text.get("position_y")
        if not isinstance(number_x, (int, float)) or not isinstance(number_y, (int, float)):
            continue
        for candidate_text in texts:
            if candidate_text is number_text:
                continue
            if not _is_usable_print_area_item(candidate_text, has_print_frames=has_print_frames):
                continue
            if (
                number_text.get("view_name")
                and candidate_text.get("view_name")
                and number_text.get("view_name") != candidate_text.get("view_name")
            ):
                continue
            if (
                number_text.get("layer_no") is not None
                and candidate_text.get("layer_no") is not None
                and number_text.get("layer_no") != candidate_text.get("layer_no")
            ):
                continue
            candidate_x = candidate_text.get("position_x")
            candidate_y = candidate_text.get("position_y")
            if not isinstance(candidate_x, (int, float)) or not isinstance(candidate_y, (int, float)):
                continue
            delta_x = float(candidate_x) - float(number_x)
            delta_y = float(candidate_y) - float(number_y)
            distance = abs(delta_y)
            if distance < 4.0 or distance > 40.0 or abs(delta_x) > max(1.0, distance * 0.08):
                continue
            lines = _text_lines_from_payload(candidate_text)
            if len(lines) != 1:
                continue
            value = normalize_identity_name_value(lines[0])
            if not value or len(_normalize_for_match(value)) < 4:
                continue
            if not _identity_name_value_is_usable("drawing_name", value):
                continue
            if _clean_drawing_number_value(value):
                continue
            if DATE_VALUE_PATTERN.search(value) or _SCALE_RATIO_TOKEN_RE.fullmatch(value):
                continue
            if re.search(r"[-+]?\d+(?:\.\d+)?\s*(?:kg|g|t)\b", value, re.IGNORECASE):
                continue
            if _classify_material_value(value, allow_unknown=False)["status"] == "formal":
                continue
            ranked.append((distance, value, candidate_text))

    if not ranked:
        return None, None
    ranked.sort(key=lambda item: item[0])
    _, value, candidate_text = ranked[0]
    return value, candidate_text


def _build_title_block_candidates(texts: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    # 別文字要素の座標結合は誤対応リスクが高いため、明示された名称ラベルの直近値だけに限定する。
    candidates: list[dict] = []
    seen: set[tuple[str, str, str | None, float | None, float | None]] = set()

    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
            continue
        lines = _text_lines_from_payload(text)
        if not lines:
            continue

        for line_index, line in enumerate(lines):
            if _contains_replacement_character(line):
                continue
            normalized_line = _normalize_for_match(line)
            for field, rule in TITLE_BLOCK_FIELD_RULES.items():
                max_value_length = int(rule.get("max_value_length", 80))
                for keyword in sorted(rule["keywords"], key=lambda item: len(str(item)), reverse=True):
                    normalized_keyword = _normalize_for_match(str(keyword))
                    if normalized_keyword not in normalized_line:
                        continue

                    value = _strip_label_value(line, str(keyword))
                    if field in IDENTITY_NAME_FIELDS:
                        value = normalize_identity_name_value(value)
                    confidence = "medium" if _is_field_value_usable(field, value, line) else "low"
                    if confidence == "low":
                        value = None
                    if not value and line_index + 1 < len(lines):
                        next_value = lines[line_index + 1].strip()
                        if field in IDENTITY_NAME_FIELDS:
                            next_value = normalize_identity_name_value(next_value)
                        if _is_field_value_usable(field, next_value, line):
                            value = next_value
                            confidence = "medium"
                    paired_text = None
                    if not value and field in IDENTITY_NAME_FIELDS:
                        value, paired_text = _nearest_identity_name_value(
                            label_text=text,
                            texts=texts,
                            field=field,
                            has_print_frames=has_print_frames,
                        )
                        if value:
                            confidence = "medium"

                    key = (field, line, value, text.get("position_x"), text.get("position_y"))
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        {
                            "field": field,
                            "label": rule["label"],
                            "value": value,
                            "evidence_text": line,
                            "confidence": confidence,
                            "view_name": text.get("view_name"),
                            "layer_no": text.get("layer_no"),
                            "position_x": text.get("position_x"),
                            "position_y": text.get("position_y"),
                            "inside_print_area": text.get("inside_print_area"),
                            "value_position_x": paired_text.get("position_x") if paired_text else None,
                            "value_position_y": paired_text.get("position_y") if paired_text else None,
                            "source": "2d_text_near_identity_label" if paired_text else "2d_text",
                        }
                    )
                    break

    return candidates


def _build_revision_note_candidates(texts: list[dict], *, has_print_frames: bool = False) -> list[dict]:
    candidates: list[dict] = []
    seen: set[tuple[str, float | None, float | None]] = set()

    for text in texts:
        if not _is_usable_print_area_item(text, has_print_frames=has_print_frames):
            continue
        lines = _text_lines_from_payload(text)
        if not lines:
            continue
        evidence_text = " ".join(lines).strip()
        if not evidence_text or _contains_replacement_character(evidence_text):
            continue
        normalized_evidence = _normalize_for_match(evidence_text)
        matched_keywords = [
            keyword
            for keyword in REVISION_NOTE_KEYWORDS
            if _normalize_for_match(keyword) in normalized_evidence
        ]
        if not matched_keywords:
            continue
        if DATE_VALUE_PATTERN.search(evidence_text) and any(
            _normalize_for_match(keyword) in normalized_evidence
            for keyword in ("改訂日", "訂正日", "revision date", "rev date")
        ):
            continue

        value = None
        for keyword in matched_keywords:
            stripped_value = _strip_label_value(evidence_text, keyword)
            if _is_title_block_value_usable(stripped_value, max_length=160):
                value = stripped_value
                break
        if value is None and _is_title_block_value_usable(evidence_text, max_length=160):
            value = evidence_text

        key = (evidence_text, text.get("position_x"), text.get("position_y"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "value": value,
                "evidence_text": evidence_text,
                "matched_keywords": matched_keywords,
                "confidence": "medium" if value else "low",
                "view_name": text.get("view_name"),
                "layer_no": text.get("layer_no"),
                "position_x": text.get("position_x"),
                "position_y": text.get("position_y"),
                "inside_print_area": text.get("inside_print_area"),
                "source": "2d_revision_text",
            }
        )

    return candidates


def _select_title_block_fields(candidates: list[dict]) -> dict:
    selected: dict = {}
    for candidate in candidates:
        if candidate.get("confidence") != "medium":
            continue
        value = candidate.get("value")
        field = candidate.get("field")
        rule = TITLE_BLOCK_FIELD_RULES.get(field, {})
        max_value_length = int(rule.get("max_value_length", 80))
        if not _is_field_value_usable(field, value, str(candidate.get("evidence_text") or "")):
            continue
        if field in IDENTITY_NAME_FIELDS and not _identity_name_value_is_usable(field, value):
            # 「品名 SUS304」のように欄名だけが誤っていても、値が正式な材質規格なら
            # 外部AIへ送らず材質辞書で確定する。
            material = _classify_material_value(value, allow_unknown=False)
            if material["status"] == "formal" and "material" not in selected:
                selected["material"] = material["canonical"]
            continue
        if field == "drawing_number":
            value = _clean_drawing_number_value(value)
            if not value:
                continue
        elif field in IDENTITY_NAME_FIELDS:
            value = normalize_identity_name_value(value)
            if not value:
                continue
        if field and field not in selected:
            selected[field] = value
    return selected


__all__ = (
    "normalize_identity_name_value",
    "_identity_name_value_is_usable",
    "_nearest_identity_name_value",
    "_nearest_drawing_name_aligned_with_number",
    "_build_title_block_candidates",
    "_build_revision_note_candidates",
    "_select_title_block_fields",
)
