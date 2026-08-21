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


def HDS参照問合せ候補(ir: HDSIR, *, 最大候補数: int = 6) -> tuple[str, ...]:
    """HDS-IRから、外部参照Rへ渡す対称な検索query群を作る。

    1. 正規化文
    2. 確定/推定の意味座標だけで作る主題query
    3. 主題query + 各choice（全候補を同条件で扱う）

    未確定・矛盾・留保した意味は検索queryへ昇格しない。choiceは正解情報ではなく
    入力として与えられた候補集合を対称利用するだけであり、gold labelは参照しない。
    """
    semantic_parts: list[str] = []
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
        semantic_parts.append(content)

    subject = " ".join(_unique(semantic_parts))
    base = " ".join(str(ir.正規化文 or ir.原文).split()).strip()

    queries: list[str] = []
    if base:
        queries.append(base)
    if subject and subject.casefold() != base.casefold():
        queries.append(subject)

    anchor = subject or base
    for _, choice in sorted(choices, key=lambda item: item[0]):
        if anchor:
            queries.append(f"{anchor} {choice}")
        else:
            queries.append(choice)

    return _unique(queries)[:最大候補数]


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
