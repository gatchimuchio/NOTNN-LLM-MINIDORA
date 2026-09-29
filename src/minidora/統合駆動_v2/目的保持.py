"""目的の正本と未充足を固定し、状態変化と目的進展を分離する。"""
from __future__ import annotations
from dataclasses import dataclass
from .値 import 署名


@dataclass(frozen=True, slots=True)
class HDS目的観測:
    契約署名: str
    未達状態: frozenset[str]
    未達認識: frozenset[str]
    残差: frozenset[str]
    再評価待ち: frozenset[str]
    閉包済み: bool

    @property
    def 直接尺度(self) -> tuple[int, int, int, int]:
        return (
            0 if self.閉包済み else 1,
            len(self.未達状態) + len(self.未達認識),
            len(self.残差),
            len(self.再評価待ち),
        )

    @property
    def 未充足署名(self) -> str:
        return 署名((self.未達状態, self.未達認識, self.残差, self.再評価待ち))


def 目的契約署名(状態) -> str:
    主体 = 状態.主体辞書()
    return 署名((
        tuple(状態.目的),
        frozenset(状態.要求状態),
        frozenset(状態.要求認識),
        tuple(主体.get("HDS目的正本", ())),
    ))


def 目的を観測(状態, 認識有効判定, *, 契約署名: str | None = None) -> HDS目的観測:
    現契約 = 目的契約署名(状態)
    if 契約署名 is not None and 現契約 != 契約署名:
        raise ValueError("実行中に目的契約を変更できない")
    未達認識 = frozenset(k for k in 状態.要求認識 if not 認識有効判定(状態, k))
    return HDS目的観測(
        現契約,
        frozenset(状態.要求状態 - 状態.成立状態),
        未達認識,
        frozenset(状態.残差),
        frozenset(状態.再評価待ち),
        bool(状態.閉包済み),
    )


def 計画効果を実測(状態差, 計画仕様) -> bool:
    if 計画仕様 is None:
        return False
    return bool(
        set(状態差.追加状態) & set(計画仕様.追加状態)
        or set(状態差.解消残差) & set(計画仕様.解消残差)
    )


def 目的進展を判定(
    *,
    前観測: HDS目的観測,
    後観測: HDS目的観測,
    最良直接尺度: tuple[int, int, int, int],
    計画長: int = 0,
    計画仕様=None,
    状態差=None,
    計画最良残数: dict[str, int] | None = None,
):
    """目的未充足の縮小、または目的計画の実測前進だけを進展とする。"""
    if 前観測.契約署名 != 後観測.契約署名:
        raise ValueError("目的契約が途中で変化した")
    新最良 = min(最良直接尺度, 後観測.直接尺度)
    直接進展 = 後観測.直接尺度 < 最良直接尺度
    計画進展 = False
    if not 直接進展 and 計画長 > 0 and 状態差 is not None and 計画効果を実測(状態差, 計画仕様):
        台帳 = 計画最良残数 if 計画最良残数 is not None else {}
        残数 = max(0, 計画長 - 1)
        過去 = 台帳.get(前観測.未充足署名)
        if 過去 is None or 残数 < 過去:
            台帳[前観測.未充足署名] = 残数
            計画進展 = True
    return 直接進展 or 計画進展, 新最良


__all__ = ["HDS目的観測", "目的契約署名", "目的を観測", "計画効果を実測", "目的進展を判定"]
