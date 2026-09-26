"""実経験から純粋作用の安定効果を形成し、保留時の回復計画にだけ利用する。

通常実行の契約効果・採否・既存出力は変更しない。経験由来の期待は、明示的に
純粋と宣言された作用について、複数の異なる実入力で同じ実測差が反復した場合だけ
形成する。反証後は、それ以前の成功経験を再利用しない。
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from ..コア.効果 import 期待効果
from .値 import 文字, 整数

HDS経験学習器版 = "MINIDORA-EXPERIENCE-LEARNING-v1"


@dataclass(frozen=True, slots=True)
class _作用族:
    作用定義ID: str
    契約版: str

    def __post_init__(self):
        文字(self.作用定義ID, "作用定義ID")
        文字(self.契約版, "作用契約版")


@dataclass(frozen=True, slots=True)
class _実経験:
    作用族: _作用族
    入力署名: str
    成立: bool
    変化有無: bool
    追加状態: frozenset[str] = frozenset()
    削除状態: frozenset[str] = frozenset()
    解消残差: frozenset[str] = frozenset()
    追加残差: frozenset[str] = frozenset()

    def __post_init__(self):
        文字(self.入力署名, "経験入力署名")


def _作用族を取る(作用) -> _作用族 | None:
    仕様 = getattr(作用, "計画仕様", None)
    if 仕様 is None or getattr(仕様, "純粋", False) is not True:
        return None
    定義ID = str(getattr(作用, "作用定義ID", "") or getattr(作用, "作用ID", ""))
    版 = str(getattr(仕様, "版", "") or getattr(作用, "契約版", "") or "v1")
    if not 定義ID or not 版:
        return None
    return _作用族(定義ID, 版)


def _成立か(作用状態) -> bool:
    return getattr(作用状態, "value", 作用状態) == "成立"


class HDS経験学習器:
    """同一実行系の実経験から、純粋作用の条件付き安定効果だけを形成する。

    永続ファイルや大域共有を持たない。通常経路では参照せず、呼出側が保留時の
    回復計画へ明示的に接続した場合だけ期待効果を返す。
    """

    __slots__ = ("_経験列", "最小汎化文脈数")

    def __init__(self, 最大経験数: int = 2048, 最小汎化文脈数: int = 2) -> None:
        整数(最大経験数, "最大学習経験数", 2, 65536)
        整数(最小汎化文脈数, "最小汎化文脈数", 2, 256)
        if 最小汎化文脈数 > 最大経験数:
            raise ValueError("最小汎化文脈数は最大経験数以下である必要がある")
        self._経験列 = deque(maxlen=最大経験数)
        self.最小汎化文脈数 = 最小汎化文脈数

    def 初期化(self) -> None:
        self._経験列.clear()

    @property
    def 経験数(self) -> int:
        return len(self._経験列)

    def 結果列を受け取る(self, 作用群, 実行結果) -> int:
        """確定した実行履歴からのみ経験を取り込む。

        動的供給器の作用や、純粋性を宣言していない作用は対象外。状態差は実行履歴に
        確定した差だけを使い、作用が返した自己申告効果だけでは学習しない。
        """
        作用表 = {str(getattr(a, "作用ID", "")): a for a in tuple(作用群)}
        追加 = 0
        for 行 in tuple(getattr(実行結果, "履歴", ())):
            作用 = 作用表.get(str(getattr(行, "作用ID", "")))
            族 = _作用族を取る(作用) if 作用 is not None else None
            if 族 is None:
                continue
            差 = getattr(行, "状態差", None)
            if 差 is None:
                continue
            成立 = _成立か(getattr(行, "作用状態", None)) and getattr(行, "阻害", None) is None
            変化 = bool(getattr(差, "変化有無", False))
            if 成立 and not 変化:
                continue
            入力署名 = str(getattr(行, "作用入力署名", ""))
            if not 入力署名:
                continue
            self._経験列.append(_実経験(
                族,
                入力署名,
                成立,
                変化,
                frozenset(getattr(差, "追加状態", ())),
                frozenset(getattr(差, "削除状態", ())),
                frozenset(getattr(差, "解消残差", ())),
                frozenset(getattr(差, "追加残差", ())),
            ))
            追加 += 1
        return 追加

    def _安定効果(self, 作用) -> 期待効果:
        族 = _作用族を取る(作用)
        if 族 is None:
            return 期待効果()
        対象 = [x for x in self._経験列 if x.作用族 == 族]
        if not 対象:
            return 期待効果()

        最後の反証 = max((i for i, x in enumerate(対象) if not x.成立), default=-1)
        成功 = [x for x in 対象[最後の反証 + 1:] if x.成立 and x.変化有無]
        if not 成功:
            return 期待効果()

        文脈別: dict[str, list[_実経験]] = {}
        for 経験 in 成功:
            文脈別.setdefault(経験.入力署名, []).append(経験)
        if len(文脈別) < self.最小汎化文脈数:
            return 期待効果()

        文脈効果 = []
        for 入力署名 in sorted(文脈別):
            rows = 文脈別[入力署名]
            追加状態 = set(rows[0].追加状態)
            削除状態 = set(rows[0].削除状態)
            解消残差 = set(rows[0].解消残差)
            追加残差 = set(rows[0].追加残差)
            for row in rows[1:]:
                追加状態.intersection_update(row.追加状態)
                削除状態.intersection_update(row.削除状態)
                解消残差.intersection_update(row.解消残差)
                追加残差.intersection_update(row.追加残差)
            文脈効果.append((追加状態, 削除状態, 解消残差, 追加残差))

        追加状態, 削除状態, 解消残差, 追加残差 = (set(x) for x in 文脈効果[0])
        for a, d, r, ar in 文脈効果[1:]:
            追加状態.intersection_update(a)
            削除状態.intersection_update(d)
            解消残差.intersection_update(r)
            追加残差.intersection_update(ar)
        return 期待効果(
            frozenset(追加状態),
            frozenset(削除状態),
            frozenset(解消残差),
            frozenset(追加残差),
            len(文脈別),
        )

    def 計画仕様を補正(self, 作用):
        """契約仕様を変更せず、回復実行用の複製へ経験由来効果だけを合成する。"""
        仕様 = getattr(作用, "計画仕様", None)
        if 仕様 is None:
            return None
        効果 = self._安定効果(作用)
        if 効果.空:
            return 仕様
        追加状態 = (仕様.追加状態 | 効果.追加状態) - 仕様.削除状態
        削除状態 = (仕様.削除状態 | 効果.削除状態) - 仕様.追加状態
        解消残差 = (仕様.解消残差 | 効果.解消残差) - 仕様.追加残差
        追加残差 = (仕様.追加残差 | 効果.追加残差) - 仕様.解消残差
        return replace(仕様, 追加状態=追加状態, 削除状態=削除状態,
                       解消残差=解消残差, 追加残差=追加残差)

    def 機会を補正(self, 作用, 機会):
        """既存期待がない時だけ、複数文脈で成立した学習効果を回復計画へ付与する。"""
        現期待 = getattr(機会, "期待", 期待効果())
        if not 現期待.空:
            return 機会
        効果 = self._安定効果(作用)
        if 効果.空:
            return 機会
        return replace(機会, 期待=効果)

    def 利用可能(self, 作用群=()) -> bool:
        if 作用群:
            return any(not self._安定効果(a).空 for a in tuple(作用群))
        族群 = {x.作用族 for x in self._経験列}
        for 族 in 族群:
            対象 = [x for x in self._経験列 if x.作用族 == 族]
            最後の反証 = max((i for i, x in enumerate(対象) if not x.成立), default=-1)
            文脈 = {x.入力署名 for x in 対象[最後の反証 + 1:] if x.成立 and x.変化有無}
            if len(文脈) >= self.最小汎化文脈数:
                return True
        return False


__all__ = ["HDS経験学習器版", "HDS経験学習器"]
