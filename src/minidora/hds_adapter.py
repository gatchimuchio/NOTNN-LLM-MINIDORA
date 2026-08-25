from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Protocol

from .hds_ir import HDSIR


@dataclass(frozen=True, slots=True)
class HDS文脈:
    """Trinityの記憶主体Mから判断主体JがCompilerへ引用する現在文脈。"""

    記憶版: int = 0
    現在焦点: Any = None
    直前結果: Any = None
    直前IR: HDSIR | None = None
    未解残差: tuple[tuple[str, str], ...] = ()
    記憶引用: tuple[str, ...] = ()


class HDSコンパイラProtocol(Protocol):
    """外部HDS Compilerと公開MINIDORA RuntimeのLegacy互換接続契約。"""

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果: Any = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR: ...


def _独立呼出(compile_fn, 入力: str) -> HDSIR:
    params = inspect.signature(compile_fn).parameters
    has_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    kwargs: dict[str, Any] = {}
    if "前回結果" in params or has_kwargs:
        kwargs["前回結果"] = None
    if "HDS履歴" in params or has_kwargs:
        kwargs["HDS履歴"] = ()
    if "文脈" in params or has_kwargs:
        kwargs["文脈"] = HDS文脈()
    return compile_fn(入力, **kwargs)


def HDS独立コンパイル(compiler: HDSコンパイラProtocol, 入力: str) -> HDSIR:
    """choice/Data等の独立文書を会話Mから切離して意味コンパイルする。

    Pipeline v1.3対応Compilerでは ``意味コンパイル`` を優先し、計算Pを独立Dataへ
    混入させない。旧式Compilerだけ ``コンパイル`` へフォールバックする。
    """

    compile_fn = getattr(compiler, "意味コンパイル", None)
    if not callable(compile_fn):
        compile_fn = compiler.コンパイル
    return _独立呼出(compile_fn, 入力)


__all__ = ["HDS文脈", "HDSコンパイラProtocol", "HDS独立コンパイル"]
