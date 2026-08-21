from __future__ import annotations

from collections.abc import Iterable

from .hds_ir import HDSIR, 値状態
from .参照 import 参照供給器, 参照記録


_SURFACE_ONLY_KINDS = {
    "source_text",
    "language.input",
    "language.normalized",
    "対象.原文保持",
    "文脈.言語",
}
_BLOCKING_STATES = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


def _unique(parts: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        value = " ".join(str(raw).split()).strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return tuple(out)


def _役割(kind: str) -> str:
    normalized = str(kind).strip()
    if normalized.startswith(("対象.", "実体.")):
        return "対象"
    if normalized.startswith(("関係.", "作用.")) or "述語" in normalized:
        return "関係"
    if normalized.startswith(("状態.", "属性.", "値.")):
        return "状態"
    if normalized.startswith(("条件.", "文脈.", "時刻.", "時間.", "範囲.")):
        return "条件"
    if normalized.startswith("目的."):
        return "焦点"
    return "その他"


def _役割語群(ir: HDSIR) -> tuple[dict[str, tuple[str, ...]], tuple[tuple[str, str], ...]]:
    groups: dict[str, list[str]] = {
        "対象": [],
        "関係": [],
        "状態": [],
        "条件": [],
        "焦点": [],
        "その他": [],
    }
    choices: list[tuple[str, str]] = []

    for coord in ir.座標:
        if coord.値状態 in _BLOCKING_STATES:
            continue
        content = " ".join(str(coord.内容).split()).strip()
        if not content:
            continue
        if coord.座標ID.startswith("choice:"):
            choices.append((coord.座標ID.split(":", 1)[1], content))
            continue
        if str(coord.種別) in _SURFACE_ONLY_KINDS:
            continue
        groups[_役割(str(coord.種別))].append(content)

    return (
        {name: _unique(values) for name, values in groups.items()},
        tuple(sorted(choices, key=lambda item: item[0])),
    )


def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:
    """HDS-IRの役割構造から、外部参照Rへ渡す対称な検索query群を作る。

    優先順位:
    1. 正規化表面文
    2. `対象 → 関係/作用 → 状態/属性 → 条件/文脈 → 焦点` のHDS構造query
    3. 構造query + 各choice（全候補を同条件で扱う）

    4択等では全choice用queryの枠を先に予約する。未確定・未観測・矛盾・留保した
    座標は検索queryへ昇格しない。表層同義語を推測で補わず、Compilerが明示した
    HDS役割と内容だけを使う。
    """
    groups, choices = _役割語群(ir)
    base = " ".join(str(ir.正規化文 or ir.原文).split()).strip()

    structured_parts = (
        *groups["対象"],
        *groups["関係"],
        *groups["状態"],
        *groups["条件"],
        *groups["焦点"],
        *groups["その他"],
    )
    structured = " ".join(_unique(structured_parts))
    entity_relation = " ".join(_unique((*groups["対象"], *groups["関係"], *groups["状態"])))
    entity_only = " ".join(groups["対象"])
    anchor = structured or entity_relation or entity_only or base

    # choice対称性を優先する。既定4択では base/structured + 4 choice = 最大6 query。
    budget = max(int(最大候補数), len(choices))
    nonchoice_slots = max(0, budget - len(choices))
    nonchoice = _unique((base, structured, entity_relation, entity_only))[:nonchoice_slots]

    choice_queries = tuple(
        f"{anchor} {choice}" if anchor else choice
        for _, choice in choices
    )
    return _unique((*nonchoice, *choice_queries))


def HDS参照検索(
    provider: 参照供給器,
    ir: HDSIR,
    *,
    上限: int = 8,
    一問合せ上限: int = 4,
) -> tuple[参照記録, ...]:
    """複数HDS queryの結果をround-robin統合し、先頭queryへの偏りを抑える。"""
    queries = HDS参照問合せ候補(ir)
    if not queries:
        return ()

    pools = [tuple(provider.検索(query, 一問合せ上限)) for query in queries]
    result: list[参照記録] = []
    seen: set[str] = set()
    depth = 0

    while len(result) < 上限:
        progressed = False
        for pool in pools:
            if depth >= len(pool):
                continue
            progressed = True
            record = pool[depth]
            if record.識別子 in seen:
                continue
            seen.add(record.識別子)
            result.append(record)
            if len(result) >= 上限:
                break
        if not progressed:
            break
        depth += 1

    return tuple(result)


__all__ = ["HDS参照問合せ候補", "HDS参照検索"]
