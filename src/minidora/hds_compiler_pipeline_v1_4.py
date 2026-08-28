from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .hds_compiler_records_v1_3 import HDS作用差分構造
from .hds_ir import HDSIR, HDS実行核
from .命令 import 手順
from .命令計算降下 import 命令計算降下
from .計算中間表現 import 計算中間表現
from .言語 import 言語計画


HDSコンパイラパイプライン版 = "v1.4"


class HDS意味専用計画器:
    """基礎意味フロントエンドから計算計画責任を外すための無作用計画器。"""

    def 計画(self, 問合せ: str) -> 言語計画:
        return 言語計画(手順("HDS意味専用", ()), {}, False, "意味")


@dataclass(frozen=True, slots=True)
class HDSコンパイル束:
    """意味IR・計算計画・作用差分構造を混ぜず並列保持するCompiler成果。"""

    意味IR: HDSIR
    計算計画: 言語計画
    作用差分構造: HDS作用差分構造 = HDS作用差分構造()
    版: str = HDSコンパイラパイプライン版

    def 互換IR(self) -> HDSIR:
        plan = self.計算計画
        return replace(
            self.意味IR,
            実行核=HDS実行核(
                plan.種別,
                (),
                "結果",
                境界=("HDS-IR", "日本語基底", "互換橋"),
                検証=("公開Compiler", "意味IRと計算Pを正本では分離"),
            ),
            初期状態=dict(plan.初期状態),
            参照必須=bool(plan.参照必須),
            種別=plan.種別,
            閉包状態="CLOSED_FOR_OPERATION",
            手順=plan.手順,
        )


@dataclass(frozen=True, slots=True)
class HDS計算コンパイル成果:
    意味IR: HDSIR
    計算IR: 計算中間表現
    初期状態: dict[str, Any]
    参照必須: bool
    種別: str
    作用差分構造: HDS作用差分構造 = HDS作用差分構造()
    版: str = HDSコンパイラパイプライン版


def HDS意味IR化(base: HDSIR, plan: 言語計画) -> HDSIR:
    return replace(
        base,
        実行核=HDS実行核(
            plan.種別,
            (),
            "結果",
            境界=("HDS意味", "日本語基底"),
            検証=("計算P非内包",),
        ),
        初期状態={},
        参照必須=bool(plan.参照必須),
        種別=plan.種別,
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        手順=None,
    )


class HDS計算降下バックエンド:
    """形成済み計算Pを計算中間表現へ降下する。自然言語は再解析しない。"""

    版 = HDSコンパイラパイプライン版

    def 降下(self, bundle: HDSコンパイル束) -> HDS計算コンパイル成果:
        plan = bundle.計算計画
        compute_ir = 命令計算降下(plan.手順)
        refs: list[str] = [bundle.意味IR.認知世界ID]
        refs.extend(item.座標ID for item in bundle.意味IR.座標[:16])
        compute_ir = replace(
            compute_ir,
            名称=plan.種別 or compute_ir.名称,
            由来=f"HDS意味IR:{bundle.意味IR.認知世界ID}",
            由来参照=tuple(dict.fromkeys(refs)),
            境界=("HDS意味IRと計算P分離", "作用差分構造は計算Pへ自動降下しない"),
            検証=("自然言語再解析なし", "計算実行境界v1"),
        )
        return HDS計算コンパイル成果(
            意味IR=bundle.意味IR,
            計算IR=compute_ir,
            初期状態=dict(plan.初期状態),
            参照必須=bool(plan.参照必須),
            種別=plan.種別,
            作用差分構造=bundle.作用差分構造,
        )


__all__ = [
    "HDSコンパイラパイプライン版",
    "HDS意味専用計画器",
    "HDSコンパイル束",
    "HDS計算コンパイル成果",
    "HDS意味IR化",
    "HDS計算降下バックエンド",
]
