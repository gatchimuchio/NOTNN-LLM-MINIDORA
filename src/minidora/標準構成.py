from __future__ import annotations

from .hds_compiler_v1 import 公開HDSコンパイラ
from .runtime import ミニドラ
from .汎用能力核 import 標準汎用能力核

標準構成版 = "MINIDORA-STANDARD-RUNTIME-v2"


def 標準ミニドラ() -> ミニドラ:
    """公開HDS Compilerと汎用能力Coreを含む現行正本Runtimeを一意に構成する。"""
    return ミニドラ(
        HDSコンパイラ_=公開HDSコンパイラ(),
        模型核_=標準汎用能力核(),
    )


__all__ = ["標準ミニドラ", "標準構成版"]
