from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class _作用文脈:
    作用ID: str
    入力状態: tuple[str, ...]
    読取認識: tuple[str, ...]
    読取成果: tuple[str, ...]
    種別: str
    契約版: str


@dataclass(frozen=True, slots=True)
class _経験:
    文脈: _作用文脈
    成立: bool
    変化有無: bool
    追加状態: frozenset[str]
    解消残差: frozenset[str]


def _文脈(機会) -> _作用文脈:
    return _作用文脈(
        str(機会.作用ID),
        tuple(sorted(機会.入力状態)),
        tuple(sorted(機会.読取認識)),
        tuple(sorted(機会.読取成果)),
        str(機会.種別),
        str(機会.契約版),
    )


def _成立か(結果) -> bool:
    状態 = getattr(結果, "状態", None)
    return getattr(状態, "value", 状態) == "成立"


class HDS一時適応キャッシュ:
    __slots__ = ("_経験列",)

    def __init__(self, 最大経験数: int = 256) -> None:
        if type(最大経験数) is not int or not 1 <= 最大経験数 <= 4096:
            raise ValueError("最大経験数は1..4096の整数が必要")
        self._経験列 = deque(maxlen=最大経験数)

    def 結果を受け取る(self, 機会, 結果, 状態差) -> None:
        if str(機会.作用ID).startswith("内的/"):
            return
        self._経験列.append(
            _経験(
                _文脈(機会),
                _成立か(結果),
                bool(状態差.変化有無),
                frozenset(状態差.追加状態),
                frozenset(状態差.解消残差),
            )
        )

    def _安定効果(self, 機会) -> tuple[frozenset[str], frozenset[str]]:
        文脈 = _文脈(機会)
        有効 = [x for x in self._経験列 if x.文脈 == 文脈 and x.成立 and x.変化有無]
        if not 有効:
            return frozenset(), frozenset()

        追加 = set(有効[0].追加状態)
        解消 = set(有効[0].解消残差)
        for 経験 in 有効[1:]:
            追加.intersection_update(経験.追加状態)
            解消.intersection_update(経験.解消残差)
        return frozenset(追加), frozenset(解消)

    def 機会を補正(self, 機会):
        if str(機会.作用ID).startswith("内的/"):
            return 機会
        追加状態, 解消残差 = self._安定効果(機会)
        if not 追加状態 and not 解消残差:
            return 機会
        return replace(
            機会,
            出力状態=機会.出力状態 | 追加状態,
            解消対象=機会.解消対象 | 解消残差,
        )
