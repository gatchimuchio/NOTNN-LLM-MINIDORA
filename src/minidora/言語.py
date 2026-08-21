from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hds_compiler import HDSコンパイラ
from .命令 import 手順


@dataclass(frozen=True, slots=True)
class 言語計画:
    """Legacy互換。内部正本はHDSIR。"""
    手順: 手順
    初期状態: dict[str, Any]
    参照必須: bool = False
    種別: str = "一般"


class 自然言語器:
    """Legacy互換境界。自然言語処理の実体はHDSコンパイラへ移譲する。"""

    def __init__(self, compiler: HDSコンパイラ | None = None) -> None:
        self.compiler = compiler or HDSコンパイラ()
        self.直近IR = None

    def 計画(self, 問合せ: str) -> 言語計画:
        ir = self.compiler.コンパイル(問合せ)
        self.直近IR = ir
        if ir.手順 is None:
            raise ValueError("HDS-IRを実行可能Pへ閉包できない")
        return 言語計画(ir.手順, dict(ir.初期状態), ir.参照必須, ir.種別)

    def 表面化(self, 値: Any, 状態: str, 理由: tuple[str, ...]) -> str:
        return self.compiler.表面化(値, 状態, 理由)
