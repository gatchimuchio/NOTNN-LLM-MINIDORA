from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Mapping

from .hds_graph_reasoning import HDS意味経路探索
from .hds_ir import HDSIR
from .k3_functional import Candidate, HDSJudge, JudgeDecision, K3相当能力核, SemanticFrame


_WORD = re.compile(r"[A-Za-z0-9_+\-\.]+|[ぁ-んァ-ヶー]+|[一-龥々]+")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "from", "with", "and", "or",
    "is", "are", "was", "were", "be", "which", "what", "who", "when", "where", "why", "how",
    "this", "that", "these", "those", "it", "its",
}
_SURFACE_ONLY_KINDS = {
    "source_text",
    "language.input",
    "language.normalized",
    "対象.原文保持",
    "文脈.言語",
}
_GENERIC_RELATIONS = {
    "意味原子→節",
    "談話順序",
    "候補→集合",
    "問い×候補→選択目的",
}


def _normalize_word(token: str) -> str:
    value = token.casefold().strip("._-")
    if re.fullmatch(r"[a-z]+", value):
        if len(value) > 5 and value.endswith("ies"):
            value = value[:-3] + "y"
        elif len(value) > 5 and value.endswith("ing"):
            value = value[:-3]
        elif len(value) > 4 and value.endswith("ed"):
            value = value[:-2]
        elif len(value) > 4 and value.endswith("s") and not value.endswith("ss"):
            value = value[:-1]
    return value


def _tokens(text: object) -> frozenset[str]:
    out: set[str] = set()
    for token in _WORD.findall(str(text)):
        value = _normalize_word(token)
        if len(value) <= 1 or value in _STOP:
            continue
        out.add(value)
    return frozenset(out)


def _choices(ir: HDSIR) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for coord in ir.座標:
        if coord.座標ID.startswith("choice:"):
            label = coord.座標ID.split(":", 1)[1]
            out.append((label, str(coord.内容)))
    return tuple(sorted(out, key=lambda x: x[0]))


def _facts(core: K3相当能力核) -> tuple[object, ...]:
    store = getattr(core.K, "_facts", {})
    return tuple(store.values())


def _fact_text(core: K3相当能力核, fact: object) -> str:
    predicate = str(getattr(fact, "predicate", ""))
    args = tuple(getattr(fact, "args", ()))
    labels = [core.R.label(str(arg)) for arg in args]
    return " ".join((predicate, *labels))


def _relation_name_from_predicate(predicate: str) -> str | None:
    prefix = "hds_relation_"
    if not predicate.startswith(prefix):
        return None
    return predicate[len(prefix):].replace("_", " ")


@dataclass(frozen=True, slots=True)
class HDS意味署名:
    語: frozenset[str]
    関係種別: frozenset[str]
    座標種別: frozenset[str]


@dataclass(frozen=True, slots=True)
class _証拠群:
    群ID: str
    語: frozenset[str]
    関係種別: frozenset[str]
    座標種別: frozenset[str]
    事実ID: tuple[str, ...]
    信頼度: float


def _意味署名(ir: HDSIR, *, fallback_text: str = "") -> HDS意味署名:
    terms: set[str] = set()
    kinds: set[str] = set()
    relations: set[str] = set()

    for coord in ir.座標:
        kind = str(coord.種別)
        if kind in _SURFACE_ONLY_KINDS or coord.座標ID.startswith("choice:"):
            continue
        if coord.原文範囲 is not None:
            terms.update(_tokens(coord.内容))
            kinds.add(kind)

    for relation in ir.関係:
        relation_type = str(relation.種別)
        if relation_type not in _GENERIC_RELATIONS:
            relations.add(relation_type)

    if not terms:
        terms.update(_tokens(fallback_text or ir.原文))
    return HDS意味署名(frozenset(terms), frozenset(relations), frozenset(kinds))


def _証拠群を作る(core: K3相当能力核) -> tuple[_証拠群, ...]:
    result: list[_証拠群] = []
    for fact in _facts(core):
        predicate = str(getattr(fact, "predicate", ""))
        args = tuple(str(x) for x in getattr(fact, "args", ()))
        fid = str(getattr(fact, "fact_id", ""))
        confidence = float(getattr(fact, "confidence", 1.0))
        terms: set[str] = set()
        relations: set[str] = set()
        kinds: set[str] = set()

        relation = _relation_name_from_predicate(predicate)
        if relation is not None:
            if relation not in _GENERIC_RELATIONS:
                relations.add(relation)
            terms.update(_tokens(" ".join(x for x in args if x != "→")))
        elif predicate == "hds_coordinate" and len(args) >= 2:
            kind = args[0]
            if kind not in _SURFACE_ONLY_KINDS:
                kinds.add(kind)
                terms.update(_tokens(args[1]))
        elif predicate == "hds_residual":
            continue
        else:
            terms.update(_tokens(_fact_text(core, fact)))
            relations.add(predicate)

        if terms or relations or kinds:
            result.append(
                _証拠群(
                    fid or str(id(fact)),
                    frozenset(terms),
                    frozenset(relations),
                    frozenset(kinds),
                    (fid,) if fid else (),
                    confidence,
                )
            )
    return tuple(result)


def _coverage(query: frozenset[str], evidence: frozenset[str]) -> float:
    if not query:
        return 0.0
    return len(query & evidence) / len(query)


def _relation_similarity(query: frozenset[str], evidence: frozenset[str]) -> float:
    if not query or not evidence:
        return 0.0
    return len(query & evidence) / math.sqrt(len(query) * len(evidence))


def _kind_similarity(query: frozenset[str], evidence: frozenset[str]) -> float:
    if not query or not evidence:
        return 0.0
    return len(query & evidence) / math.sqrt(len(query) * len(evidence))


