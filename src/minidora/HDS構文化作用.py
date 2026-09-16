from __future__ import annotations

from hashlib import sha256
import inspect
from typing import Sequence

from .HDS実行主体 import HDS作用機会, HDS作用結果, HDS作用状態, HDS実行状態
from .HDS中間表現 import HDSIR


class HDS構文化作用:
    """自然言語入力をHDS自身の作業状態へ構文化する知覚作用。

    構文化器は採否・回答生成を行わず、生成したHDS-IRと意味残差をHDS実行主体へ帰還する。
    `HDSIR.実行可能` は旧計算実行境界なので、計算閉包を明示要求した場合だけ残差化する。
    """

    def __init__(
        self,
        構文化器,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈=None,
        入力状態: Sequence[str] = (),
        出力状態: str = "HDS意味構文化済み",
        解消対象: Sequence[str] = ("入力未構文化",),
        実行閉包要求: bool = False,
    ) -> None:
        compile_fn = getattr(構文化器, "コンパイル", None)
        if not callable(compile_fn):
            raise TypeError("HDS構文化作用にはコンパイル可能な構文化器が必要")
        self.構文化器 = 構文化器
        self.入力 = str(入力)
        self.前回結果 = 前回結果
        self.HDS履歴 = tuple(HDS履歴)
        self.文脈 = 文脈
        self.入力状態 = frozenset(str(x) for x in 入力状態)
        self.出力状態 = str(出力状態)
        self.解消対象 = frozenset(str(x) for x in 解消対象)
        self.実行閉包要求 = bool(実行閉包要求)
        self.作用ID = "HDS構文化"
        self._入力印 = sha256(self.入力.encode("utf-8")).hexdigest()

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if not self.入力状態.issubset(状態.成立状態):
            return None
        if self.出力状態 in 状態.成立状態:
            return None
        return HDS作用機会(
            self.作用ID,
            f"{self._入力印}:{状態.状態署名}",
            self.入力状態,
            frozenset({self.出力状態}),
            self.解消対象,
            1,
            1.0,
            True,
            ("HDS_COMPILER_AS_COGNITIVE_INPUT",),
        )

    def _コンパイル(self) -> HDSIR:
        compile_fn = self.構文化器.コンパイル
        params = inspect.signature(compile_fn).parameters
        has_kwargs = any(item.kind is inspect.Parameter.VAR_KEYWORD for item in params.values())
        kwargs = {}
        if "前回結果" in params or has_kwargs:
            kwargs["前回結果"] = self.前回結果
        if "HDS履歴" in params or has_kwargs:
            kwargs["HDS履歴"] = self.HDS履歴
        if "文脈" in params or has_kwargs:
            kwargs["文脈"] = self.文脈
        return compile_fn(self.入力, **kwargs)

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        try:
            ir = self._コンパイル()
        except Exception as exc:
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({f"構文化失敗:{type(exc).__name__}"}),
                理由=("HDS_COMPILE_FAILED", type(exc).__name__),
            )

        if not isinstance(ir, HDSIR):
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({"構文化失敗:HDSIR型不正"}),
                理由=("HDS_COMPILE_RETURN_TYPE_INVALID",),
            )

        residuals = {
            f"HDS残差:{item.種別}:{item.理由}"
            for item in ir.残差
        }
        if self.実行閉包要求:
            residuals.update(f"HDS実行阻害:{item}" for item in ir.実行阻害理由)
        reason = ["HDS_IR_ATTACHED_TO_HDS_STATE"]
        if residuals:
            reason.append("HDS_IR_HAS_RESIDUALS")
        else:
            reason.append("HDS_IR_CLOSED_FOR_CURRENT_CONTRACT")
        return HDS作用結果(
            HDS作用状態.成立,
            追加状態=frozenset({self.出力状態}),
            解消残差=self.解消対象,
            追加残差=frozenset(residuals),
            成果=(("HDS_IR", ir),),
            理由=tuple(reason),
        )


__all__ = ["HDS構文化作用"]
