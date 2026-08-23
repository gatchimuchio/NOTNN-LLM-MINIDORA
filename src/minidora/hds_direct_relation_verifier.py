from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .hds_data_k import HDS証拠事実
from .hds_ir import HDSIR, 値状態
from .k3_functional import Candidate, K3相当能力核
from .semantic_tokens import 意味語


_BLOCKING_PROVENANCE = {
    "value_state:未確定",
    "value_state:未観測",
    "value_state:矛盾",
    "value_state:留保",
}
_HYPOTHESIS_ORIGIN = "HDS候補代入仮説"


@dataclass(frozen=True, slots=True)
class HDS直接関係診断:
    候補: str
    得点: float
    独立出典数: int
    根拠事実ID: tuple[str, ...]


def _coverage(query: frozenset[str], evidence: frozenset[str]) -> float:
    if not query:
        return 0.0
    return len(query & evidence) / len(query)


def _relation_name(predicate: str) -> str | None:
    prefix = "hds_relation_"
    if not str(predicate).startswith(prefix):
        return None
    return str(predicate)[len(prefix):].replace("_", " ")


def _fact_blocked(fact: object) -> bool:
    provenance = {str(x) for x in getattr(fact, "provenance", ())}
    return bool(provenance & _BLOCKING_PROVENANCE) or any(
        item.startswith("residual_blocked:") for item in provenance
    )


def _source_id(fact: object) -> str:
    provenance = tuple(str(x) for x in getattr(fact, "provenance", ()))
    if "HDS-IR" in provenance:
        source = provenance[:provenance.index("HDS-IR")]
        if source:
            return "|".join(source)
    fid = str(getattr(fact, "fact_id", ""))
    return "fact:" + (fid or str(id(fact)))


def _hypothesis_edges(ir: HDSIR) -> tuple[tuple[str, frozenset[str], frozenset[str]], ...]:
    coords = ir.座標辞書()
    out: list[tuple[str, frozenset[str], frozenset[str]]] = []
    for relation in ir.関係:
        if str(relation.由来) != _HYPOTHESIS_ORIGIN:
            continue
        if relation.値状態 not in {値状態.推定, 値状態.確定}:
            continue
        starts = [coords[cid] for cid in relation.始点 if cid in coords]
        ends = [coords[cid] for cid in relation.終点 if cid in coords]
        for start in starts:
            for end in ends:
                start_terms = 意味語(start.内容)
                end_terms = 意味語(end.内容)
                if start_terms and end_terms:
                    out.append((str(relation.種別), start_terms, end_terms))
    return tuple(out)


def _fact_edges(fact: object) -> tuple[str, frozenset[str], frozenset[str]] | None:
    if _fact_blocked(fact):
        return None
    relation = _relation_name(str(getattr(fact, "predicate", "")))
    if relation is None:
        return None
    args = tuple(str(x) for x in getattr(fact, "args", ()))
    if "→" not in args:
        return None
    split = args.index("→")
    starts = tuple(x for x in args[:split] if x)
    ends = tuple(x for x in args[split + 1:] if x)
    if not starts or not ends:
        return None
    start_terms = 意味語(" ".join(starts))
    end_terms = 意味語(" ".join(ends))
    if not start_terms or not end_terms:
        return None
    return relation, start_terms, end_terms


def HDS直接関係検証(
    core: K3相当能力核,
    candidates: Mapping[str, HDSIR],
    *,
    最小端点被覆: float = 0.60,
    最小優位差: float = 0.15,
) -> tuple[Candidate | None, tuple[HDS直接関係診断, ...]]:
    """候補代入仮説とDataの有向HDS関係が直接一致する場合だけ候補証拠を返す。

    候補語の共起、検索hit数、文書全体の語集合は使わない。関係種別・始点・終点が同時に
    一致したFactだけをsource単位で集約する。同等の対抗候補が残る場合は候補を返さない。
    """
    facts = tuple(HDS証拠事実(core))
    fact_edges: list[tuple[object, str, frozenset[str], frozenset[str]]] = []
    for fact in facts:
        edge = _fact_edges(fact)
        if edge is not None:
            relation, starts, ends = edge
            fact_edges.append((fact, relation, starts, ends))

    diagnostics: list[HDS直接関係診断] = []
    for label, candidate_ir in sorted(candidates.items()):
        hypotheses = _hypothesis_edges(candidate_ir)
        per_source: dict[str, tuple[float, str]] = {}
        for relation, expected_start, expected_end in hypotheses:
            for fact, fact_relation, actual_start, actual_end in fact_edges:
                if relation != fact_relation:
                    continue
                start_cov = _coverage(expected_start, actual_start)
                end_cov = _coverage(expected_end, actual_end)
                if start_cov < 最小端点被覆 or end_cov < 最小端点被覆:
                    continue
                confidence = max(0.0, min(1.0, float(getattr(fact, "confidence", 1.0))))
                score = math.sqrt(start_cov * end_cov) * confidence
                source = _source_id(fact)
                fid = str(getattr(fact, "fact_id", ""))
                old = per_source.get(source)
                if old is None or score > old[0]:
                    per_source[source] = (score, fid)

        ranked_sources = sorted(per_source.values(), key=lambda row: (-row[0], row[1]))
        aggregate = 0.0
        for index, (score, _) in enumerate(ranked_sources[:3]):
            aggregate += score * (1.0 if index == 0 else 0.35 if index == 1 else 0.15)
        proof = tuple(fid for _, fid in ranked_sources[:3] if fid)
        diagnostics.append(HDS直接関係診断(str(label), aggregate, len(per_source), proof))

    ranked = sorted(diagnostics, key=lambda item: (-item.得点, -item.独立出典数, item.候補))
    if not ranked or ranked[0].得点 < 最小端点被覆 or not ranked[0].根拠事実ID:
        return None, tuple(diagnostics)
    second = ranked[1].得点 if len(ranked) > 1 else 0.0
    if ranked[0].得点 - second < 最小優位差:
        return None, tuple(diagnostics)

    top = ranked[0]
    confidence = min(0.995, 0.80 + min(0.19, top.得点 * 0.10))
    candidate = Candidate(
        answer=top.候補,
        relation="HDS_directed_relation_verification",
        confidence=confidence,
        expert="HDS_direct_relation_verifier",
        proof_fact_ids=top.根拠事実ID,
        provenance=(
            "HDS-IR",
            "K",
            "CANDIDATE_SUBSTITUTION_HYPOTHESIS",
            "DIRECTED_ENDPOINT_MATCH",
            "SOURCE_DEDUPLICATED",
            "NO_GUESS",
        ),
    )
    return candidate, tuple(diagnostics)


__all__ = ["HDS直接関係診断", "HDS直接関係検証"]
