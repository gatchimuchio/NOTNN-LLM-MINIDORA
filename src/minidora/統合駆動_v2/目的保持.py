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
    閉包済み: bool

    @property
    def 直接尺度(self) -> tuple[int, int, int]:
        return (
            0 if self.閉包済み else 1,
            len(self.未達状態) + len(self.未達認識),
            len(self.残差),
        )

    @property
    def 未充足署名(self) -> str:
        return 署名((self.未達状態, self.未達認識, self.残差))


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
        bool(状態.閉包済み),
    )


def 目的未充足ノード(状態, 認識有効判定, *, 必要認識=(), 修復状態=(), 修復認識=()):
    """現在目的から逆算した未充足ノードを修飾名で返す。

    目的に関係しない再評価待ち・学習状態・主体内部状態は根にしない。
    """
    nodes = {"状態:" + str(x) for x in 状態.要求状態 if x not in 状態.成立状態}
    nodes.update("残差:" + str(x) for x in 状態.残差)
    required = set(状態.要求認識) | set(必要認識) | set(修復認識)
    nodes.update("認識:" + str(x) for x in required if not 認識有効判定(状態, x))
    nodes.update("状態:" + str(x) for x in 修復状態 if x not in 状態.成立状態)
    return frozenset(nodes)


def 作用が目的経路に属する(
    状態, 機会, *, 認識有効判定, 関連作用ID=(), 必要認識=(), 修復状態=(), 修復認識=(), 計画仕様=None,
):
    """作用を「実行可能」ではなく「現在目的へ接続する」ことでゲートする。

    学習済み期待効果は目的関連性の根拠にしない。静的契約、明示された前処理依存、
    実際の未充足認識への識別だけを採用する。
    """
    nodes = 目的未充足ノード(状態, 認識有効判定, 必要認識=必要認識, 修復状態=修復状態, 修復認識=修復認識)
    if not nodes:
        return False
    if 機会.作用ID in set(関連作用ID):
        return True

    unmet_states = {x[3:] for x in nodes if x.startswith("状態:")}
    residuals = {x[3:] for x in nodes if x.startswith("残差:")}
    recognitions = {x[3:] for x in nodes if x.startswith("認識:")}

    if 計画仕様 is not None:
        if set(計画仕様.追加状態) & unmet_states:
            return True
        if set(計画仕様.解消残差) & residuals:
            return True
    else:
        if set(機会.出力状態) & unmet_states:
            return True
        if set(機会.解消対象) & residuals:
            return True

    if set(機会.識別対象) & recognitions:
        return True
    if set(getattr(機会, "目的依存", ())) & nodes:
        return True
    return False


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
    最良直接尺度: tuple[int, int, int],
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


__all__ = ["HDS目的観測", "目的契約署名", "目的を観測", "目的未充足ノード", "作用が目的経路に属する", "計画効果を実測", "目的進展を判定"]
