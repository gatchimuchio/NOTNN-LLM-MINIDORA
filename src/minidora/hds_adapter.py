from __future__ import annotations

from typing import Any, Protocol

from .hds_ir import HDSIR


class HDSコンパイラProtocol(Protocol):
    """外部HDS Compilerと公開MINIDORA Runtimeの接続契約。"""

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果: Any = None,
        HDS履歴: tuple[HDSIR, ...] = (),
    ) -> HDSIR: ...


__all__ = ["HDSコンパイラProtocol"]
