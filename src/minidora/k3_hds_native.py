from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .choice_intent import HDS選択意図判定
from .hds_candidate_reconcile import HDS候補証拠, HDS候補横断調停
from .hds_data_k import HDS証拠事実
from .hds_effort import HDS探索方針選択
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


def _source_group_id(fact: object) -> str:
    document = _document_group_id(fact)
    if document is not None:
        return document
    fid = str(getattr(fact, "fact_id", ""))
    return "fact:" + (fid or str(id(fact)))


def _fact_source_map(core: K3相当能力核) -> dict[str, str]:
    out: dict[str, str] = {}
    for fact in _facts(core):
        fid = str(getattr(fact, "fact_id", ""))
        if fid:
            out[fid] = _source_group_id(fact)
    return out


@dataclass(frozen=True, slots=True)
class HDS意味署名:
    語: frozenset[str]
    関係種別: frozenset[str]
    座標種別: frozenset[str]


@dataclass(frozen=True, slots=True)
class _証拠群:
    群ID: str
    出典ID: str
    語: frozenset[str]
    関係種別: frozenset[str]
    座標種別: frozenset[str]
    事実ID: tuple[str, ...]
    信頼度: float
    範囲: str = "fact"
    関係阻害: bool = False


@dataclass(frozen=True, slots=True)
class HDS候補診断:
    候補: str
    合計得点: float
    証拠得点: float
    graph得点: float
    graph補正係数: float
    独立出典数: int
    採用証拠数: int
    graph深さ: int | None
    根拠事実数: int
    識別語数: int = 0


def _意味署名(ir: HDSIR, *, fallback_text: str = "") -> HDS意味署名:
    """HDS-IRの確定・推定意味を署名へ落とす。"""
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


