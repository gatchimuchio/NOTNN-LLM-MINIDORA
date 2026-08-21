from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
    並列安全 = True

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
    """複数Providerを並列取得し、Provider順を保ったround-robinで統合する。"""

    並列安全 = True

    def __init__(
        self,
        *供給器群: 参照供給器,
        名称: str = "複合参照",
        並列: bool = True,
        最大並列: int = 4,
    ) -> None:
        self.名称 = 名称
        self._供給器群 = tuple(供給器群)
        self.並列 = bool(並列)
        self.最大並列 = max(1, int(最大並列))
        self.最後のエラー: tuple[tuple[str, str], ...] = ()

    def _取得(self, provider: 参照供給器, 問合せ: str, 上限: int) -> tuple[参照記録, ...]:
        return tuple(provider.検索(問合せ, 上限))

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]:
        if 上限 <= 0 or not self._供給器群:
            return ()

        pools: list[tuple[参照記録, ...]] = []
        errors: list[tuple[str, str]] = []
        if self.並列 and len(self._供給器群) > 1:
            workers = min(self.最大並列, len(self._供給器群))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-r") as executor:
                futures = [executor.submit(self._取得, provider, 問合せ, 上限) for provider in self._供給器群]
                for provider, future in zip(self._供給器群, futures):
                    try:
                        pools.append(future.result())
                    except Exception as exc:
                        pools.append(())
                        errors.append((str(getattr(provider, "名称", type(provider).__name__)), f"{type(exc).__name__}: {exc}"))
        else:
            for provider in self._供給器群:
                try:
                    pools.append(self._取得(provider, 問合せ, 上限))
                except Exception as exc:
                    pools.append(())
                    errors.append((str(getattr(provider, "名称", type(provider).__name__)), f"{type(exc).__name__}: {exc}"))
        self.最後のエラー = tuple(errors)

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
