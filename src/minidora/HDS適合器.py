from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Protocol

from .HDS中間表現 import HDSIR


@dataclass(frozen=True, slots=True)
class HDS文脈:
    'Runtime局所作業状態またはTrinity Mから構文化器へ引用する現在文脈。'

    記憶版: int = 0
    現在焦点: Any = None
    直前結果: Any = None
    直前IR: HDSIR | None = None
    未解残差: tuple[tuple[str, str], ...] = ()
    記憶引用: tuple[str, ...] = ()
    直前入力: str | None = None
    直前採否: str | None = None


class HDSコンパイラProtocol(Protocol):
    '外部HDS 構文化器と公開MINIDORA RuntimeのLegacy互換接続契約。'

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


def HDS独立コンパイル(構文化器: HDSコンパイラProtocol, 入力: str) -> HDSIR:
    '選択肢/資料等の独立文書を会話Mから切離して意味コンパイルする。\n\n    処理系列 v1.3対応構文化器では ``意味コンパイル`` を優先し、計算Pを独立資料へ\n    混入させない。旧式構文化器だけ ``コンパイル`` へフォールバックする。\n    '

    compile_fn = getattr(構文化器, "意味コンパイル", None)
    if not callable(compile_fn):
        compile_fn = 構文化器.コンパイル
    return _独立呼出(compile_fn, 入力)


__all__ = ["HDS文脈", "HDSコンパイラProtocol", "HDS独立コンパイル"]
