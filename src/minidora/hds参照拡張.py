from __future__ import annotations

from typing import Iterable

from .hds_ir import HDSIR
from .hds_reference import (
    HDS参照予算選択,
    HDS参照検索,
    _候補被覆,
    _query_pools,
    _round_robin,
    _役割語群,
    _縮退仕様,
    _記録統合,
)
from .参照 import 参照供給器, 参照記録


def _候補ラベル群(record: 参照記録) -> frozenset[str]:
    return frozenset(
        str(value)
        for key, value in record.条件
        if str(key) == "hds_query_choice" and str(value)
    )


def HDS候補被覆優先統合(
    primary: Iterable[参照記録],
    extra: Iterable[参照記録],
    expected_labels: Iterable[str],
    limit: int,
) -> tuple[参照記録, ...]:
    """候補別queryで観測できたsourceを対称に残してから、残枠へ通常順を戻す。"""
    total_limit = max(0, int(limit))
    if total_limit <= 0:
        return ()

    combined: list[参照記録] = []
    index_by_id: dict[str, int] = {}
    for record in (*tuple(primary), *tuple(extra)):
        source_id = str(record.識別子)
        existing = index_by_id.get(source_id)
        if existing is not None:
            combined[existing] = _記録統合(combined[existing], record)
            continue
        index_by_id[source_id] = len(combined)
        combined.append(record)

    selected: list[参照記録] = []
    selected_ids: set[str] = set()
    for label in sorted({str(item) for item in expected_labels if str(item)}):
        candidate = next(
            (
                record
                for record in combined
                if str(record.識別子) not in selected_ids and label in _候補ラベル群(record)
            ),
            None,
        )
        if candidate is None:
            continue
        selected.append(candidate)
        selected_ids.add(str(candidate.識別子))
        if len(selected) >= total_limit:
            return tuple(selected)

    for record in combined:
        source_id = str(record.識別子)
        if source_id in selected_ids:
            continue
        selected.append(record)
        selected_ids.add(source_id)
        if len(selected) >= total_limit:
            break
    return tuple(selected)


def HDS参照検索強化(
    provider: 参照供給器,
    ir: HDSIR,
    *,
    上限: int | None = None,
    一問合せ上限: int | None = None,
    最大問合せ並列: int | None = None,
    最大候補補完回数: int = 1,
) -> tuple[参照記録, ...]:
    """既存Rを保持しつつ、generic hitで候補fallbackが潰れる欠陥だけを補修する。"""
    budget = HDS参照予算選択(ir)
    total_limit = budget.取得上限 if 上限 is None else max(0, int(上限))
    per_query = budget.一問合せ上限 if 一問合せ上限 is None else max(1, int(一問合せ上限))
    parallel = budget.最大問合せ並列 if 最大問合せ並列 is None else max(1, int(最大問合せ並列))
    if total_limit <= 0:
        return ()

    references = HDS参照検索(
        provider,
        ir,
        上限=total_limit,
        一問合せ上限=per_query,
        最大問合せ並列=parallel,
    )
    _, choices = _役割語群(ir)
    expected = {label for label, _ in choices}
    if not expected:
        return references

    for _ in range(max(0, int(最大候補補完回数))):
        coverage = set(_候補被覆(references))
        missing = expected - coverage
        if not missing:
            break
        fallback_specs = tuple(
            spec
            for spec in _縮退仕様(ir)
            if spec.候補 is not None and spec.候補 in missing
        )
        if not fallback_specs:
            break
        extra = _round_robin(
            _query_pools(provider, fallback_specs, per_query, max_parallel=parallel),
            total_limit,
        )
        if not extra:
            break
        merged = HDS候補被覆優先統合(references, extra, expected, total_limit)
        before = tuple((record.識別子, record.条件) for record in references)
        after = tuple((record.識別子, record.条件) for record in merged)
        references = merged
        if after == before:
            break
    return references


def HDS追加参照検索(
    provider: 参照供給器,
    ir: HDSIR,
    *,
    段階: int = 1,
    最大取得上限: int = 32,
) -> tuple[参照記録, ...]:
    """HDS介入時だけ既存Rの予算を段階的に広げて再観測する。"""
    budget = HDS参照予算選択(ir)
    factor = max(2, 1 + int(段階))
    total_limit = min(max(1, int(最大取得上限)), max(budget.取得上限, budget.取得上限 * factor))
    per_query = min(total_limit, max(budget.一問合せ上限, budget.一問合せ上限 * factor))
    return HDS参照検索強化(
        provider,
        ir,
        上限=total_limit,
        一問合せ上限=per_query,
        最大問合せ並列=budget.最大問合せ並列,
        最大候補補完回数=1,
    )


__all__ = ["HDS候補被覆優先統合", "HDS参照検索強化", "HDS追加参照検索"]
