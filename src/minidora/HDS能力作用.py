from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .HDS実行主体 import (
    HDS作用機会,
    HDS作用結果,
    HDS作用状態,
    HDS実行状態,
)
from .製品版.能力契約 import 能力モジュール, 能力文脈
from .採否 import 実行状態


@dataclass(frozen=True, slots=True)
class HDS能力作用設定:
    出力状態: frozenset[str]
    入力状態: frozenset[str] = frozenset()
    解消対象: frozenset[str] = frozenset()
    資源負荷: int = 1
    追加残差接頭辞: str = "能力未成立"


class HDS能力モジュール作用:
    """既存の能力モジュールをHDS-first実行主体から呼ぶためのAdapter。

    能力モジュールの判定値は作用候補内の優先度情報としてのみ扱い、最終採用・
    回答正しさ・HDS判断へ読み替えない。COMMITはHDS実行主体だけが行う。
    """

    def __init__(
        self,
        モジュール: 能力モジュール,
        文脈: 能力文脈,
        *,
        出力状態: Sequence[str] = (),
        入力状態: Sequence[str] = (),
        解消対象: Sequence[str] = (),
        資源負荷: int = 1,
    ) -> None:
        name = str(getattr(モジュール, "名前", "")).strip()
        version = str(getattr(モジュール, "版", "")).strip()
        if not name or not version:
            raise ValueError("HDS能力作用には名前と版を持つ能力モジュールが必要")
        if not isinstance(文脈, 能力文脈):
            raise TypeError("HDS能力作用には能力文脈が必要")
        self.モジュール = モジュール
        self.文脈 = 文脈
        self.作用ID = f"能力:{name}@{version}"
        self.設定 = HDS能力作用設定(
            frozenset(str(x) for x in (出力状態 or (f"能力:{name}:成立",))),
            frozenset(str(x) for x in 入力状態),
            frozenset(str(x) for x in 解消対象),
            max(0, int(資源負荷)),
        )

    def _判定値(self) -> float:
        try:
            return max(0.0, min(1.0, float(self.モジュール.判定(self.文脈))))
        except Exception:
            return 0.0

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        score = self._判定値()
        if score <= 0.0:
            return None
        # 文脈はこの作用Adapter生成時に固定されている。HDS作業状態が変化すれば
        # 作用入力署名も変わり、同じ能力を別状態で再評価できる。
        signature = f"{状態.状態署名}:{self.作用ID}:{score:.12f}"
        return HDS作用機会(
            self.作用ID,
            signature,
            self.設定.入力状態,
            self.設定.出力状態,
            self.設定.解消対象,
            self.設定.資源負荷,
            score,
            True,
            (f"CAPABILITY_SCORE:{score:.12f}", "HDS_CAPABILITY_OPPORTUNITY"),
        )

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        try:
            result = self.モジュール.実行(self.文脈)
        except Exception as exc:
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({f"能力例外:{self.作用ID}:{type(exc).__name__}"}),
                理由=("CAPABILITY_EXCEPTION", type(exc).__name__),
            )

        effective = result.状態
        output_name = f"能力結果:{self.モジュール.名前}"
        if result.成立 is True and effective == 実行状態.合格:
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=self.設定.出力状態,
                解消残差=self.設定.解消対象,
                成果=((output_name, result),),
                理由=("CAPABILITY_SUCCEEDED",),
            )

        reason = str(getattr(result, "保留理由", "") or effective.value)
        residual = f"{self.設定.追加残差接頭辞}:{self.モジュール.名前}:{reason}"
        state = HDS作用状態.失敗 if effective == 実行状態.失敗 else HDS作用状態.保留
        return HDS作用結果(
            state,
            追加残差=frozenset({residual}),
            成果=((output_name, result),),
            理由=("CAPABILITY_NOT_COMMITTED", reason),
        )


__all__ = ["HDS能力作用設定", "HDS能力モジュール作用"]
