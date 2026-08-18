from __future__ import annotations

from typing import Sequence

from .型 import Candidate, Decision, RunStatus


class HDSJudgementProtocol:
    """公開版はHDS本体ではなく、採否・停止・権限の局所Projection。"""

    def decide(self, candidates: Sequence[Candidate]) -> Decision:
        if not candidates:
            return Decision(RunStatus.SUSPEND, None, ("候補なし", "未知残存"), 0.0)
        ranked = sorted(candidates, key=lambda row: (-row.confidence, row.candidate_id))
        selected = ranked[0]
        if selected.hazard_flags:
            return Decision(RunStatus.FAIL, selected, ("危険検出", "出力拒否"), selected.confidence)
        if selected.contradiction_ids:
            return Decision(RunStatus.SUSPEND, selected, ("未解消矛盾",), selected.confidence)
        if not selected.evidence_ids:
            return Decision(RunStatus.SUSPEND, selected, ("証拠なし",), selected.confidence)
        if not selected.verifier_results or not all(bool(row.get("passed")) for row in selected.verifier_results):
            return Decision(RunStatus.SUSPEND, selected, ("検証未完",), selected.confidence)
        competitors = [row for row in ranked[1:] if row.answer != selected.answer and abs(row.confidence - selected.confidence) <= 0.05]
        if competitors:
            return Decision(RunStatus.SUSPEND, selected, ("候補競合",), selected.confidence)
        return Decision(
            RunStatus.PASS,
            selected,
            ("証拠結合済", "決定的再実行合格", "矛盾なし", "出力許可"),
            selected.confidence,
        )


HDS採否規約 = HDSJudgementProtocol
