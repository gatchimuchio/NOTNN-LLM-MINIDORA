from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
import re

from .hds_effort import HDS努力水準
from .hds_ir import HDSIR, 値状態
from .semantic_tokens import 意味語
from .参照 import 参照供給器, 参照記録

_SURFACE_ONLY_KINDS = {"source_text", "language.input", "language.normalized", "対象.原文保持", "文脈.言語"}
_QUERY_META_PREFIXES = ("制御.", "監査.")
_BLOCKING_STATES = {値状態.未確定, 値状態.未観測, 値状態.矛盾, 値状態.留保}
_FOCUS_SPLIT = re.compile(r"(?<=[?!.。？！])\s+|\n+")

@dataclass(frozen=True, slots=True)
class HDS参照予算:
    努力水準: str
    取得上限: int
    一問合せ上限: int
    最大問合せ並列: int

@dataclass(frozen=True, slots=True)
class _HDS問合せ仕様:
    問合せ: str
    種別: str
    候補: str | None = None

def HDS参照予算選択(ir: HDSIR) -> HDS参照予算:
    level = HDS努力水準(ir)
    if level == "max": return HDS参照予算(level, 16, 4, 4)
    if level == "high": return HDS参照予算(level, 12, 4, 4)
    return HDS参照予算(level, 6, 3, 2)

def _unique(parts: Iterable[str]) -> tuple[str, ...]:
    out: list[str] = []; seen: set[str] = set()
    for raw in parts:
        value = " ".join(str(raw).split()).strip()
        if not value: continue
        key = value.casefold()
        if key in seen: continue
        seen.add(key); out.append(value)
    return tuple(out)

def _役割(kind: str) -> str:
    normalized = str(kind).strip()
    if normalized.startswith(("対象.", "実体.")): return "対象"
    if normalized.startswith(("関係.", "作用.")) or "述語" in normalized: return "関係"
    if normalized.startswith(("状態.", "属性.", "値.")): return "状態"
    if normalized.startswith(("条件.", "文脈.", "時刻.", "時間.", "範囲.")): return "条件"
    if normalized.startswith("目的."): return "焦点"
    return "その他"

def _役割語群(ir: HDSIR) -> tuple[dict[str, tuple[str, ...]], tuple[tuple[str, str], ...]]:
    groups: dict[str, list[str]] = {"対象": [], "関係": [], "状態": [], "条件": [], "焦点": [], "その他": []}
    choices: list[tuple[str, str]] = []
    for coord in ir.座標:
        if coord.値状態 in _BLOCKING_STATES: continue
        content = " ".join(str(coord.内容).split()).strip()
        if not content: continue
        if coord.座標ID.startswith("choice:"):
            choices.append((coord.座標ID.split(":", 1)[1], content)); continue
        kind = str(coord.種別)
        if kind in _SURFACE_ONLY_KINDS or kind.startswith(_QUERY_META_PREFIXES): continue
        groups[_役割(kind)].append(content)
    return {name: _unique(values) for name, values in groups.items()}, tuple(sorted(choices))

def _切詰め(text: str, limit: int) -> str:
    value = " ".join(str(text).split()).strip()
    if len(value) <= limit: return value
    parts = value.split()
    if not parts or limit <= 0: return ""
    head_budget = max(1, int(limit * 0.58)); tail_budget = max(1, limit - head_budget - 1)
    head: list[str] = []; size = 0; split_index = 0
    for index, part in enumerate(parts):
        extra = len(part) + (1 if head else 0)
        if size + extra > head_budget: split_index = index; break
        head.append(part); size += extra; split_index = index + 1
    tail_rev: list[str] = []; size = 0
    for part in reversed(parts[split_index:]):
        extra = len(part) + (1 if tail_rev else 0)
        if size + extra > tail_budget: break
        tail_rev.append(part); size += extra
    tail = list(reversed(tail_rev))
    return " ".join(head) if not tail else " ".join((*head, *tail))

def _焦点抽出(text: str, *, limit: int = 180) -> str:
    raw = str(text).strip()
    if not raw: return ""
    segments = [segment.strip() for segment in _FOCUS_SPLIT.split(raw) if segment.strip()]
    for segment in reversed(segments):
        if "?" in segment or "？" in segment: return _切詰め(segment, limit)
    if len(segments) > 1: return _切詰め(segments[-1], limit)
    return _切詰め(" ".join(raw.split()[-32:]), limit)

def _検索表層(token: str) -> str:
    for prefix in ("math:", "atom:", "sym:"):
        if token.startswith(prefix): return token[len(prefix):]
    return token

