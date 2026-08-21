from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .hds_ir import HDSIR
from .k3_functional import Candidate, HDSJudge, JudgeDecision, K3相当能力核, SemanticFrame


_WORD = re.compile(r"[A-Za-z0-9_+\-\.]+|[ぁ-んァ-ヶー]+|[一-龥々]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
    "is", "are", "was", "were", "be", "which", "what", "who", "when", "where", "why", "how",
    "this", "that", "these", "those", "it", "its",
}


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token.casefold()
        for token in _WORD.findall(text)
        if len(token) > 1 and token.casefold() not in _STOP
    )


def _choices(ir: HDSIR) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for coord in ir.座標:
        if coord.座標ID.startswith("choice:"):
            label = coord.座標ID.split(":", 1)[1]
            out.append((label, str(coord.内容)))
    return tuple(sorted(out, key=lambda x: x[0]))


def _facts(core: K3相当能力核) -> tuple[object, ...]:
    # KnowledgeBaseと同一package内の接続Adapter。読み取り専用で保持Dataを列挙する。
    store = getattr(core.K, "_facts", {})
    return tuple(store.values())


def _fact_text(core: K3相当能力核, fact: object) -> str:
    predicate = str(getattr(fact, "predicate", ""))
    args = tuple(getattr(fact, "args", ()))
    labels = [core.R.label(str(arg)) for arg in args]
    return " ".join((predicate, *labels))


@dataclass(frozen=True, slots=True)
class HDSK3結果:
    状態: str
    回答ラベル: str | None
    判定: JudgeDecision
    候補: tuple[Candidate, ...]
    根拠事実数: int
    理由: tuple[str, ...]


class HDSIRネイティブAdapter:
    """HDS-IRをK3相当能力核へ直接接続する一般Adapter。

    ベンチ名・設問形式・正解情報には依存しない。候補集合をHDS座標から取得し、
    Kに存在する根拠事実との意味重なりだけで候補を形成する。根拠が無ければJが保留する。
    """

    def __init__(self, core: K3相当能力核 | None = None, judge: HDSJudge | None = None) -> None:
        self.core = core or K3相当能力核()
        self.judge = judge or self.core.J

    def 実行(self, ir: HDSIR) -> HDSK3結果:
        choices = _choices(ir)
        if not choices:
            decision = JudgeDecision("SUSPEND", None, ("HDS_NO_CHOICE_SET",))
            return HDSK3結果("SUSPEND", None, decision, (), 0, decision.reason_codes)

        question_tokens = _tokens(ir.原文)
        facts = _facts(self.core)
        scored: list[tuple[float, Candidate]] = []

        for label, option in choices:
            option_tokens = _tokens(option)
            proof_ids: list[str] = []
            evidence_score = 0.0

            # 選択肢が既知の単純assertionへ射影できる場合は直接照合する。
            parsed = self.core.R.parse(option)
            parsed_fact = getattr(parsed, "fact", None)
            if parsed_fact is not None:
                matches = self.core.K.find(parsed_fact.predicate, parsed_fact.args, parsed_fact.polarity)
                for fact in matches:
                    if fact.fact_id not in proof_ids:
                        proof_ids.append(fact.fact_id)
                        evidence_score += 8.0 * float(fact.confidence)

            # 一般候補では、問いと候補の双方に接続するK事実だけを根拠として採用する。
            for fact in facts:
                ft = _tokens(_fact_text(self.core, fact))
                option_overlap = len(option_tokens & ft)
                question_overlap = len(question_tokens & ft)
                if option_overlap == 0 or question_overlap == 0:
                    continue
                fid = str(getattr(fact, "fact_id", ""))
                if fid and fid not in proof_ids:
                    proof_ids.append(fid)
                confidence = float(getattr(fact, "confidence", 1.0))
                evidence_score += confidence * (2.0 * option_overlap + question_overlap)

            if proof_ids and evidence_score > 0:
                confidence = min(0.999, 0.50 + evidence_score / (20.0 + evidence_score))
                candidate = Candidate(
                    answer=label,
                    relation="HDS_choice_selection",
                    confidence=confidence,
                    expert="HDS_IR_native",
                    proof_fact_ids=tuple(proof_ids),
                    provenance=("HDS-IR", "K"),
                )
                scored.append((evidence_score, candidate))

        if not scored:
            decision = JudgeDecision("SUSPEND", None, ("NO_KNOWLEDGE_EVIDENCE", "NO_GUESS"))
            return HDSK3結果("SUSPEND", None, decision, (), 0, decision.reason_codes)

        scored.sort(key=lambda x: (-x[0], -x[1].confidence, x[1].answer))
        top_score = scored[0][0]
        top = [candidate for score, candidate in scored if abs(score - top_score) < 1e-12]
        candidates = tuple(candidate for _, candidate in scored)
        if len(top) != 1:
            decision = JudgeDecision("SUSPEND", None, ("AMBIGUOUS_EVIDENCE", "NO_GUESS"))
            proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
            return HDSK3結果("SUSPEND", None, decision, candidates, proof_count, decision.reason_codes)

        frame = SemanticFrame(
            kind="question",
            intent="knowledge_query",
            raw=ir.原文,
            predicate="HDS_choice_selection",
            args=(None,),
            tags=("HDS-IR", "choice"),
            language=getattr(ir, "入力言語", "en") or "en",
        )
        decision = self.judge.decide(frame, top)
        selected = decision.selected_candidate.answer if decision.selected_candidate else None
        proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
        return HDSK3結果(decision.status, selected, decision, candidates, proof_count, decision.reason_codes)


__all__ = ["HDSK3結果", "HDSIRネイティブAdapter"]
