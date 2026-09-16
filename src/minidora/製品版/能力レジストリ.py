from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Mapping, Sequence

from .能力契約 import 能力モジュール, 能力文脈


レジストリ版 = '能力-登録簿-v1'


@dataclass(frozen=True, slots=True)
class 能力候補:
    モジュール: 能力モジュール
    信頼: float


@dataclass(frozen=True, slots=True)
class 能力選択:
    モジュール: 能力モジュール
    信頼: float
    候補: tuple[tuple[str, float], ...]


class 能力レジストリ:
    """登録能力の目録。

    `選択` は旧製品経路の互換入口として保持する。HDS-first経路では `候補群` / `HDS作用群`
    を使い、レジストリ自身を最終的な能力選択主体にしない。
    """

    def __init__(self, modules: tuple[能力モジュール, ...] = ()) -> None:
        self._lock = RLock()
        self._modules: dict[str, 能力モジュール] = {}
        for module in modules:
            self.登録(module)

    def 登録(self, モジュール: 能力モジュール) -> None:
        name = str(モジュール.名前).strip()
        if not name:
            raise ValueError('モジュール名が空')
        with self._lock:
            self._modules[name] = モジュール

    def 解除(self, name: str) -> None:
        with self._lock:
            self._modules.pop(name, None)

    def 一覧(self) -> tuple[能力モジュール, ...]:
        with self._lock:
            return tuple(
                sorted(self._modules.values(), key=lambda module: (-int(module.優先度), module.名前))
            )

    def 候補群(self, 文脈: 能力文脈, min_score: float = 0.01) -> tuple[能力候補, ...]:
        """適用可能な全能力を返す。ここでは勝者を確定しない。"""
        scored: list[tuple[float, int, str, 能力モジュール]] = []
        for module in self.一覧():
            try:
                score = max(0.0, min(1.0, float(module.判定(文脈))))
            except Exception:
                score = 0.0
            if score >= min_score:
                scored.append((score, int(module.優先度), module.名前, module))
        scored.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
        return tuple(能力候補(module, score) for score, _, _, module in scored)

    def 選択(self, 文脈: 能力文脈, min_score: float = 0.01) -> 能力選択 | None:
        """旧製品ABI。HDS-firstでは使用せず、既存挙動を完全維持する。"""
        candidates = self.候補群(文脈, min_score=min_score)
        if not candidates:
            return None
        top = candidates[0]
        return 能力選択(
            top.モジュール,
            top.信頼,
            tuple((item.モジュール.名前, item.信頼) for item in candidates),
        )

    def HDS作用群(
        self,
        文脈: 能力文脈,
        *,
        出力状態: Mapping[str, Sequence[str]] | None = None,
        入力状態: Mapping[str, Sequence[str]] | None = None,
        解消対象: Mapping[str, Sequence[str]] | None = None,
        min_score: float = 0.01,
    ):
        """登録能力をHDS-first実行主体が選べる作用群へ射影する。

        作用の意味契約は呼出側が明示する。能力名や判定値から要求状態・残差を推測しない。
        """
        from ..HDS能力作用 import HDS能力モジュール作用

        outputs = dict(出力状態 or {})
        inputs = dict(入力状態 or {})
        residuals = dict(解消対象 or {})
        return tuple(
            HDS能力モジュール作用(
                item.モジュール,
                文脈,
                出力状態=outputs.get(item.モジュール.名前, ()),
                入力状態=inputs.get(item.モジュール.名前, ()),
                解消対象=residuals.get(item.モジュール.名前, ()),
            )
            for item in self.候補群(文脈, min_score=min_score)
        )


__all__ = ["レジストリ版", "能力候補", "能力選択", "能力レジストリ"]
