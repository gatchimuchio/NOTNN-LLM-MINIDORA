from __future__ import annotations

from typing import Sequence

from .hds_adapter import HDS文脈
from .hds_compiler import 公開HDSコンパイラ as _基礎HDSコンパイラ
from .hds_compiler import 公開HDSコンパイラ方針
from .hds_compiler_frontend import 公開HDSフロントエンド射影, 公開HDS詳細成果
from .hds_compiler_records import HDSCompiler成果
from .hds_ir import HDSIR


class 公開HDSコンパイラ(_基礎HDSコンパイラ):
    """MINIDORA公開標準HDS Compiler Architecture v1。

    既存の決定論的意味Projectionを互換基礎層として利用し、その上へ座標固定・動態・暗黙知・
    論証・原理探索入力・監査要求・保持契約を開放Front-Endとして重ねる。

    Compilerは真偽、原理の最終採用、行動、最終採否を決めない。
    """

    Architecture版 = "v1"
    基底言語 = "ja"

    def コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSIR:
        base = super().コンパイル(
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return 公開HDSフロントエンド射影(base).IR

    def 詳細コンパイル(
        self,
        入力: str,
        *,
        前回結果: object = None,
        HDS履歴: tuple[HDSIR, ...] = (),
        文脈: HDS文脈 | None = None,
    ) -> HDSCompiler成果:
        base = _基礎HDSコンパイラ.コンパイル(
            self,
            入力,
            前回結果=前回結果,
            HDS履歴=HDS履歴,
            文脈=文脈,
        )
        return 公開HDSフロントエンド射影(base)

    def 詳細問題IR(self, question: str, choices: Sequence[str]) -> HDSCompiler成果:
        return 公開HDS詳細成果(self.問題IR(question, choices))


__all__ = ["公開HDSコンパイラ方針", "公開HDSコンパイラ", "HDSCompiler成果"]
