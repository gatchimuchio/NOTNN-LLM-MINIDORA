from __future__ import annotations
import itertools
import re
from typing import Any, Mapping
from .基礎 import OperatorError, OperatorResult

_OPTIONS = re.compile(r"\(([A-F])\)\s*([^\n]+)")

def _clean_value(value: str) -> str:
    return value.strip().strip("。 、").strip("『』")

_RELATION_PATTERNS = (
    (re.compile(r"([^。]+?)は([^。]+?)の右側"), ">"),
    (re.compile(r"([^。]+?)は([^。]+?)の左側"), "<"),
    (re.compile(r"([^。]+?)は([^。]+?)よりも新し(?:く|い)"), ">"),
    (re.compile(r"([^。]+?)は([^。]+?)よりも古い"), "<"),
    (re.compile(r"([^。]+?)は([^。]+?)よりも安価"), "<"),
    (re.compile(r"([^。]+?)は([^。]+?)よりも下位"), "<"),
)

def _entity_from_option(body: str) -> str:
    match = re.match(r"(.+?)(?:は|が)", body)
    if not match:
        raise OperatorError(f"選択肢主体を抽出できません: {body}")
    return _clean_value(match.group(1))

def _tail_entity(value: str) -> str:
    value = value.split("――")[-1].split("：")[-1].strip()
    for prefix in ("3羽の鳥がいます", "3台の車両", "3冊の本があります", "3冊の本です", "3種類の果物", "3人のゴルファー"):
        value = value.removeprefix(prefix).strip("――：、 ")
    return _clean_value(value)

def solve_ordering(text: str) -> OperatorResult:
    narrative, option_text = text.split("選択肢:", 1)
    options = {label: body.strip() for label, body in _OPTIONS.findall(option_text)}
    entities = tuple(dict.fromkeys(_entity_from_option(body) for body in options.values()))
    if len(entities) != 3:
        raise OperatorError(f"3対象を得られません: {entities}")
    constraints: list[tuple[str, str, str]] = []
    for pattern, relation in _RELATION_PATTERNS:
        for match in pattern.finditer(narrative):
            left = _tail_entity(match.group(1)); right = _tail_entity(match.group(2))
            if left in entities and right in entities:
                constraints.append((left, relation, right))
    extrema: list[tuple[str, int]] = []
    fixed_ranks: list[tuple[str, int]] = []
    for entity in entities:
        if re.search(re.escape(entity) + r"(?:は|が)最も右側", narrative): extrema.append((entity, 2))
        if re.search(re.escape(entity) + r"(?:は|が)最も左側", narrative): extrema.append((entity, 0))
        if re.search(re.escape(entity) + r"(?:は|が)左から2(?:番目|冊目)", narrative): fixed_ranks.append((entity, 1))
    valid: list[dict[str, int]] = []
    for permutation in itertools.permutations(range(3)):
        rank = dict(zip(entities, permutation))
        if any(rank[left] <= rank[right] for left, relation, right in constraints if relation == ">"): continue
        if any(rank[left] >= rank[right] for left, relation, right in constraints if relation == "<"): continue
        if any(rank[entity] != required for entity, required in extrema): continue
        if any(rank[entity] != required for entity, required in fixed_ranks): continue
        valid.append(rank)
    if not valid:
        raise OperatorError(f"順序制約が閉じません: {constraints}, {extrema}")

    def option_truth(body: str, rank: Mapping[str, int]) -> bool:
        entity = _entity_from_option(body)
        if "左から2" in body or "2番目に高価" in body: return rank[entity] == 1
        if "最も右側" in body or "最も新しい" in body or "1位" in body: return rank[entity] == 2
        if "最も左側" in body or "最も古い" in body: return rank[entity] == 0
        raise OperatorError(f"未対応の順序選択肢: {body}")

    surviving = [label for label, body in options.items() if all(option_truth(body, rank) for rank in valid)]
    if len(surviving) != 1:
        raise OperatorError(f"選択肢が一意でありません: {surviving}, valid={valid}")
    answer = f"({surviving[0]})"
    return OperatorResult(
        answer,
        (
            {"opcode": "順序制約抽出", "entities": entities, "constraints": constraints, "extrema": extrema, "fixed_ranks": fixed_ranks},
            {"opcode": "全順序列挙", "valid": valid},
            {"opcode": "選択肢評価", "answer": answer},
        ),
        {"entities": entities, "constraints": constraints, "extrema": extrema, "fixed_ranks": fixed_ranks, "valid_orders": valid, "options": options},
    )
