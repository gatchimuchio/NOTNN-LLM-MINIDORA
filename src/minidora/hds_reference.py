from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .hds_effort import HDS努力水準
from .hds_ir import HDSIR, 値状態
from .semantic_tokens import 意味語
from .参照 import 参照供給器, 参照記録


_SURFACE_ONLY_KINDS = {
    "source_text",
    "language.input",
    "language.normalized",
    "対象.原文保持",
    "文脈.言語",
}
_BLOCKING_STATES = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}


@dataclass(frozen=True, slots=True)
class HDS参照予算:
    努力水準: str
    取得上限: int
    一問合せ上限: int
    最大問合せ並列: int


def HDS参照予算選択(ir: HDSIR) -> HDS参照予算:
    level = HDS努力水準(ir)
    if level == "max":
        return HDS参照予算(level, 16, 4, 4)
    if level == "high":
        return HDS参照予算(level, 12, 4, 4)
    return HDS参照予算(level, 6, 3, 2)


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


def _compact_join(parts: Iterable[str], *, 最大要素: int = 12, 最大文字数: int = 280) -> str:
    """検索器へ渡すHDS anchorを、先頭の意味役割を保ったまま有限長へ圧縮する。"""
    selected: list[str] = []
    size = 0
    char_limit = max(1, int(最大文字数))
    for part in _unique(parts):
        if len(selected) >= max(1, int(最大要素)):
            break
        remaining = char_limit - size - (1 if selected else 0)
        if remaining <= 0:
            break
        piece = part[:remaining].strip()
        if not piece:
            break
        selected.append(piece)
        size += len(piece) + (1 if len(selected) > 1 else 0)
        if len(piece) < len(part):
            break
    return " ".join(selected)


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
        "対象": [], "関係": [], "状態": [], "条件": [], "焦点": [], "その他": [],
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
    return {name: _unique(values) for name, values in groups.items()}, tuple(sorted(choices))


def _検索語(token: str) -> str:
    if token.startswith("math:"):
        return token[5:]
    return token


def _候補識別語群(choices: tuple[tuple[str, str], ...]) -> dict[str, tuple[str, ...]]:
    """全choiceを対称比較し、各choiceを他候補から区別する意味語を返す。"""
    terms_by_label = {label: 意味語(text) for label, text in choices}
    frequency: dict[str, int] = {}
    for terms in terms_by_label.values():
        for term in terms:
            frequency[term] = frequency.get(term, 0) + 1

    result: dict[str, tuple[str, ...]] = {}
    for label, terms in terms_by_label.items():
        distinctive = [term for term in terms if frequency.get(term, 0) < len(choices)]
        distinctive.sort(key=lambda term: (frequency.get(term, 0), 0 if term.startswith("math:") else 1, -len(term), term))
        result[label] = _unique(_検索語(term) for term in distinctive[:8])
    return result


def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:
    groups, choices = _役割語群(ir)
    base = " ".join(str(ir.正規化文 or ir.原文).split()).strip()
    structured_parts = _unique((
        *groups["対象"], *groups["関係"], *groups["状態"],
        *groups["条件"], *groups["焦点"], *groups["その他"],
    ))
    structured = _compact_join(structured_parts)
    entity_relation = _compact_join((*groups["対象"], *groups["関係"], *groups["状態"]), 最大要素=10)
    entity_only = _compact_join(groups["対象"], 最大要素=8)
    compact_base = _compact_join((base,), 最大要素=1, 最大文字数=280)
    anchor = structured or entity_relation or entity_only or compact_base

    budget = max(int(最大候補数), len(choices))
    nonchoice_slots = max(0, budget - len(choices))
    nonchoice = _unique((compact_base, structured, entity_relation, entity_only))[:nonchoice_slots]

    distinctive = _候補識別語群(choices)
    choice_queries = []
    for label, choice in choices:
        choice_focus = " ".join(distinctive.get(label, ())) or choice
        choice_queries.append(_compact_join((anchor, choice_focus), 最大要素=2, 最大文字数=360))
    return _unique((*nonchoice, *choice_queries))


