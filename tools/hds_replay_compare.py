from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("result JSON objectが必要")
    return dict(value)


def _index(result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in result.get("details", ()):
        if not isinstance(row, Mapping):
            continue
        case_id = str(row.get("id", ""))
        if not case_id:
            continue
        out[case_id] = dict(row)
    return out


def _classify(before: Mapping[str, Any], after: Mapping[str, Any]) -> str:
    before_correct = before.get("correct")
    after_correct = after.get("correct")
    before_answered = before.get("status") == "APPROVE" and before.get("predicted") is not None
    after_answered = after.get("status") == "APPROVE" and after.get("predicted") is not None

    if not before_answered and after_answered:
        if after_correct is True:
            return "SUSPEND_TO_CORRECT"
        if after_correct is False:
            return "SUSPEND_TO_WRONG"
        return "SUSPEND_TO_ANSWERED_UNSCORED"
    if before_answered and not after_answered:
        if before_correct is True:
            return "CORRECT_TO_SUSPEND"
        if before_correct is False:
            return "WRONG_TO_SUSPEND"
        return "ANSWERED_TO_SUSPEND_UNSCORED"
    if before_correct is False and after_correct is True:
        return "WRONG_TO_CORRECT"
    if before_correct is True and after_correct is False:
        return "CORRECT_TO_WRONG"
    if before_correct is True and after_correct is True:
        return "CORRECT_STABLE"
    if before_correct is False and after_correct is False:
        return "WRONG_STABLE"
    if not before_answered and not after_answered:
        return "SUSPEND_STABLE"
    return "OTHER"


def compare(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    left = _index(before)
    right = _index(after)
    ids = sorted(set(left) | set(right))
    transitions: Counter[str] = Counter()
    reason_delta: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []

    for case_id in ids:
        b = left.get(case_id)
        a = right.get(case_id)
        if b is None:
            transition = "ADDED_CASE"
        elif a is None:
            transition = "REMOVED_CASE"
        else:
            transition = _classify(b, a)
            b_reasons = set(map(str, b.get("reasons", ())))
            a_reasons = set(map(str, a.get("reasons", ())))
            for reason in sorted(a_reasons - b_reasons):
                reason_delta["+" + reason] += 1
            for reason in sorted(b_reasons - a_reasons):
                reason_delta["-" + reason] += 1
        transitions[transition] += 1
        rows.append(
            {
                "id": case_id,
                "transition": transition,
                "before_status": None if b is None else b.get("status"),
                "after_status": None if a is None else a.get("status"),
                "before_predicted": None if b is None else b.get("predicted"),
                "after_predicted": None if a is None else a.get("predicted"),
                "before_correct": None if b is None else b.get("correct"),
                "after_correct": None if a is None else a.get("correct"),
            }
        )

    return {
        "schema": "minidora.hds-choice-replay.compare.v1",
        "before": {
            "total": before.get("total"),
            "correct": before.get("correct"),
            "accuracy_percent": before.get("accuracy_percent"),
            "answered": before.get("answered"),
            "answer_rate_percent": before.get("answer_rate_percent"),
        },
        "after": {
            "total": after.get("total"),
            "correct": after.get("correct"),
            "accuracy_percent": after.get("accuracy_percent"),
            "answered": after.get("answered"),
            "answer_rate_percent": after.get("answer_rate_percent"),
        },
        "delta": {
            "correct": (after.get("correct") - before.get("correct")) if isinstance(after.get("correct"), int) and isinstance(before.get("correct"), int) else None,
            "accuracy_percent": (after.get("accuracy_percent") - before.get("accuracy_percent")) if isinstance(after.get("accuracy_percent"), (int, float)) and isinstance(before.get("accuracy_percent"), (int, float)) else None,
            "answered": (after.get("answered") - before.get("answered")) if isinstance(after.get("answered"), int) and isinstance(before.get("answered"), int) else None,
            "answer_rate_percent": (after.get("answer_rate_percent") - before.get("answer_rate_percent")) if isinstance(after.get("answer_rate_percent"), (int, float)) and isinstance(before.get("answer_rate_percent"), (int, float)) else None,
        },
        "transitions": dict(sorted(transitions.items())),
        "reason_delta": dict(sorted(reason_delta.items())),
        "details": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="2つのHDS Replay結果をcase単位で比較する。")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = compare(_load(args.before), _load(args.after))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
