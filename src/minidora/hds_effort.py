from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .hds_ir import HDSIR
from .k3_functional import DistilledEffortPolicyController, EffortPolicy, SemanticFrame
from .semantic_tokens import 意味語


@dataclass(frozen=True, slots=True)
class HDS探索方針:
    水準: str
    K3方針: EffortPolicy
    証拠上限: int
    graph深さ上限: int
    証拠重み: tuple[float, ...]


def _構造量(ir: HDSIR, 候補IR: Mapping[str, HDSIR] | None) -> tuple[int, int, int, int]:
    coords = sum(1 for c in ir.座標 if not c.座標ID.startswith("choice:"))
    relations = len(ir.関係)
    residuals = len(ir.残差)
    terms = len(意味語(ir.正規化文 or ir.原文))
    if 候補IR:
        coords += sum(len(cir.座標) for cir in 候補IR.values())
        relations += sum(len(cir.関係) for cir in 候補IR.values())
        residuals += sum(len(cir.残差) for cir in 候補IR.values())
        terms += sum(len(意味語(cir.正規化文 or cir.原文)) for cir in 候補IR.values())
    return coords, relations, residuals, terms


def HDS努力水準(ir: HDSIR, 候補IR: Mapping[str, HDSIR] | None = None) -> str:
    """HDS構造量から、K3型の計算資源水準を決定論的に選ぶ。

    ベンチ名や正解情報は使わない。関係数・意味座標・残差・意味語数だけを見る。
    """
    coords, relations, residuals, terms = _構造量(ir, 候補IR)
    choices = sum(1 for c in ir.座標 if c.座標ID.startswith("choice:"))
    complexity = (
        2 * relations
        + residuals
        + max(0, coords - 3) // 2
        + max(0, terms - 6) // 4
        + max(0, choices - 2)
    )
    if complexity >= 12 or relations >= 4 or residuals >= 2:
        return "max"
    if complexity >= 5 or relations >= 1 or choices >= 4:
        return "high"
    return "low"


def HDS探索方針選択(
    ir: HDSIR,
    候補IR: Mapping[str, HDSIR] | None = None,
    *,
    指定水準: str | None = None,
    controller: DistilledEffortPolicyController | None = None,
) -> HDS探索方針:
    level = 指定水準 or HDS努力水準(ir, 候補IR)
    frame = SemanticFrame(
        kind="question",
        intent="knowledge_query",
        raw=ir.原文,
        predicate="HDS_choice_selection",
        args=(None,),
        tags=("HDS-IR", "choice", "structural_graph"),
        language=ir.入力言語 or "en",
    )
    base = (controller or DistilledEffortPolicyController()).select(frame, level)

    # graphはまず4段で探索し、未到達時のみここで定めた上限へ拡張する。
    # K3側のlow/high/maxを、候補証拠幅と追加探索深さの両方へ反映する。
    if base.name == "max":
        return HDS探索方針(base.name, base, 8, 10, (1.0, 0.55, 0.35, 0.24, 0.16, 0.11, 0.08, 0.05))
    if base.name == "high":
        return HDS探索方針(base.name, base, 5, 8, (1.0, 0.45, 0.25, 0.14, 0.08))
    return HDS探索方針(base.name, base, 3, 6, (1.0, 0.35, 0.15))


__all__ = ["HDS探索方針", "HDS努力水準", "HDS探索方針選択"]
