from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .hds_data_k import HDSIR知識Adapter
from .hds_replay import HDSIR復元
from .k3_functional import K3相当能力核
from .k3_hds_native import HDSIRネイティブAdapter


@dataclass(frozen=True, slots=True)
class ReplayCase結果:
    識別子: str
    状態: str
    予測: str | None
    gold: str | None
    正解: bool | None
    理由: tuple[str, ...]
    努力: str
    graph深さ上限: int
    証拠上限: int
    根拠事実数: int
    K追加事実数: int
    K証拠事実数: int
    候補診断: tuple[dict[str, Any], ...]


def HDSReplayCase評価(
    row: Mapping[str, Any],
    *,
    effort: str | None = None,
    基礎能力核: K3相当能力核 | None = None,
) -> ReplayCase結果:
    """1件の固定HDS replay rowをgold非入力で評価する。"""
    payload = dict(row)
    gold_value = payload.pop("gold", None)
    gold = str(gold_value) if gold_value is not None else None
    question = HDSIR復元(payload["question_ir"])
    choices = {
        str(label): HDSIR復元(data)
        for label, data in dict(payload.get("choices_ir", {})).items()
    }

    core = (基礎能力核 or K3相当能力核()).clone()
    ingest = HDSIR知識Adapter(core)
    added = 0
    evidence = 0
    for item in payload.get("data", ()):
        ir = HDSIR復元(item["ir"])
        provenance = tuple(str(x) for x in item.get("provenance", ()))
        source_confidence = float(item.get("source_confidence", 1.0))
        result = ingest.投入(
            ir,
            provenance=provenance,
            信頼係数=source_confidence,
        )
        added += result.追加事実数
        evidence += result.証拠事実数

    result = HDSIRネイティブAdapter(core).実行(question, 候補IR=choices, 努力=effort)
    diagnostics = tuple(
        {
            "候補": item.候補,
            "合計得点": item.合計得点,
            "証拠得点": item.証拠得点,
            "graph得点": item.graph得点,
            "graph補正": item.graph補正係数,
            "独立出典数": item.独立出典数,
            "採用証拠数": item.採用証拠数,
            "graph深さ": item.graph深さ,
            "根拠事実数": item.根拠事実数,
        }
        for item in result.候補診断
    )
    predicted = result.回答ラベル
    return ReplayCase結果(
        識別子=str(payload.get("id", "")),
        状態=result.状態,
        予測=predicted,
        gold=gold,
        正解=(predicted == gold) if gold is not None else None,
        理由=tuple(result.理由),
        努力=result.努力水準,
        graph深さ上限=result.探索深さ上限,
        証拠上限=result.証拠上限,
        根拠事実数=result.根拠事実数,
        K追加事実数=added,
        K証拠事実数=evidence,
        候補診断=diagnostics,
    )


def HDSReplay評価(
    rows: Iterable[Mapping[str, Any]],
    *,
    effort: str | None = None,
    基礎能力核: K3相当能力核 | None = None,
) -> dict[str, Any]:
    details: list[ReplayCase結果] = []
    reason_counts: Counter[str] = Counter()
    effort_counts: Counter[str] = Counter()
    correct = 0
    with_gold = 0
    answered = 0

    for row in rows:
        detail = HDSReplayCase評価(row, effort=effort, 基礎能力核=基礎能力核)
        details.append(detail)
        reason_counts.update(detail.理由)
        effort_counts[detail.努力] += 1
        if detail.状態 == "APPROVE" and detail.予測 is not None:
            answered += 1
        if detail.gold is not None:
            with_gold += 1
            if detail.正解:
                correct += 1

    total = len(details)
    return {
        "schema": "minidora.hds-choice-replay.result.v2",
        "total": total,
        "with_gold": with_gold,
        "correct": correct if with_gold else None,
        "accuracy_percent": (100.0 * correct / with_gold) if with_gold else None,
        "answered": answered,
        "suspended": total - answered,
        "answer_rate_percent": (100.0 * answered / total) if total else 0.0,
        "effort_override": effort,
        "effort_counts": dict(sorted(effort_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "details": [
            {
                "id": item.識別子,
                "status": item.状態,
                "predicted": item.予測,
                "gold": item.gold,
                "correct": item.正解,
                "reasons": list(item.理由),
                "effort": item.努力,
                "graph_depth_limit": item.graph深さ上限,
                "evidence_limit": item.証拠上限,
                "proof_fact_count": item.根拠事実数,
                "k_facts_added": item.K追加事実数,
                "evidence_facts": item.K証拠事実数,
                "candidate_diagnostics": list(item.候補診断),
            }
            for item in details
        ],
    }


__all__ = ["ReplayCase結果", "HDSReplayCase評価", "HDSReplay評価"]
