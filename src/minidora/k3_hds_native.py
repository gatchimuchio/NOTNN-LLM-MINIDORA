from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .hds_data_k import HDS証拠事実
from .hds_graph_reasoning import HDS意味経路探索
from .hds_ir import HDSIR, 値状態
from .k3_functional import Candidate, HDSJudge, JudgeDecision, K3相当能力核, SemanticFrame
from .semantic_tokens import 意味語


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
_SIGNATURE_BLOCKING_STATES = {
    値状態.未確定,
    値状態.未観測,
    値状態.矛盾,
    値状態.留保,
}
_BLOCKING_PROVENANCE = {"value_state:" + state.value for state in _SIGNATURE_BLOCKING_STATES}


def _choices(ir: HDSIR) -> tuple[tuple[str, str], ...]:
    out: list[tuple[str, str]] = []
    for coord in ir.座標:
        if coord.座標ID.startswith("choice:"):
            label = coord.座標ID.split(":", 1)[1]
            out.append((label, str(coord.内容)))
    return tuple(sorted(out, key=lambda x: x[0]))


def _facts(core: K3相当能力核) -> tuple[object, ...]:
    """Kのcanonical Factに、潰さず保持したHDS独立証拠を重ねて返す。"""
    store = getattr(core.K, "_facts", {})
    evidence = HDS証拠事実(core)
    if not evidence:
        return tuple(store.values())

    evidence_ids = {str(getattr(fact, "fact_id", "")) for fact in evidence}
    canonical_non_hds = []
    for fact in store.values():
        fid = str(getattr(fact, "fact_id", ""))
        provenance = tuple(str(x) for x in getattr(fact, "provenance", ()))
        if fid in evidence_ids:
            continue
        if "HDS-IR" in provenance:
            continue
        canonical_non_hds.append(fact)
    return tuple(canonical_non_hds) + tuple(evidence)


def _fact_blocked(fact: object) -> bool:
    provenance = {str(x) for x in getattr(fact, "provenance", ())}
    return bool(provenance & _BLOCKING_PROVENANCE)


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


def _document_group_id(fact: object) -> str | None:
    provenance = tuple(str(x) for x in getattr(fact, "provenance", ()))
    if "HDS-IR" not in provenance:
        return None
    split = provenance.index("HDS-IR")
    source = provenance[:split]
    if not source:
        return None
    return "document:" + "|".join(source)


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
    範囲: str = "fact"
    関係阻害: bool = False


def _意味署名(ir: HDSIR, *, fallback_text: str = "") -> HDS意味署名:
    """HDS-IRの確定・推定意味を署名へ落とす。

    原文範囲の有無は意味成立条件ではない。Compilerが導出した座標も、未確定等で
    なければ問い・候補の意味署名へ含める。
    """
    terms: set[str] = set()
    kinds: set[str] = set()
    relations: set[str] = set()

    for coord in ir.座標:
        kind = str(coord.種別)
        if kind in _SURFACE_ONLY_KINDS or coord.座標ID.startswith("choice:"):
            continue
        if coord.値状態 in _SIGNATURE_BLOCKING_STATES:
            continue
        coord_terms = 意味語(coord.内容)
        if coord_terms:
            terms.update(coord_terms)
            kinds.add(kind)

    for relation in ir.関係:
        if relation.値状態 in _SIGNATURE_BLOCKING_STATES:
            continue
        relation_type = str(relation.種別)
        if relation_type not in _GENERIC_RELATIONS:
            relations.add(relation_type)

    if not terms:
        terms.update(意味語(fallback_text or ir.原文))
    return HDS意味署名(frozenset(terms), frozenset(relations), frozenset(kinds))


def _fact_signature(core: K3相当能力核, fact: object) -> tuple[set[str], set[str], set[str]]:
    if _fact_blocked(fact):
        return set(), set(), set()

    predicate = str(getattr(fact, "predicate", ""))
    args = tuple(str(x) for x in getattr(fact, "args", ()))
    terms: set[str] = set()
    relations: set[str] = set()
    kinds: set[str] = set()

    relation = _relation_name_from_predicate(predicate)
    if relation is not None:
        if relation not in _GENERIC_RELATIONS:
            relations.add(relation)
        terms.update(意味語(" ".join(x for x in args if x != "→")))
    elif predicate == "hds_coordinate" and len(args) >= 2:
        kind = args[0]
        if kind not in _SURFACE_ONLY_KINDS:
            kinds.add(kind)
            terms.update(意味語(args[1]))
    elif predicate != "hds_residual":
        terms.update(意味語(_fact_text(core, fact)))
        relations.add(predicate)
    return terms, relations, kinds


