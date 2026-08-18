from __future__ import annotations
import re
from typing import Any
from .基礎 import OperatorError, OperatorResult

_PEOPLE = ("アリス", "ボブ", "クレア")
_OPTIONS = re.compile(r"\(([A-F])\)\s*([^\n]+)")


def _clean_value(value: str) -> str:
    return value.strip().strip("。 、").strip("『』")


def _parse_initial_assignments(text: str) -> dict[str, str]:
    first = text.split("\n", 1)[0]
    result: dict[str, str] = {}
    for person in _PEOPLE:
        patterns = [
            rf"{person}は『([^』]+)』",
            rf"{person}は([^、。]+?)と(?:、|踊)",
            rf"{person}は([^、。]+?のボール)",
        ]
        for pattern in patterns:
            match = re.search(pattern, first)
            if match:
                result[person] = _clean_value(match.group(1))
                break
    if len(result) != 3:
        raise OperatorError(f"初期割当を抽出できません: {result}")
    return result


def solve_swaps(text: str) -> OperatorResult:
    state = _parse_initial_assignments(text)
    initial = dict(state)
    swaps = re.findall(r"(?:まず|次に|最後に)(アリス|ボブ|クレア)と(アリス|ボブ|クレア)が[^。]*(?:交換|交代)", text)
    if not swaps:
        raise OperatorError("交換列を抽出できません")
    transitions: list[dict[str, Any]] = []
    for left, right in swaps:
        state[left], state[right] = state[right], state[left]
        transitions.append({"swap": [left, right], "state": dict(state)})
    question_area = text.split("選択肢:", 1)[0]
    target_matches = re.findall(r"(アリス|ボブ|クレア)(?:が持っている[^\n。]*|のパートナー)は\s*$", question_area.strip())
    if not target_matches:
        target_matches = re.findall(r"(アリス|ボブ|クレア)(?:が持っている[^\n。]*|のパートナー)は", question_area)
    if not target_matches:
        raise OperatorError("照会主体を抽出できません")
    target = target_matches[-1]
    value = _clean_value(state[target])
    options = {label: _clean_value(body) for label, body in _OPTIONS.findall(text)}
    label = next((label for label, body in options.items() if body == value), None)
    if label is None:
        raise OperatorError(f"最終値が選択肢にありません: {value}, {options}")
    answer = f"({label})"
    return OperatorResult(
        answer,
        (
            {"opcode": "状態対応読込", "state": initial},
            *({"opcode": "交換", **row} for row in transitions),
            {"opcode": "状態読出", "target": target, "value": value},
            {"opcode": "選択肢対応", "answer": answer},
        ),
        {"initial": initial, "swaps": swaps, "final": state, "target": target, "options": options},
    )
