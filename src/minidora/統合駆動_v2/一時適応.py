from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from ..コア.効果 import 期待効果


@dataclass(frozen=True, slots=True)
class _作用文脈:
    作用定義ID: str
    意味入力署名: str
    種別: str
    契約版: str


@dataclass(frozen=True, slots=True)
class _経験:
    文脈: _作用文脈
    成立: bool
    変化有無: bool
    追加状態: frozenset[str]
    削除状態: frozenset[str]
    解消残差: frozenset[str]
    追加残差: frozenset[str]
    反証: bool = False


def _文脈(機会) -> _作用文脈:
    # 旧作用機会は作用定義ID/意味入力署名を持たないため、宣言済みの旧契約へ縮退する。
    作用ID = str(getattr(機会, "作用ID"))
    作用定義ID = str(getattr(機会, "作用定義ID", "") or 作用ID)
    意味入力署名 = getattr(機会, "意味入力署名", "")
    if not 意味入力署名:
        意味入力署名 = getattr(機会, "作用入力署名", "")
    if not 意味入力署名:
        from ..コア.値 import 署名
        意味入力署名 = 署名((
            作用定義ID,
            tuple(sorted(getattr(機会, "入力状態", ()))),
            tuple(getattr(機会, "読取認識", ())),
            tuple(getattr(機会, "読取成果", ())),
        ))
    return _作用文脈(
        作用定義ID,
        str(意味入力署名),
        str(getattr(機会, "種別")),
        str(getattr(機会, "契約版")),
    )


def _成立か(結果) -> bool:
    状態 = getattr(結果, "状態", None)
    return getattr(状態, "value", 状態) == "成立"


def _既に満たす(機会, 前状態) -> bool:
    if 前状態 is None:
        return False
    出力済み = 機会.出力状態 <= 前状態.成立状態
    解消済み = not bool(機会.解消対象 & 前状態.残差)
    return 出力済み and 解消済み


class HDS一時適応キャッシュ:
    """一回の実行内だけ、同一定義・同一意味入力で観測した効果を共有する。"""

    __slots__ = ("_経験列",)

    def __init__(self, 最大経験数: int = 256) -> None:
        if type(最大経験数) is not int or not 1 <= 最大経験数 <= 4096:
            raise ValueError("最大経験数は1..4096の整数が必要")
        self._経験列 = deque(maxlen=最大経験数)

    def 結果を受け取る(self, 機会, 結果, 状態差, 前状態=None) -> None:
        if str(機会.作用ID).startswith("内的/"):
            return
        成立 = _成立か(結果)
        変化 = bool(状態差.変化有無)
        # 同じ意味入力で実行失敗した場合、以前の成功期待をそのまま残さない。
        # 成功かつ無変化は、既に効果が成立していた場合は反証にしない。
        反証 = (not 成立) or (成立 and not 変化 and not _既に満たす(機会, 前状態))
        self._経験列.append(
            _経験(
                _文脈(機会),
                成立,
                変化,
                frozenset(状態差.追加状態),
                frozenset(状態差.削除状態),
                frozenset(状態差.解消残差),
                frozenset(状態差.追加残差),
                反証,
            )
        )

    def _安定効果(self, 機会) -> 期待効果:
        文脈 = _文脈(機会)
        対象 = [x for x in self._経験列 if x.文脈 == 文脈]
        if not 対象:
            return 期待効果()
        # 最新の反証より前の成功は再利用しない。
        最後の反証 = max((i for i, x in enumerate(対象) if x.反証), default=-1)
        有効 = [x for x in 対象[最後の反証 + 1:] if x.成立 and x.変化有無]
        if not 有効:
            return 期待効果()

        追加 = set(有効[0].追加状態)
        削除 = set(有効[0].削除状態)
        解消 = set(有効[0].解消残差)
        追加残差 = set(有効[0].追加残差)
        for 経験 in 有効[1:]:
            追加.intersection_update(経験.追加状態)
            削除.intersection_update(経験.削除状態)
            解消.intersection_update(経験.解消残差)
            追加残差.intersection_update(経験.追加残差)
        return 期待効果(frozenset(追加), frozenset(削除), frozenset(解消),
                      frozenset(追加残差), len(有効))

    def 機会を補正(self, 機会):
        if str(機会.作用ID).startswith("内的/"):
            return 機会
        効果 = self._安定効果(機会)
        if 効果.空:
            return 機会
        # 契約効果は変更せず、経験由来の期待だけ別欄へ保持する。
        return replace(機会, 期待=効果)
