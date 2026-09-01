from __future__ import annotations

from dataclasses import replace
from typing import Callable

from .hds_choice_runtime import HDS選択実行結果, HDS選択推論実行
from .hds_ir import HDSIR
from .hds能力経路_v3 import HDS能力経路V3候補提案実行
from .k3_functional import K3相当能力核
from .模型 import MINIDORA模型核
from .参照 import 参照記録


HDS候補worker = Callable[[HDSIR, tuple[参照記録, ...]], HDS選択実行結果]


def _基礎提案化(result: HDS選択実行結果) -> HDS選択実行結果:
    """既存workerのAPPROVEを採用権限なしのPROPOSEへ落とす。"""

    if result.状態 != "APPROVE" or result.回答ラベル is None or result.回答内容 is None:
        return result
    return replace(
        result,
        状態="PROPOSE",
        理由=tuple(dict.fromkeys(tuple(result.理由) + (
            "HDS_ADAPTIVE_BASE_SELECTED",
            "CANDIDATE_GENERATION_HAS_NO_COMMIT_AUTHORITY",
        ))),
    )


def _能力経路優先可能(result: HDS選択実行結果) -> bool:
    """raw候補横断更新ではなく、実観測変化または専門作用消費だけを根拠にする。"""

    if result.状態 != "PROPOSE" or result.回答ラベル is None or result.回答内容 is None:
        return False
    reasons = set(result.理由)
    return bool(
        result.専門作用起動数 > 0
        or "HDS_ACTION_DELTA_CONSUMED" in reasons
        or "C_LOCAL_VIEW_RECHECK_SELECTED" in reasons
        or "NEW_REFERENCE_STATE_CONSUMED" in reasons
    )


def HDS適応候補調停(
    能力提案: HDS選択実行結果,
    基礎提案: HDS選択実行結果,
) -> HDS選択実行結果:
    """観測状態の実変化に基づいて二つの候補workerを調停する。

    判断規則:
    - 能力経路が専門作用を実消費した、またはlocal/new-referenceという実観測変化を経て
      PROPOSEを形成した場合だけ、その能力提案を基礎経路より優先する。
    - `候補横断更新数 > 0` 単独は採用根拠にしない。同Dataの候補縮小で作れるためである。
    - 上記が成立しない場合は、基礎経路が閉じた場合だけ基礎提案を採用候補へ残す。
    - 双方に採用可能な提案が無ければSUSPENDする。

    この関数はgold、正解ラベル、ベンチケースIDを受け取らない。
    COMMIT権限も持たない。
    """

    if _能力経路優先可能(能力提案):
        return replace(
            能力提案,
            理由=tuple(dict.fromkeys(tuple(能力提案.理由) + (
                "HDS_ADAPTIVE_PRIMARY_SELECTED",
                "OBSERVATION_STATE_CHANGE_SUPPORTED",
            ))),
        )

    base = _基礎提案化(基礎提案)
    if base.状態 == "PROPOSE":
        return base

    reasons = tuple(dict.fromkeys(
        tuple(能力提案.理由)
        + tuple(基礎提案.理由)
        + (
            "HDS_ADAPTIVE_NO_COMMITTABLE_PROPOSAL",
            "PRIMARY_WITHOUT_OBSERVATION_CHANGE_NOT_COMMITTED",
            "PRIMARY_WITHOUT_SECOND_ORDER_SUPPORT_NOT_COMMITTED",
        )
    ))
    return replace(
        能力提案,
        状態="SUSPEND",
        回答ラベル=None,
        回答内容=None,
        理由=reasons,
    )


def HDS適応候補提案実行(
    question_ir: HDSIR,
    references: tuple[参照記録, ...],
    *,
    コンパイル,
    基礎能力核: K3相当能力核,
    模型核: MINIDORA模型核 | None = None,
) -> HDS選択実行結果:
    """同一HDS-IR・同一Dataで能力v3 workerと基礎workerを生成し、一般規則で調停する。"""

    primary = HDS能力経路V3候補提案実行(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        模型核=模型核,
    )
    base = HDS選択推論実行(
        question_ir,
        references,
        コンパイル=コンパイル,
        基礎能力核=基礎能力核,
        作業再作用=False,
        局所再照合=False,
    )
    return HDS適応候補調停(primary, base)


__all__ = [
    "HDS候補worker",
    "HDS適応候補調停",
    "HDS適応候補提案実行",
]