def _証拠群を作る(core: K3相当能力核) -> tuple[_証拠群, ...]:
    """Fact単位証拠に加えて、同一HDS文書内の分散意味を低重みで再統合する。"""
    result: list[_証拠群] = []
    document_terms: dict[str, set[str]] = {}
    document_relations: dict[str, set[str]] = {}
    document_kinds: dict[str, set[str]] = {}
    document_fact_ids: dict[str, list[str]] = {}
    document_confidences: dict[str, list[float]] = {}
    document_blocked_relations: set[str] = set()

    for fact in _facts(core):
        predicate = str(getattr(fact, "predicate", ""))
        if predicate == "hds_residual":
            continue

        group_id = _document_group_id(fact)
        if _fact_blocked(fact):
            if group_id is not None and _relation_name_from_predicate(predicate) is not None:
                document_blocked_relations.add(group_id)
            continue

        fid = str(getattr(fact, "fact_id", ""))
        confidence = float(getattr(fact, "confidence", 1.0))
        terms, relations, kinds = _fact_signature(core, fact)

        if terms or relations or kinds:
            result.append(
                _証拠群(
                    fid or str(id(fact)),
                    frozenset(terms),
                    frozenset(relations),
                    frozenset(kinds),
                    (fid,) if fid else (),
                    confidence,
                    "fact",
                )
            )

        if group_id is None or not (terms or relations or kinds):
            continue
        document_terms.setdefault(group_id, set()).update(terms)
        document_relations.setdefault(group_id, set()).update(relations)
        document_kinds.setdefault(group_id, set()).update(kinds)
        if fid:
            ids = document_fact_ids.setdefault(group_id, [])
            if fid not in ids:
                ids.append(fid)
        document_confidences.setdefault(group_id, []).append(confidence)

    for group_id in sorted(document_terms):
        ids = tuple(document_fact_ids.get(group_id, ()))
        if len(ids) < 2:
            continue
        relations = frozenset(document_relations.get(group_id, set()))
        # 明示された関係が未確定等で、確定関係が一つもない文書は、
        # 座標の共起だけで関係を確定させない。
        relation_blocked = group_id in document_blocked_relations and not relations
        confidences = document_confidences.get(group_id, [1.0])
        result.append(
            _証拠群(
                group_id,
                frozenset(document_terms[group_id]),
                relations,
                frozenset(document_kinds.get(group_id, set())),
                ids,
                sum(confidences) / len(confidences),
                "document",
                relation_blocked,
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
    if evidence.関係阻害:
        return 0.0

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
    scope_multiplier = 1.0
    if evidence.範囲 == "document":
        # 同一文書内共起はFact直結より弱い証拠として扱い、誤接続を抑える。
        scope_multiplier = 0.62
        if relation_match <= 0 and kind_match <= 0:
            scope_multiplier *= 0.65
    return (
        evidence.信頼度
        * (4.0 * candidate_coverage + 2.0 * question_coverage)
        * structural_multiplier
        * scope_multiplier
    )


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

    問い・候補・DataのHDS意味署名、独立source証拠、同一文書内の意味共起、K内の
    方向付きHDS関係を統合する。通常4段、未到達時のみ6段まで関係探索する。
    ベンチ名・正解情報には依存せず、根拠が無い場合や一意差が無い場合はJ/HDSが保留する。
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
                else HDS意味署名(意味語(option), frozenset(), frozenset())
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

            evidence_scores.sort(key=lambda item: (-item[0], item[1].範囲, item[1].群ID))
            aggregate = direct_score
            for weight, (score, evidence) in zip((1.0, 0.35, 0.15), evidence_scores[:3]):
                aggregate += weight * score
                for fid in evidence.事実ID:
                    if fid not in proof_ids:
                        proof_ids.append(fid)

            preferred_relations = question_signature.関係種別 | candidate_signature.関係種別
            path = HDS意味経路探索(
                self.core,
                question_signature.語,
                candidate_signature.語,
                preferred_relations,
                最大深さ=4,
            )
            if path.得点 <= 0:
                path = HDS意味経路探索(
                    self.core,
                    question_signature.語,
                    candidate_signature.語,
                    preferred_relations,
                    最大深さ=6,
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
