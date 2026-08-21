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
    """外部HDS Compilerと公開MINIDORA Runtimeの接続契約。"""

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果: Any = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR: ...


def HDS独立コンパイル(compiler: HDSコンパイラProtocol, 入力: str) -> HDSIR:
    """choice/Data等の独立文書を会話Mから切離してコンパイルする。

    現在のユーザー要求はTrinity文脈を使ってよい。一方、選択肢や検索で取得した外部Dataへ
    前turnの現在焦点・直前結果・未解残差を注入すると、外部証拠が会話状態に汚染される。
    この入口は空のHDS文脈だけを渡し、旧式Compilerには実装済み引数だけを供給する。
    """
    compile_fn = compiler.コンパイル
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


__all__ = ["HDS文脈", "HDSコンパイラProtocol", "HDS独立コンパイル"]