def HDS参照縮退問合せ候補(ir: HDSIR) -> tuple[str, ...]:
    """主検索が完全0件の場合だけ使う、より短い対称query群。

    `対象 + choice差分語` を全choice同条件で作り、次に `対象 + 関係/状態`、最後に対象単体へ縮退する。
    choice単独は対象が取れない場合だけ使用し、一般語choiceだけの過広検索を常態化させない。
    """
    groups, choices = _役割語群(ir)
    entity = _compact_join(groups["対象"], 最大要素=8)
    relation = _compact_join((*groups["関係"], *groups["状態"]), 最大要素=6)
    contextual = _compact_join((*groups["条件"], *groups["焦点"]), 最大要素=6)
    distinctive = _候補識別語群(choices)
    choice_queries = tuple(
        _compact_join((entity, " ".join(distinctive.get(label, ())) or choice), 最大要素=2, 最大文字数=320)
        if entity else (" ".join(distinctive.get(label, ())) or choice)
        for label, choice in choices
    )
    reduced = _unique((
        *choice_queries,
        _compact_join((entity, relation), 最大要素=2),
        _compact_join((entity, contextual), 最大要素=2),
        entity,
    ))
    primary = {query.casefold() for query in HDS参照問合せ候補(ir)}
    return tuple(query for query in reduced if query.casefold() not in primary)


def _query_pools(provider: 参照供給器, queries: tuple[str, ...], per_query_limit: int, *, max_parallel: int) -> list[tuple[参照記録, ...]]:
    parallel_safe = bool(getattr(provider, "並列安全", False))
    if not parallel_safe or len(queries) <= 1 or max_parallel <= 1:
        pools: list[tuple[参照記録, ...]] = []
        for query in queries:
            try:
                pools.append(tuple(provider.検索(query, per_query_limit)))
            except Exception:
                pools.append(())
        return pools
    workers = min(max(1, int(max_parallel)), len(queries))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-rq") as executor:
        futures = [executor.submit(provider.検索, query, per_query_limit) for query in queries]
        pools = []
        for future in futures:
            try:
                pools.append(tuple(future.result()))
            except Exception:
                pools.append(())
        return pools


def _round_robin(pools: Iterable[tuple[参照記録, ...]], limit: int) -> tuple[参照記録, ...]:
    pools_tuple = tuple(pools)
    result: list[参照記録] = []
    seen: set[str] = set()
    depth = 0
    while len(result) < limit:
        progressed = False
        for pool in pools_tuple:
            if depth >= len(pool):
                continue
            progressed = True
            record = pool[depth]
            if record.識別子 in seen:
                continue
            seen.add(record.識別子)
            result.append(record)
            if len(result) >= limit:
                break
        if not progressed:
            break
        depth += 1
    return tuple(result)


def HDS参照検索(
    provider: 参照供給器,
    ir: HDSIR,
    *,
    上限: int | None = None,
    一問合せ上限: int | None = None,
    最大問合せ並列: int | None = None,
) -> tuple[参照記録, ...]:
    """K3 effort由来budgetで検索し、完全0件時だけHDS構造を段階縮退して再検索する。"""
    budget = HDS参照予算選択(ir)
    total_limit = budget.取得上限 if 上限 is None else max(0, int(上限))
    per_query = budget.一問合せ上限 if 一問合せ上限 is None else max(1, int(一問合せ上限))
    parallel = budget.最大問合せ並列 if 最大問合せ並列 is None else max(1, int(最大問合せ並列))
    if total_limit <= 0:
        return ()

    primary = HDS参照問合せ候補(ir)
    if primary:
        primary_records = _round_robin(
            _query_pools(provider, primary, per_query, max_parallel=parallel),
            total_limit,
        )
        if primary_records:
            return primary_records

    fallback = HDS参照縮退問合せ候補(ir)
    if not fallback:
        return ()
    return _round_robin(
        _query_pools(provider, fallback, per_query, max_parallel=parallel),
        total_limit,
    )


__all__ = [
    "HDS参照予算",
    "HDS参照予算選択",
    "HDS参照問合せ候補",
    "HDS参照縮退問合せ候補",
    "HDS参照検索",
]
