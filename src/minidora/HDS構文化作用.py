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
    同一性はHDS全状態ではなく、構文化器が実際に消費する固定入力だけから作る。
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
        コンパイル関数 = getattr(構文化器, "コンパイル", None)
        if not callable(コンパイル関数):
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
        署名材料 = repr((
            self.入力,
            self.前回結果,
            self.HDS履歴,
            self.文脈,
            self.実行閉包要求,
            type(構文化器).__module__,
            type(構文化器).__qualname__,
        )).encode("utf-8")
        self._入力印 = sha256(署名材料).hexdigest()

    def 機会(self, 状態: HDS実行状態) -> HDS作用機会 | None:
        if not self.入力状態.issubset(状態.成立状態):
            return None
        if self.出力状態 in 状態.成立状態:
            return None
        return HDS作用機会(
            self.作用ID,
            self._入力印,
            self.入力状態,
            frozenset({self.出力状態}),
            self.解消対象,
            1,
            1.0,
            True,
            ("HDS_COMPILER_AS_COGNITIVE_INPUT",),
        )

    def _コンパイル(self) -> HDSIR:
        コンパイル関数 = self.構文化器.コンパイル
        引数 = inspect.signature(コンパイル関数).parameters
        可変引数 = any(項目.kind is inspect.Parameter.VAR_KEYWORD for 項目 in 引数.values())
        追加引数 = {}
        if "前回結果" in 引数 or 可変引数:
            追加引数["前回結果"] = self.前回結果
        if "HDS履歴" in 引数 or 可変引数:
            追加引数["HDS履歴"] = self.HDS履歴
        if "文脈" in 引数 or 可変引数:
            追加引数["文脈"] = self.文脈
        return コンパイル関数(self.入力, **追加引数)

    def 実行(self, 状態: HDS実行状態) -> HDS作用結果:
        try:
            中間表現 = self._コンパイル()
        except Exception as exc:
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({f"構文化失敗:{type(exc).__name__}"}),
                理由=("HDS_COMPILE_FAILED", type(exc).__name__),
            )

        if not isinstance(中間表現, HDSIR):
            return HDS作用結果(
                HDS作用状態.失敗,
                追加残差=frozenset({"構文化失敗:HDSIR型不正"}),
                理由=("HDS_COMPILE_RETURN_TYPE_INVALID",),
            )

        残差群 = {
            f"HDS残差:{項目.種別}:{項目.理由}"
            for 項目 in 中間表現.残差
        }
        if self.実行閉包要求:
            残差群.update(f"HDS実行阻害:{項目}" for 項目 in 中間表現.実行阻害理由)
        理由群 = ["HDS_IR_ATTACHED_TO_HDS_STATE"]
        if 残差群:
            理由群.append("HDS_IR_HAS_RESIDUALS")
        else:
            理由群.append("HDS_IR_CLOSED_FOR_CURRENT_CONTRACT")
        return HDS作用結果(
            HDS作用状態.成立,
            追加状態=frozenset({self.出力状態}),
            解消残差=self.解消対象,
            追加残差=frozenset(残差群),
            成果=(("HDS_IR", 中間表現),),
            理由=tuple(理由群),
        )


__all__ = ["HDS構文化作用"]
