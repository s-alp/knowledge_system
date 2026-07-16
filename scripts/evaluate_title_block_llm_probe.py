from __future__ import annotations

import json
from pathlib import Path
import sys
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Gemini title-block probe output against guardrails.")
    parser.add_argument("probe_json", help="Probe JSON created by scripts/probe_title_block_llm.py")
    parser.add_argument("--output", help="Optional JSON file to write the evaluation result.")
    parser.add_argument("--allow-gemini-errors", action="store_true", help="Do not fail when probe files contain gemini_error.")
    args = parser.parse_args()

    path = Path(args.probe_json)
    payload = json.loads(path.read_text(encoding="utf-8"))

    gemini_errors = []
    positive_labels = 0
    negative_labels = 0
    classification_true_positives = 0
    classification_false_positives = []
    classification_wrong_fields = []
    classification_missed_positives = []
    guardrail_false_positives = []
    accepted_wrong_fields = []
    accepted_uplift_count = 0

    for file_result in payload.get("files", []):
        if file_result.get("gemini_error"):
            gemini_errors.append(
                {
                    "file": file_result.get("file"),
                    "error": file_result.get("gemini_error"),
                }
            )
        candidates = file_result.get("candidate_preview", [])
        classifications = {
            int(item["index"]): item
            for item in (file_result.get("gemini", {}).get("classifications", []) or [])
            if "index" in item
        }
        accepted = {
            int(item["index"]): item
            for item in (file_result.get("gemini", {}).get("accepted", []) or [])
            if "index" in item
        }

        for index, candidate in enumerate(candidates):
            expected_field = candidate.get("field") if candidate.get("value") is not None else None
            classification = classifications.get(index)
            classified_field = classification.get("field") if classification else None
            accepted_item = accepted.get(index)

            if expected_field is None:
                negative_labels += 1
                if classified_field:
                    classification_false_positives.append(
                        {
                            "file": file_result["file"],
                            "index": index,
                            "actual": classification,
                        }
                    )
                if accepted_item:
                    guardrail_false_positives.append(
                        {
                            "file": file_result["file"],
                            "index": index,
                            "actual": accepted_item,
                        }
                    )
                continue

            positive_labels += 1
            if classified_field == expected_field:
                classification_true_positives += 1
            elif classified_field is None:
                classification_missed_positives.append(
                    {
                        "file": file_result["file"],
                        "index": index,
                        "expected": expected_field,
                    }
                )
            else:
                classification_wrong_fields.append(
                    {
                        "file": file_result["file"],
                        "index": index,
                        "expected": expected_field,
                        "actual": classification,
                    }
                )

            if accepted_item:
                if accepted_item.get("field") == expected_field:
                    accepted_uplift_count += 1
                else:
                    accepted_wrong_fields.append(
                        {
                            "file": file_result["file"],
                            "index": index,
                            "expected": expected_field,
                            "actual": accepted_item,
                        }
                    )

    classified_positive_count = (
        classification_true_positives
        + len(classification_false_positives)
        + len(classification_wrong_fields)
    )
    result = {
        "probeFile": str(path),
        "referenceDefinition": (
            "A candidate with an existing non-empty value is a positive label. "
            "A label-only or value-less candidate is a negative label."
        ),
        "fileCount": len(payload.get("files", [])),
        "classified": bool(payload.get("classified")),
        "geminiErrorCount": len(gemini_errors),
        "positiveLabelCount": positive_labels,
        "negativeLabelCount": negative_labels,
        "classificationTruePositiveCount": classification_true_positives,
        "classificationFalsePositiveCount": len(classification_false_positives),
        "classificationWrongFieldCount": len(classification_wrong_fields),
        "classificationMissedPositiveCount": len(classification_missed_positives),
        "classificationPrecision": (
            round(classification_true_positives / classified_positive_count, 4)
            if classified_positive_count
            else None
        ),
        "classificationPositiveRecall": (
            round(classification_true_positives / positive_labels, 4)
            if positive_labels
            else None
        ),
        "guardrailFalsePositiveCount": len(guardrail_false_positives),
        "guardrailWrongFieldCount": len(accepted_wrong_fields),
        "guardrailSafetyRate": (
            round((negative_labels - len(guardrail_false_positives)) / negative_labels, 4)
            if negative_labels
            else None
        ),
        "acceptedUpliftCount": accepted_uplift_count,
        "classificationFalsePositives": classification_false_positives,
        "classificationWrongFields": classification_wrong_fields,
        "classificationMissedPositives": classification_missed_positives,
        "geminiErrors": gemini_errors,
        "guardrailFalsePositives": guardrail_false_positives,
        "acceptedWrongFields": accepted_wrong_fields,
        "assessment": (
            "probe_errors"
            if gemini_errors and not args.allow_gemini_errors
            else "unsafe"
            if guardrail_false_positives or accepted_wrong_fields or classification_false_positives or classification_wrong_fields
            else "incomplete_classification"
            if classification_missed_positives
            else "measured_safe_uplift"
            if accepted_uplift_count
            else "safe_but_no_accepted_uplift"
        ),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    has_blocking_issue = (
        (gemini_errors and not args.allow_gemini_errors)
        or guardrail_false_positives
        or accepted_wrong_fields
        or classification_false_positives
        or classification_wrong_fields
        or classification_missed_positives
    )
    return 1 if has_blocking_issue else 0


if __name__ == "__main__":
    raise SystemExit(main())