def _候補差分語(choices: tuple[tuple[str, str], ...]) -> dict[str, tuple[str, ...]]:
    if not choices: return {}
    signatures = {label: set(意味語(text)) for label, text in choices}; labels = tuple(label for label, _ in choices)
    out: dict[str, tuple[str, ...]] = {}
    for label, _text in choices:
        other_union: set[str] = set()
        for other in labels:
            if other != label: other_union.update(signatures[other])
        distinctive = signatures[label] - other_union
        if not distinctive: distinctive = signatures[label]
        ordered = sorted(distinctive, key=lambda token: (0 if token.startswith("math:") else 1 if any(ch.isdigit() for ch in token) else 2, token))
        out[label] = tuple(_検索表層(token) for token in ordered[:16])
    return out

def _問合せ仕様(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[_HDS問合せ仕様, ...]:
    groups, choices = _役割語群(ir); raw = str(ir.正規化文 or ir.原文)
    base = _切詰め(raw, 280); focus = _焦点抽出(raw)
    structured = _切詰め(" ".join(_unique((*groups["焦点"], *groups["対象"], *groups["関係"], *groups["状態"], *groups["条件"], *groups["その他"]))), 240)
    entity_relation = _切詰め(" ".join(_unique((*groups["対象"], *groups["関係"], *groups["状態"]))), 200)
    entity_only = _切詰め(" ".join(groups["対象"]), 160)
    structural_anchor = structured or entity_relation or entity_only
    anchor = _切詰め(" ".join(_unique((structural_anchor, focus))), 220) or focus or structural_anchor or base
    budget = max(int(最大候補数), len(choices)); nonchoice_slots = max(0, budget - len(choices))
    nonchoice_raw = ((structured, "structured"), (focus, "focus"), (entity_relation, "entity_relation"), (base, "surface"), (entity_only, "entity"))
    specs: list[_HDS問合せ仕様] = []; seen: set[str] = set()
    for query, kind in nonchoice_raw:
        if len(specs) >= nonchoice_slots: break
        key = query.casefold()
        if not query or key in seen: continue
        seen.add(key); specs.append(_HDS問合せ仕様(query, kind))
    distinctive = _候補差分語(choices)
    for label, choice in choices:
        terms = distinctive.get(label, ()); suffix = " ".join(terms) or _切詰め(choice, 120)
        query = _切詰め(" ".join(_unique((anchor, suffix))), 360)
        if not query: continue
        key = query.casefold()
        if key not in seen: seen.add(key)
        specs.append(_HDS問合せ仕様(query, "choice", label))
    return tuple(specs)

def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:
    return tuple(spec.問合せ for spec in _問合せ仕様(ir, 最大候補数=最大候補数))

def _縮退仕様(ir: HDSIR) -> tuple[_HDS問合せ仕様, ...]:
    groups, choices = _役割語群(ir)
    entity = _切詰め(" ".join(groups["対象"]), 160)
    relation = _切詰め(" ".join(_unique((*groups["関係"], *groups["状態"]))), 160)
    contextual = _切詰め(" ".join(_unique((*groups["条件"], *groups["焦点"]))), 160)
    distinctive = _候補差分語(choices); primary = {q.casefold() for q in HDS参照問合せ候補(ir)}
    specs: list[_HDS問合せ仕様] = []; seen: set[str] = set(primary)
    for label, choice in choices:
        suffix = " ".join(distinctive.get(label, ())) or _切詰め(choice, 100)
        for query, kind in ((_切詰め(" ".join(_unique((entity, suffix))), 280), "fallback_choice"), (_切詰め(suffix, 180), "fallback_choice_only")):
            key = query.casefold()
            if not query or key in seen: continue
            seen.add(key); specs.append(_HDS問合せ仕様(query, kind, label))
    for query, kind in ((" ".join(_unique((entity, relation))), "fallback_relation"), (" ".join(_unique((entity, contextual))), "fallback_context"), (entity, "fallback_entity")):
        query = _切詰め(query, 280); key = query.casefold()
        if not query or key in seen: continue
        seen.add(key); specs.append(_HDS問合せ仕様(query, kind))
    return tuple(specs)

def HDS参照縮退問合せ候補(ir: HDSIR) -> tuple[str, ...]:
    return tuple(spec.問合せ for spec in _縮退仕様(ir))

def _条件追加(record: 参照記録, spec: _HDS問合せ仕様) -> 参照記録:
    conditions = list(record.条件); additions = [("hds_query_kind", spec.種別)]
    if spec.候補 is not None: additions.append(("hds_query_choice", spec.候補))
    for item in additions:
        if item not in conditions: conditions.append(item)
    return replace(record, 条件=tuple(conditions))

def _query_pools(provider: 参照供給器, specs: tuple[_HDS問合せ仕様, ...], per_query_limit: int, *, max_parallel: int) -> list[tuple[参照記録, ...]]:
    def run(spec: _HDS問合せ仕様) -> tuple[参照記録, ...]:
        return tuple(_条件追加(record, spec) for record in provider.検索(spec.問合せ, per_query_limit))
    parallel_safe = bool(getattr(provider, "並列安全", False))
    if not parallel_safe or len(specs) <= 1 or max_parallel <= 1:
        pools: list[tuple[参照記録, ...]] = []
        for spec in specs:
            try: pools.append(run(spec))
            except Exception: pools.append(())
        return pools
    workers = min(max(1, int(max_parallel)), len(specs))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-rq") as executor:
        futures = [executor.submit(run, spec) for spec in specs]; pools = []
        for future in futures:
            try: pools.append(tuple(future.result()))
            except Exception: pools.append(())
        return pools

def _記録統合(old: 参照記録, new: 参照記録) -> 参照記録:
    conditions = list(old.条件)
    for condition in new.条件:
        if condition not in conditions: conditions.append(condition)
    return replace(old, 条件=tuple(conditions), 信頼=max(float(old.信頼), float(new.信頼)))

def _round_robin(pools: Iterable[tuple[参照記録, ...]], limit: int) -> tuple[参照記録, ...]:
    pools_tuple = tuple(pools); result: list[参照記録] = []; index_by_id: dict[str, int] = {}; depth = 0
    while True:
        progressed = False
        for pool in pools_tuple:
            if depth >= len(pool): continue
            progressed = True; record = pool[depth]; existing = index_by_id.get(record.識別子)
            if existing is not None: result[existing] = _記録統合(result[existing], record); continue
            if len(result) >= limit: continue
            index_by_id[record.識別子] = len(result); result.append(record)
        if not progressed: break
        depth += 1
    return tuple(result)

def _候補被覆(records: Iterable[参照記録]) -> frozenset[str]:
    labels: set[str] = set()
    for record in records:
        for key, value in record.条件:
            if str(key) == "hds_query_choice" and str(value): labels.add(str(value))
    return frozenset(labels)

def _記録群統合(first: Iterable[参照記録], second: Iterable[参照記録], limit: int) -> tuple[参照記録, ...]:
    result: list[参照記録] = []; index_by_id: dict[str, int] = {}
    for record in (*tuple(first), *tuple(second)):
        existing = index_by_id.get(record.識別子)
        if existing is not None: result[existing] = _記録統合(result[existing], record); continue
        if len(result) >= limit: continue
        index_by_id[record.識別子] = len(result); result.append(record)
    return tuple(result)

def HDS参照検索(provider: 参照供給器, ir: HDSIR, *, 上限: int | None = None, 一問合せ上限: int | None = None, 最大問合せ並列: int | None = None) -> tuple[参照記録, ...]:
    budget = HDS参照予算選択(ir)
    total_limit = budget.取得上限 if 上限 is None else max(0, int(上限)); per_query = budget.一問合せ上限 if 一問合せ上限 is None else max(1, int(一問合せ上限)); parallel = budget.最大問合せ並列 if 最大問合せ並列 is None else max(1, int(最大問合せ並列))
    if total_limit <= 0: return ()
    _, choices = _役割語群(ir); expected_labels = {label for label, _ in choices}; primary_specs = _問合せ仕様(ir)
    primary_records = _round_robin(_query_pools(provider, primary_specs, per_query, max_parallel=parallel), total_limit) if primary_specs else ()
    coverage = set(_候補被覆(primary_records))
    needs_fallback = not primary_records or bool(expected_labels - coverage) or len(primary_records) < min(total_limit, max(2, len(expected_labels)))
    if not needs_fallback: return primary_records
    fallback_specs = _縮退仕様(ir)
    if not fallback_specs: return primary_records
    filtered_specs = tuple(spec for spec in fallback_specs if spec.候補 is None or spec.候補 not in coverage)
    if not filtered_specs: return primary_records
    fallback_records = _round_robin(_query_pools(provider, filtered_specs, per_query, max_parallel=parallel), total_limit)
    return _記録群統合(primary_records, fallback_records, total_limit)

__all__ = ["HDS参照予算", "HDS参照予算選択", "HDS参照問合せ候補", "HDS参照縮退問合せ候補", "HDS参照検索"]
