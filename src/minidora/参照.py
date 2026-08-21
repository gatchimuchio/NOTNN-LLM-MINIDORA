from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Protocol


@dataclass(frozen=True, slots=True)
class 参照記録:
    識別子: str
    対象: str
    内容: str
    由来: str
    供給器: str
    信頼: float = 1.0
    意味キー: str | None = None
    値: Any = None
    時点: str | None = None
    範囲: str | None = None
    条件: tuple[tuple[str, str], ...] = ()
    意味確定: bool = False

    @property
    def 表示値(self) -> Any:
        return self.値 if self.意味キー is not None else self.内容


class 参照供給器(Protocol):
    名称: str

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]: ...


def _検索語(問合せ: str) -> set[str]:
    text = unicodedata.normalize("NFKC", 問合せ).casefold().strip()
    if not text:
        return set()
    text = re.sub(r"[\s、。,.!?！？「」『』（）()【】\[\]：:]+", " ", text)
    text = re.sub(
        r"(?<=[0-9a-z一-龯ぁ-んァ-ン])(?:について|から|まで|より|ので|の|は|が|を|に|で|と|へ|や|も)(?=[0-9a-z一-龯ぁ-んァ-ン])",
        " ",
        text,
    )
    return {part for part in text.split() if part}


def 参照矛盾数(記録群: Iterable[参照記録]) -> int:
    """意味同一性がData側で確定したスロットだけを競合として数える。"""
    groups: dict[
        tuple[str, str, str | None, str | None, tuple[tuple[str, str], ...]],
        set[str],
    ] = {}
    for record in 記録群:
        if record.意味キー is None or not record.意味確定:
            continue
        key = (
            record.対象,
            record.意味キー,
            record.時点,
            record.範囲,
            tuple(record.条件),
        )
        groups.setdefault(key, set()).add(repr(record.値))
    return sum(1 for values in groups.values() if len(values) > 1)


class 固定参照供給器:
    def __init__(self, 記録群: Iterable[参照記録], 名称: str = "固定資料") -> None:
        self.名称 = 名称
        self._記録群 = tuple(記録群)

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]:
        語 = _検索語(問合せ)
        if not 語:
            return self._記録群[:上限]
        採点済み: list[tuple[int, 参照記録]] = []
        for 記録 in self._記録群:
            意味面 = " ".join(
                str(value)
                for value in (
                    記録.対象,
                    記録.意味キー or "",
                    記録.値 if 記録.意味キー is not None else "",
                    記録.時点 or "",
                    記録.範囲 or "",
                    記録.内容,
                )
            )
            本文 = unicodedata.normalize("NFKC", 意味面).casefold()
            点 = sum(1 for token in 語 if token in 本文)
            if 点:
                採点済み.append((点, 記録))
        採点済み.sort(key=lambda x: (-x[0], x[1].識別子))
        return tuple(record for _, record in 採点済み[:上限])


class 複合参照供給器:
    def __init__(self, *供給器群: 参照供給器, 名称: str = "複合参照") -> None:
        self.名称 = 名称
        self._供給器群 = tuple(供給器群)

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]:
        結果: list[参照記録] = []
        既出: set[str] = set()
        for 供給器 in self._供給器群:
            for 記録 in 供給器.検索(問合せ, 上限):
                if 記録.識別子 in 既出:
                    continue
                既出.add(記録.識別子)
                結果.append(記録)
                if len(結果) >= 上限:
                    return tuple(結果)
        return tuple(結果)
