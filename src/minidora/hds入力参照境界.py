from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .hds_ir import HDSIR
from .参照 import 参照記録


@dataclass(frozen=True, slots=True)
class HDS入力Data束:
    """HDS Compilerで構文化したDataをMINIDORA入力へ整列する前段境界。"""

    IR群: tuple[HDSIR, ...]
    出典ID群: tuple[str, ...]
    信頼群: tuple[float, ...]
    成功記録群: tuple[参照記録, ...]
    失敗数: int


def HDS入力出典ID(record: 参照記録) -> str:
    identifier = str(record.識別子).strip()
    if identifier:
        return identifier
    provider = str(record.供給器).strip()
    origin = str(record.由来).strip()
    fallback = ":".join(part for part in (provider, origin) if part)
    return fallback or "anonymous-reference"


def HDS入力Data整列(
    references: Sequence[参照記録],
    payloads: Sequence[HDSIR | Exception],
    射影: Callable[[HDSIR], HDSIR],
) -> HDS入力Data束:
    """成功したDataだけをMINIDORA入力用に同一添字で保持する。

    ここは前段入力境界であり、後段HDS判断主体の入力ではない。
    """
    if len(references) != len(payloads):
        raise ValueError("参照記録とDataコンパイル結果は同数である必要がある")

    irs: list[HDSIR] = []
    ids: list[str] = []
    trusts: list[float] = []
    records: list[参照記録] = []
    failed = 0
    for record, payload in zip(references, payloads):
        if isinstance(payload, Exception):
            failed += 1
            continue
        irs.append(射影(payload))
        ids.append(HDS入力出典ID(record))
        trusts.append(float(record.信頼))
        records.append(record)
    return HDS入力Data束(tuple(irs), tuple(ids), tuple(trusts), tuple(records), failed)


__all__ = ["HDS入力Data束", "HDS入力出典ID", "HDS入力Data整列"]