def _候補識別語(signatures: Mapping[str, HDS意味署名]) -> dict[str, frozenset[str]]:
    """候補集合の共通意味を除き、各候補固有の識別語を返す。"""
    labels = tuple(signatures)
    out: dict[str, frozenset[str]] = {}
    for label in labels:
        others: set[str] = set()
        for other in labels:
            if other != label:
                others.update(signatures[other].語)
        out[label] = frozenset(signatures[label].語 - others)
    return out


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
        source_id = _source_group_id(fact)
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
                    source_id,
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
        relation_blocked = group_id in document_blocked_relations and not relations
        confidences = document_confidences.get(group_id, [1.0])
        result.append(
            _証拠群(
                group_id,
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


def _group_score(
    question: HDS意味署名,
    candidate: HDS意味署名,
    evidence: _証拠群,
    *,
    識別語: frozenset[str] = frozenset(),
) -> float:
    if evidence.関係阻害:
        return 0.0

    full_coverage = _coverage(candidate.語, evidence.語)
    if full_coverage <= 0:
        return 0.0

    question_coverage = _coverage(question.語, evidence.語)
    if question.語 and question_coverage <= 0:
        return 0.0

    if 識別語:
        distinctive_coverage = _coverage(識別語, evidence.語)
        candidate_coverage = 0.35 * full_coverage + 0.65 * distinctive_coverage
    else:
        candidate_coverage = full_coverage

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
        scope_multiplier = 0.62
        if relation_match <= 0 and kind_match <= 0:
            scope_multiplier *= 0.65
    return (
        evidence.信頼度
        * (4.0 * candidate_coverage + 2.0 * question_coverage)
        * structural_multiplier
        * scope_multiplier
    )


def _例外消去候補(
    choices: tuple[tuple[str, str], ...],
    scored: list[tuple[float, Candidate]],
    diagnostics: tuple[HDS候補診断, ...],
) -> Candidate | None:
    """N択のN-1候補が独立根拠付きで確認された場合だけ、残り1候補を消去法で返す。"""
    labels = tuple(label for label, _ in choices)
    candidate_by_label = {candidate.answer: candidate for _, candidate in scored}
    diagnostic_by_label = {diagnostic.候補: diagnostic for diagnostic in diagnostics}

    supported = [
        label
        for label in labels
        if label in candidate_by_label
        and diagnostic_by_label.get(label) is not None
        and diagnostic_by_label[label].独立出典数 >= 1
        and diagnostic_by_label[label].根拠事実数 >= 1
    ]
    unsupported = [label for label in labels if label not in supported]
    if len(unsupported) != 1 or len(supported) != len(labels) - 1:
        return None

    proof_ids: list[str] = []
    confidences: list[float] = []
    for label in supported:
        candidate = candidate_by_label[label]
        confidences.append(candidate.confidence)
        for fid in candidate.proof_fact_ids:
            if fid and fid not in proof_ids:
                proof_ids.append(fid)
    if not proof_ids or not confidences:
        return None

    return Candidate(
        answer=unsupported[0],
        relation="HDS_choice_exception_elimination",
        confidence=min(confidences),
        expert="HDS_exception_elimination",
        proof_fact_ids=tuple(proof_ids),
        provenance=(
            "HDS-IR",
            "K",
            "EXCEPTION_INTENT",
            "N_MINUS_ONE_ELIMINATION",
            "NO_GUESS",
        ),
    )


@dataclass(frozen=True, slots=True)
class HDSK3結果:
    状態: str
    回答ラベル: str | None
    判定: JudgeDecision
    候補: tuple[Candidate, ...]
    根拠事実数: int
    理由: tuple[str, ...]
    努力水準: str = "low"
    探索深さ上限: int = 6
    証拠上限: int = 3
    候補診断: tuple[HDS候補診断, ...] = ()


class HDSIRネイティブAdapter:
    """HDS-IRをK3相当能力核へ直接接続する一般Adapter。"""

    def __init__(self, core: K3相当能力核 | None = None, judge: HDSJudge | None = None) -> None:
        self.core = core or K3相当能力核()
        self.judge = judge or self.core.J

    def 実行(
        self,
        ir: HDSIR,
        *,
        候補IR: Mapping[str, HDSIR] | None = None,
        努力: str | None = None,
    ) -> HDSK3結果:
        choices = _choices(ir)
        if not choices:
            decision = JudgeDecision("SUSPEND", None, ("HDS_NO_CHOICE_SET",))
            return HDSK3結果("SUSPEND", None, decision, (), 0, decision.reason_codes)

        探索方針 = HDS探索方針選択(
            ir,
            候補IR,
            指定水準=努力,
            controller=self.core.policy_controller,
        )
        question_signature = _意味署名(ir, fallback_text=ir.原文)
        evidence_groups = _証拠群を作る(self.core)
        facts = _facts(self.core)
        fact_sources = _fact_source_map(self.core)

        candidate_signatures: dict[str, HDS意味署名] = {}
        for label, option in choices:
            candidate_ir = (候補IR or {}).get(label)
            candidate_signatures[label] = (
                _意味署名(candidate_ir, fallback_text=option)
                if candidate_ir is not None
                else HDS意味署名(意味語(option), frozenset(), frozenset())
            )
        distinctive_terms = _候補識別語(candidate_signatures)

        raw_evidence: list[HDS候補証拠] = []
        for label, option in choices:
            candidate_signature = candidate_signatures[label]

            parsed = self.core.R.parse(option)
            parsed_fact = getattr(parsed, "fact", None)
            if parsed_fact is not None:
                for fact in facts:
                    if _fact_blocked(fact):
                        continue
                    if str(getattr(fact, "predicate", "")) != parsed_fact.predicate:
                        continue
                    if tuple(getattr(fact, "args", ())) != parsed_fact.args:
                        continue
                    if bool(getattr(fact, "polarity", True)) != parsed_fact.polarity:
                        continue
                    fid = str(getattr(fact, "fact_id", ""))
                    raw_evidence.append(
                        HDS候補証拠(
                            label,
                            _source_group_id(fact),
                            8.0 * float(getattr(fact, "confidence", 1.0)),
                            (fid,) if fid else (),
                            "direct",
                        )
                    )

            for evidence in evidence_groups:
                score = _group_score(
                    question_signature,
                    candidate_signature,
                    evidence,
                    識別語=distinctive_terms.get(label, frozenset()),
                )
                if score <= 0:
                    continue
                raw_evidence.append(
                    HDS候補証拠(
                        label,
                        evidence.出典ID,
                        score,
                        evidence.事実ID,
                        evidence.範囲,
                    )
                )

        labels = tuple(label for label, _ in choices)
        reconciled = HDS候補横断調停(
            labels,
            raw_evidence,
            証拠重み=探索方針.証拠重み,
            証拠上限=探索方針.証拠上限,
        )

        scored: list[tuple[float, Candidate]] = []
        diagnostics: list[HDS候補診断] = []
        for label, option in choices:
            candidate_signature = candidate_signatures[label]
            distinctive = distinctive_terms.get(label, frozenset())
            evidence_result = reconciled[label]
            aggregate = evidence_result.合計得点
            evidence_score = aggregate
            proof_ids: list[str] = []
            selected_sources = {item.出典ID for item in evidence_result.採用証拠}
            for item in evidence_result.採用証拠:
                for fid in item.事実ID:
                    if fid and fid not in proof_ids:
                        proof_ids.append(fid)

            preferred_relations = question_signature.関係種別 | candidate_signature.関係種別
            graph_target = distinctive or candidate_signature.語
            path = HDS意味経路探索(
                self.core,
                question_signature.語,
                graph_target,
                preferred_relations,
                最大深さ=4,
            )
            if path.得点 <= 0 and 探索方針.graph深さ上限 > 4:
                path = HDS意味経路探索(
                    self.core,
                    question_signature.語,
                    graph_target,
                    preferred_relations,
                    最大深さ=探索方針.graph深さ上限,
                )

            graph_score = 0.0
            graph_factor = 0.0
            graph_sources = {
                fact_sources[fid]
                for fid in path.事実ID
                if fid in fact_sources
            }
            if path.得点 > 0:
                if graph_sources:
                    novel = graph_sources - selected_sources
                    novelty = len(novel) / len(graph_sources)
                    graph_factor = 0.45 + 0.55 * novelty
                else:
                    graph_factor = 0.65
                graph_score = 2.5 * path.得点 * graph_factor
                aggregate += graph_score
                for fid in path.事実ID:
                    if fid and fid not in proof_ids:
                        proof_ids.append(fid)

            independent_sources = selected_sources | graph_sources
            diagnostics.append(
                HDS候補診断(
                    候補=label,
                    合計得点=aggregate,
                    証拠得点=evidence_score,
                    graph得点=graph_score,
                    graph補正係数=graph_factor,
                    独立出典数=len(independent_sources),
                    採用証拠数=len(evidence_result.採用証拠),
                    graph深さ=path.深さ,
                    根拠事実数=len(proof_ids),
                    識別語数=len(distinctive),
                )
            )

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
                            provenance=(
                                "HDS-IR",
                                "K",
                                "STRUCTURAL_GRAPH_MATCH",
                                "SOURCE_AWARE_RECONCILE",
                                "CANDIDATE_DISTINCTIVE_WEIGHT",
                                "effort:" + 探索方針.水準,
                                "sources:" + str(len(independent_sources)),
                            ),
                        ),
                    )
                )

        diagnostic_tuple = tuple(sorted(diagnostics, key=lambda item: item.候補))
        scored.sort(key=lambda item: (-item[0], -item[1].confidence, item[1].answer))
        candidates = tuple(candidate for _, candidate in scored)

        intent = HDS選択意図判定(ir.原文)
        frame = SemanticFrame(
            kind="question",
            intent="knowledge_query",
            raw=ir.原文,
            predicate="HDS_choice_selection",
            args=(None,),
            tags=("HDS-IR", "choice", "structural_graph", "source_aware_reconcile", "candidate_distinctive", intent.種別),
            language=getattr(ir, "入力言語", "en") or "en",
        )

        if intent.種別 == "EXCEPTION":
            eliminated = _例外消去候補(choices, scored, diagnostic_tuple)
            if eliminated is None:
                decision = JudgeDecision("SUSPEND", None, ("EXCEPTION_NOT_RESOLVED", "NO_GUESS"))
                proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
                return HDSK3結果(
                    "SUSPEND", None, decision, candidates, proof_count, decision.reason_codes,
                    探索方針.水準, 探索方針.graph深さ上限, 探索方針.証拠上限, diagnostic_tuple,
                )
            decision = self.judge.decide(frame, (eliminated,))
            selected = decision.selected_candidate.answer if decision.selected_candidate else None
            all_candidates = (eliminated, *tuple(candidate for candidate in candidates if candidate.answer != eliminated.answer))
            proof_count = len(set(eliminated.proof_fact_ids))
            return HDSK3結果(
                decision.status, selected, decision, all_candidates, proof_count, decision.reason_codes,
                探索方針.水準, 探索方針.graph深さ上限, 探索方針.証拠上限, diagnostic_tuple,
            )

        if not scored:
            decision = JudgeDecision("SUSPEND", None, ("NO_KNOWLEDGE_EVIDENCE", "NO_GUESS"))
            return HDSK3結果(
                "SUSPEND", None, decision, (), 0, decision.reason_codes,
                探索方針.水準, 探索方針.graph深さ上限, 探索方針.証拠上限, diagnostic_tuple,
            )

        top_score, top_candidate = scored[0]
        if len(scored) > 1:
            second_score = scored[1][0]
            margin = top_score - second_score
            if margin <= max(0.12, top_score * 0.02):
                decision = JudgeDecision("SUSPEND", None, ("AMBIGUOUS_EVIDENCE", "NO_GUESS"))
                proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
                return HDSK3結果(
                    "SUSPEND", None, decision, candidates, proof_count, decision.reason_codes,
                    探索方針.水準, 探索方針.graph深さ上限, 探索方針.証拠上限, diagnostic_tuple,
                )

        decision = self.judge.decide(frame, (top_candidate,))
        selected = decision.selected_candidate.answer if decision.selected_candidate else None
        proof_count = len({fid for candidate in candidates for fid in candidate.proof_fact_ids})
        return HDSK3結果(
            decision.status, selected, decision, candidates, proof_count, decision.reason_codes,
            探索方針.水準, 探索方針.graph深さ上限, 探索方針.証拠上限, diagnostic_tuple,
        )


__all__ = ["HDS意味署名", "HDS候補診断", "HDSK3結果", "HDSIRネイティブAdapter"]
