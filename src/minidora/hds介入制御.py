from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class 既存作用(StrEnum):
    参照取得 = "REFERENCE"
    作業再作用 = "EXISTING_WORKING_RECONCILE"
    局所再照合 = "EXISTING_LOCAL_REPARSE"
    能力模型照合 = "EXISTING_CAPABILITY_MODEL"
    計算実行 = "EXISTING_COMPUTE_EXECUTOR"


class 既存判定(StrEnum):
    実行中 = "RUNNING"
    承認 = "APPROVE"
    保留 = "SUSPEND"
    失敗 = "FAIL"


class 残差種別(StrEnum):
    観測不足 = "OBSERVATION_SHORTAGE"
    問題意味損失 = "QUESTION_SEMANTIC_LOSS"
    候補意味損失 = "CANDIDATE_SEMANTIC_LOSS"
    Data意味損失 = "DATA_SEMANTIC_LOSS"
    候補競合 = "CANDIDATE_CONFLICT"
    候補識別不足 = "CANDIDATE_DISCRIMINATION_INSUFFICIENT"
    状態差未消費 = "STATE_DELTA_UNCONSUMED"
    計算要求 = "COMPUTE_REQUIRED"
    未解残差 = "UNRESOLVED_RESIDUAL"


class HDS指令種別(StrEnum):
    不介入 = "NO_INTERVENTION"
    既存作用起動 = "RUN_EXISTING_ACTION"
    停止要求 = "REQUEST_STOP"


@dataclass(frozen=True, slots=True)
class HDS監督状態:
    """HDSへ渡す最小観測面。回答ラベル・候補本文・候補得点は含めない。"""

    既存判定: 既存判定
    出力存在: bool
    直接検証済み: bool
    根拠あり: bool
    参照状態署名: str
    候補状態署名: str
    残差: frozenset[残差種別]


@dataclass(frozen=True, slots=True)
class 既存作用機会:
    """既存MINIDORA側がHDSへ公開する作用capability metadata。"""

    作用: 既存作用
    解消対象: frozenset[残差種別]
    作用入力署名: str
    資源負荷: int = 1
    状態変更可能: bool = True
    根拠: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HDS指令:
    種別: HDS指令種別
    作用: 既存作用 | None = None
    対象残差: tuple[残差種別, ...] = ()
    理由: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HDS介入記録:
    作用: 既存作用
    作用入力署名: str
    対象残差: tuple[残差種別, ...]
    進展: bool | None = None


@dataclass(frozen=True, slots=True)
class 介入観測:
    状態: HDS監督状態
    作用機会: tuple[既存作用機会, ...]
    HDS介入記録: tuple[HDS介入記録, ...]
    HDS残予算: int


class HDS介入制御(Protocol):
    def 判定(self, 観測: 介入観測) -> HDS指令: ...


class 標準HDS介入制御:
    """既存MINIDORAを横から監督する有限Domain Projection。

    HDSは回答を生成・採用しない。現在残差と既存側が公開した作用機会だけを見て、
    次に起動する既存作用を選ぶ。同一作用・同一作用入力署名は反復しない。
    """

    def 判定(self, 観測: 介入観測) -> HDS指令:
        state = 観測.状態
        if state.既存判定 == 既存判定.承認 and state.出力存在 and not state.残差:
            return HDS指令(HDS指令種別.不介入, 理由=("EXISTING_MINIDORA_APPROVED",))
        if 観測.HDS残予算 <= 0:
            return HDS指令(HDS指令種別.停止要求, 理由=("HDS_INTERVENTION_BUDGET_EXHAUSTED",))
        if not state.残差:
            return HDS指令(HDS指令種別.停止要求, 理由=("NO_RECOVERABLE_RESIDUAL",))

        used = {(row.作用, row.作用入力署名) for row in 観測.HDS介入記録}
        candidates: list[tuple[int, float, int, str, 既存作用機会, tuple[残差種別, ...]]] = []
        for offer in 観測.作用機会:
            if not offer.状態変更可能 or (offer.作用, offer.作用入力署名) in used:
                continue
            targets = tuple(sorted(state.残差.intersection(offer.解消対象), key=lambda x: x.value))
            if not targets:
                continue
            coverage = len(targets)
            specificity = coverage / max(1, len(offer.解消対象))
            candidates.append((coverage, specificity, max(0, int(offer.資源負荷)), offer.作用.value, offer, targets))

        if not candidates:
            return HDS指令(HDS指令種別.停止要求, 理由=("NO_PRODUCTIVE_EXISTING_ACTION",))

        candidates.sort(key=lambda row: (-row[0], -row[1], row[2], row[3]))
        _, _, _, _, offer, targets = candidates[0]
        return HDS指令(
            HDS指令種別.既存作用起動,
            offer.作用,
            targets,
            tuple(dict.fromkeys((
                "RESIDUAL_TO_EXISTING_ACTION",
                *offer.根拠,
                *(f"TARGET:{item.value}" for item in targets),
            ))),
        )


__all__ = [
    "既存作用",
    "既存判定",
    "残差種別",
    "HDS指令種別",
    "HDS監督状態",
    "既存作用機会",
    "HDS指令",
    "HDS介入記録",
    "介入観測",
    "HDS介入制御",
    "標準HDS介入制御",
]
