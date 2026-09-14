from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


模型閉包版 = "MINIDORA-模型閉包-v0.1"


class 模型閉包状態(StrEnum):
    成立 = "成立"
    入力意味不足 = "入力意味不足"
    参照不足 = "参照不足"
    競合 = "競合"
    矛盾 = "矛盾"
    未確定 = "未確定"


@dataclass(frozen=True, slots=True)
class 模型残差:
    種別: str
    対象: str = ""
    詳細: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class 模型閉包:
    状態: 模型閉包状態
    回答候補ID: str | None
    参照得点: tuple[tuple[str, int], ...]
    残差: tuple[模型残差, ...] = ()
    版: str = 模型閉包版

    @property
    def 成立(self) -> bool:
        return self.状態 == 模型閉包状態.成立 and self.回答候補ID is not None


def _寄与群(result: Any):
    for row in tuple(getattr(result, "候補差", ())):
        cid = str(getattr(row, "候補ID", ""))
        for item in tuple(getattr(row, "寄与", ())):
            yield cid, item


def _入力境界未成立(result: Any) -> tuple[模型残差, ...]:
    out = []
    for cid, item in _寄与群(result):
        name = str(getattr(item, "関係名", ""))
        roots = tuple(str(x) for x in getattr(item, "根拠", ()))
        if name == "入力境界未成立" or "INCOMPLETE_INPUT_STATE" in roots:
            out.append(模型残差("入力意味不足", cid, roots or ("INCOMPLETE_INPUT_STATE",)))
    return tuple(out)


def _矛盾残差(result: Any) -> tuple[模型残差, ...]:
    out = []
    for cid, item in _寄与群(result):
        name = str(getattr(item, "関係名", ""))
        roots = tuple(str(x) for x in getattr(item, "根拠", ()))
        if any("矛盾" in x for x in (name, *roots)):
            out.append(模型残差("矛盾", cid, roots or (name,)))
    return tuple(out)


def 模型終端を判定(result: Any) -> 模型閉包:
    """MINIDORA能力Core自身の閉包状態を、外側のHDS/J語彙なしで確定する。

    ``APPROVE/SUSPEND`` は製品・監督境界の語彙なのでここでは使わない。
    Coreは、入力意味・参照寄与・候補差・矛盾だけから自身の状態を返す。
    """
    ref_scores_dict = dict(getattr(result, "参照候補辞書")())
    ref_scores = tuple(sorted((str(k), int(v)) for k, v in ref_scores_dict.items()))
    winner = getattr(result, "参照最有力候補ID", None)
    input_residuals = _入力境界未成立(result)
    contradiction_residuals = _矛盾残差(result)

    if input_residuals:
        return 模型閉包(
            模型閉包状態.入力意味不足,
            None,
            ref_scores,
            input_residuals + contradiction_residuals,
        )

    if winner is not None:
        return 模型閉包(模型閉包状態.成立, str(winner), ref_scores, contradiction_residuals)

    positive = [(cid, score) for cid, score in ref_scores if score > 0]
    if positive:
        maximum = max(score for _, score in positive)
        top = tuple(cid for cid, score in positive if score == maximum)
        if len(top) > 1:
            return 模型閉包(
                模型閉包状態.競合,
                None,
                ref_scores,
                contradiction_residuals + (模型残差("候補競合", "", top),),
            )
        return 模型閉包(
            模型閉包状態.未確定,
            None,
            ref_scores,
            contradiction_residuals + (模型残差("終端不整合", top[0], ("POSITIVE_REFERENCE_WITHOUT_WINNER",)),),
        )

    if contradiction_residuals:
        return 模型閉包(模型閉包状態.矛盾, None, ref_scores, contradiction_residuals)

    refs = tuple(getattr(getattr(result, "文脈", None), "参照状態", ()))
    detail = ("NO_USABLE_REFERENCE_CONTRIBUTION",) if refs else ("NO_REFERENCE_STATE",)
    return 模型閉包(
        模型閉包状態.参照不足,
        None,
        ref_scores,
        (模型残差("参照不足", "", detail),),
    )


__all__ = [
    "模型閉包版",
    "模型閉包状態",
    "模型残差",
    "模型閉包",
    "模型終端を判定",
]
