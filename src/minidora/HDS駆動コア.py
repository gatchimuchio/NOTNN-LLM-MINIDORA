from __future__ import annotations

from typing import Mapping, Sequence

from .HDS実行主体 import HDS実行主体, HDS実行状態, HDS作用器, HDS実行結果
from .HDS構文化作用 import HDS構文化作用


HDS駆動コア版 = "MINIDORA-HDS-FIRST-v1"


class HDS駆動コア:
    """MINIDORA内部のHDS-first公開実行入口。

    外向きLLM成立用の厳密言語模型核を置換しない。ここではHDSが目的・状態・残差を所有し、
    MINIDORAの構文化器・参照・計算・模型・能力モジュール等を作用器として起動する。
    """

    def __init__(
        self,
        *,
        HDSコンパイラ=None,
        最大作用回数: int = 32,
    ) -> None:
        self.HDSコンパイラ = HDSコンパイラ
        self.最大作用回数 = int(最大作用回数)

    def 実行(
        self,
        問合せ: str,
        *,
        目的: Sequence[str] = (),
        要求状態: Sequence[str] = (),
        追加作用: Sequence[HDS作用器] = (),
        初期成立状態: Sequence[str] = (),
        初期残差: Sequence[str] | None = None,
        初期成果: Mapping[str, object] | None = None,
        主体状態: Mapping[str, object] | None = None,
        前回結果: object = None,
        HDS履歴=(),
        文脈=None,
    ) -> HDS実行結果:
        actions: list[HDS作用器] = []
        residuals = set(str(x) for x in (初期残差 or ()))
        if self.HDSコンパイラ is not None:
            residuals.add("入力未構文化")
            actions.append(HDS構文化作用(
                self.HDSコンパイラ,
                str(問合せ),
                前回結果=前回結果,
                HDS履歴=tuple(HDS履歴),
                文脈=文脈,
            ))
        actions.extend(tuple(追加作用))

        initial = HDS実行状態(
            tuple(str(x) for x in 目的),
            frozenset(str(x) for x in 要求状態),
            frozenset(str(x) for x in 初期成立状態),
            frozenset(residuals),
            tuple(sorted(dict(初期成果 or {}).items(), key=lambda row: row[0])),
            tuple(sorted(dict(主体状態 or {}).items(), key=lambda row: row[0])),
            0,
        )
        return HDS実行主体(
            tuple(actions),
            最大作用回数=self.最大作用回数,
        ).実行(initial)


__all__ = ["HDS駆動コア版", "HDS駆動コア"]