def _group_score(question: HDS意味署名, candidate: HDS意味署名, evidence: _証拠群) -> float:
    candidate_coverage = _coverage(candidate.語, evidence.語)
    if candidate_coverage <= 0:
        return 0.0

    question_coverage = _coverage(question.語, evidence.語)
    if question.語 and question_coverage <= 0:
        return 0.0

    relation_match = max(
        _relation_similarity(question.関係種別, evidence.関係種別),
        _relation_similarity(candidate.関係種別, evidence.関係種別),
    )
    kind_match = max(
        _kind_similarity(question.座標種別, evidence.座標種別),
        _kind_similarity(candidate.座標種別, evidence.座標種別),
    )
    structural_multiplier = 1.0 + 1.5 * relation_match + 0.5 * kind_match
    return evidence.信頼度 * (4.0 * candidate_coverage + 2.0 * question_coverage) * structural_multiplier


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

    問い・候補・DataのHDS意味署名を比較し、単一Fact一致に加えてK内のHDS関係を
    最大4段辿る。ベンチ名・正解情報には依存せず、根拠が無い場合や一意差が無い場合は
    J/HDSが保留する。
    """

    def __init__(self, core: K3相当能力核 | None = None, judge: HDSJudge | None = None) -> None:
        self.core = core or K3相当能力核()
        self.judge = judge or self.core.J

    def 実行(self, ir: HDSIR, *, 候補IR: Mapping[str, HDSIR] | None = None) -> HDSK3結果:
        choices = _choices(ir)
        if not choices:
            decision = JudgeDecision("SUSPEND", None, ("HDS_NO_CHOICE_SET",))
            return HDSK3結果("SUSPEND", None, decision, (), 0, decision.reason_codes)

        question_signature = _意味署名(ir, fallback_text=ir.原文)
        evidence_groups = _証拠群を作る(self.core)
        scored: list[tuple[float, Candidate]] = []

        for label, option in choices:
            candidate_ir = (候補IR or {}).get(label)
            candidate_signature = (
                _意味署名(candidate_ir, fallback_text=option)
                if candidate_ir is not None
                else HDS意味署名(_tokens(option), frozenset(), frozenset())
            )
            proof_ids: list[str] = []
            evidence_scores: list[tuple[float, _証拠群]] = []

            parsed = self.core.R.parse(option)
            parsed_fact = getattr(parsed, "fact", None)
            direct_score = 0.0
            if parsed_fact is not None:
                matches = self.core.K.find(parsed_fact.predicate, parsed_fact.args, parsed_fact.polarity)
                for fact in matches:
                    fid = str(getattr(fact, "fact_id", ""))
                    if fid and fid not in proof_ids:
                        proof_ids.append(fid)
                    direct_score += 8.0 * float(fact.confidence)

            for evidence in evidence_groups:
                score = _group_score(question_signature, candidate_signature, evidence)
                if score > 0:
                    evidence_scores.append((score, evidence))

            evidence_scores.sort(key=lambda item: (-item[0], item[1].群ID))
            aggregate = direct_score
            for weight, (score, evidence) in zip((1.0, 0.35, 0.15), evidence_scores[:3]):
                aggregate += weight * score
                for fid in evidence.事実ID:
                    if fid not in proof_ids:
                        proof_ids.append(fid)

            path = HDS意味経路探索(
                self.core,
                question_signature.語,
                candidate_signature.語,
                question_signature.関係種別 | candidate_signature.関係種別,
                最大深さ=4,
            )
            if path.得点 > 0:
                aggregate += 2.5 * path.得点
                for fid in path.事実ID:
                    if fid not in proof_ids:
                        proof_ids.append(fid)

            if proof_ids and aggregate > 0:
                confidence = min(0.999, 0.50 + aggregate / (20.0 + aggregate))
                scored.append(
                    (
                        aggregate,
                        Candidate(
                            answer=label,
                            relation="HDS_choice_selection",
                            confidence=confidence,
                            expert="HDS_IR_structural_graph",
                            proof_fact_ids=tuple(proof_ids),
                            provenance=("HDS-IR", "K", "STRUCTURAL_GRAPH_MATCH"),
                        ),
                    )
                )

        if not scored:
            decision = JudgeDecision("SUSPEND", None, ("NO_KNOWLEDGE_EVIDENCE", "NO_GUESS"))
            return HDSK3結果("SUSPEND", None, decision, (), 0, decision.reason_codes)

        scored.sort(key=lambda item: (-item[0], -item[1].confidence, item[1].answer))
        candidates = tuple(candidate for _, candidate in scored)
        top_score, top_candidate = scored[0]
        if len(scored) > 1:
            second_score = scored[1][0]
            margin = top_score - second_score
            if margin <= max(0.12, top_score * 0.02):
                decision = JudgeDecision("SUSPEND", None, ("AMBIGUOUS_EVIDENCE", "NO_GUESS"))
                proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
                return HDSK3結果("SUSPEND", None, decision, candidates, proof_count, decision.reason_codes)

        frame = SemanticFrame(
            kind="question",
            intent="knowledge_query",
            raw=ir.原文,
            predicate="HDS_choice_selection",
            args=(None,),
            tags=("HDS-IR", "choice", "structural_graph"),
            language=getattr(ir, "入力言語", "en") or "en",
        )
        decision = self.judge.decide(frame, (top_candidate,))
        selected = decision.selected_candidate.answer if decision.selected_candidate else None
        proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
        return HDSK3結果(decision.status, selected, decision, candidates, proof_count, decision.reason_codes)


__all__ = ["HDS意味署名", "HDSK3結果", "HDSIRネイティブAdapter"]
