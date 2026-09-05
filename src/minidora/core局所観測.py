from __future__ import annotations

from dataclasses import replace
import unicodedata
from typing import Sequence

from .hds_ir import HDSIR
from .hds局所再照合 import HDS局所Window候補
from .参照 import 参照記録


def _正規化(text: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(text)).split()).strip()


def MINIDORA局所観測view(
    question_ir: HDSIR,
    references: Sequence[参照記録],
    *,
    上限: int = 12,
) -> tuple[tuple[参照記録, ...], int]:
    """同じsource identityのまま、問いと候補差分が共存する局所窓へ観測viewを絞る。

    これはDataの追加取得・候補採用・gold参照を行わない。
    元の参照集合とsource identityを保持し、本文viewだけを一時的に置換する。
    """
    refs = tuple(references)
    windows = HDS局所Window候補(question_ir, refs, 上限=max(0, int(上限)))
    best_by_source = {}
    for row in windows:
        source_id = str(row.参照.識別子)
        if source_id not in best_by_source:
            best_by_source[source_id] = row

    changed = 0
    projected: list[参照記録] = []
    for record in refs:
        row = best_by_source.get(str(record.識別子))
        if row is None or _正規化(row.内容).casefold() == _正規化(record.内容).casefold():
            projected.append(record)
            continue
        conditions = list(record.条件)
        marker = ("minidora_observation_view", "local")
        if marker not in conditions:
            conditions.append(marker)
        projected.append(replace(record, 内容=row.内容, 条件=tuple(conditions)))
        changed += 1
    return tuple(projected), changed


__all__ = ["MINIDORA局所観測view"]
