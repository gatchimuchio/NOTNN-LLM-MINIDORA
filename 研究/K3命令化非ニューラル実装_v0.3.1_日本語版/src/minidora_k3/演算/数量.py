from __future__ import annotations
import re
from typing import Mapping, Sequence
from .基礎 import OperatorError, OperatorResult

_QUANTITY = re.compile(
    r"(?P<item>[ァ-ヶー一-龯々A-Za-z・]+?)(?P<count>\d+)"
    r"(?P<unit>本|台|個|粒|房|匹|頭|種類|点|脚|株|片|玉|冊|台|つ)"
)


def _normalize_count_item(value: str) -> str:
    value = value.strip().strip("、。 ")
    for prefix in ("私は", "そして", "また", "さらに", "と"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value.strip().strip("、。 ")


def _requested_category(text: str, ontology: Mapping[str, Sequence[str]]) -> str | None:
    question = text.split("全部で", 1)[1] if "全部で" in text else text
    candidates = sorted(ontology, key=len, reverse=True)
    for category in candidates:
        if category in question:
            return category
    if "物品" in question or "物体" in question or "全部" in question:
        return "物品"
    return None


def solve_count(text: str, ontology: Mapping[str, Sequence[str]] | None = None) -> OperatorResult:
    statement = text.split("全部で", 1)[0]
    pairs = [(_normalize_count_item(m.group("item")), int(m.group("count")), m.group("unit")) for m in _QUANTITY.finditer(statement)]
    if not pairs:
        raise OperatorError("数量対象を抽出できません")
    ontology = ontology or {}
    category = _requested_category(text, ontology)
    allowed = set(ontology.get(category, ())) if category else set()
    selected = pairs if "*" in allowed or category in {None, "物品", "物体"} else [row for row in pairs if row[0] in allowed]
    if not selected:
        raise OperatorError(f"質問カテゴリに適合する数量対象がありません: category={category}, items={pairs}")
    total = sum(count for _, count, _ in selected)
    return OperatorResult(
        str(total),
        (
            {"opcode": "数量抽出", "items": pairs},
            {"opcode": "参照存在論分類", "category": category, "selected": selected},
            {"opcode": "合計", "values": [count for _, count, _ in selected], "result": total},
        ),
        {"items": pairs, "selected": selected, "category": category, "sum": total, "ontology_used": bool(ontology)},
    )
