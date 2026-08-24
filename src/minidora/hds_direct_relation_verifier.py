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
_ASSERTION_ORIGINS = frozenset({"公開HDS Compiler", "共有言語基底P"})
_GENERIC_RELATIONS = {
    "意味原子→節",
    "談話順序",
    "節→述語",
    "候補→集合",
    "問い×候補→選択目的",
    "共参照",
    "数量単位",
}


@dataclass(frozen=True, slots=True)
class HDS直接関係診断:
    候補: str
    得点: float
    独立出典数: int
    根拠事実ID: tuple[str, ...]
    仮説一致出典数: int = 0
    命題一致出典数: int = 0


@dataclass(frozen=True, slots=True)
class _候補辺:
    関係: str
    始点語: frozenset[str]
    終点語: frozenset[str]
    種別: str


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


def _否定候補(ir: HDSIR) -> bool:
    return any(str(coord.種別) == "状態.否定" for coord in ir.座標)


def _candidate_edges(ir: HDSIR) -> tuple[_候補辺, ...]:
    """K射影後の候補IRから直接検証可能な有向辺だけを読む。

    共有言語基底Pの関係はCompilerと同じ意味正本資産から生じるため、K射影でscope安全性を
    通過した後は公開Compiler関係と同じ assertion として扱う。Runtime/J専用由来はここへ
    許可しない。
    """
    coords = ir.座標辞書()
    out: list[_候補辺] = []
    negative = _否定候補(ir)
    for relation in ir.関係:
        origin = str(relation.由来)
        if origin == _HYPOTHESIS_ORIGIN:
            mode = "hypothesis"
            if relation.値状態 not in {値状態.推定, 値状態.確定}:
                continue
        elif origin in _ASSERTION_ORIGINS:
            # 否定候補を肯定命題として直接証明しない。K射影で未対応scope辺は既に除外済み。
            if negative or relation.値状態 != 値状態.確定:
                continue
            if str(relation.種別) in _GENERIC_RELATIONS:
                continue
            mode = "assertion"
        else:
            continue

        starts = [coords[cid] for cid in relation.始点 if cid in coords]
        ends = [coords[cid] for cid in relation.終点 if cid in coords]
        for start in starts:
            for end in ends:
                start_terms = 意味語(start.内容)
                end_terms = 意味語(end.内容)
                if start_terms and end_terms:
                    edge = _候補辺(str(relation.種別), start_terms, end_terms, mode)
                    if edge not in out:
                        out.append(edge)
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
    """候補の有向HDS関係とData関係が直接一致する場合だけ候補証拠を返す。

    二つの経路を扱う。
    - 問いの未知端点へ実体候補を代入した仮説関係: 1独立sourceから直接検証可能。
    - 候補自身が表す完全命題の関係: 検索自己確認を避けるため2独立source以上を要求。

    候補語の共起、検索hit数、文書全体の語集合は使わない。関係種別・始点・終点が同時に
    一致したFactだけをsource単位で集約し、同等の対抗候補が残る場合は候補を返さない。
    """
    facts = tuple(HDS証拠事実(core))
    fact_edges: list[tuple[object, str, frozenset[str], frozenset[str]]] = []
    for fact in facts:
        edge = _fact_edges(fact)
        if edge is not None:
            relation, starts, ends = edge
            fact_edges.append((fact, relation, starts, ends))

    diagnostics: list[HDS直接関係診断] = []
    eligible: dict[str, bool] = {}
    for label, candidate_ir in sorted(candidates.items()):
        candidate_edges = _candidate_edges(candidate_ir)
        per_source: dict[str, tuple[float, str, str]] = {}
        for expected in candidate_edges:
            for fact, fact_relation, actual_start, actual_end in fact_edges:
                if expected.関係 != fact_relation:
                    continue
                start_cov = _coverage(expected.始点語, actual_start)
                end_cov = _coverage(expected.終点語, actual_end)
                if start_cov < 最小端点被覆 or end_cov < 最小端点被覆:
                    continue
                confidence = max(0.0, min(1.0, float(getattr(fact, "confidence", 1.0))))
                score = math.sqrt(start_cov * end_cov) * confidence
                source = _source_id(fact)
                fid = str(getattr(fact, "fact_id", ""))
                old = per_source.get(source)
                if old is None or score > old[0] or (score == old[0] and expected.種別 == "hypothesis"):
                    per_source[source] = (score, fid, expected.種別)

        ranked_sources = sorted(per_source.values(), key=lambda row: (-row[0], row[1], row[2]))
        aggregate = 0.0
        for index, (score, _, _) in enumerate(ranked_sources[:3]):
            aggregate += score * (1.0 if index == 0 else 0.35 if index == 1 else 0.15)
        proof = tuple(fid for _, fid, _ in ranked_sources[:3] if fid)
        hypothesis_sources = sum(mode == "hypothesis" for _, _, mode in per_source.values())
        assertion_sources = sum(mode == "assertion" for _, _, mode in per_source.values())
        is_eligible = hypothesis_sources >= 1 or assertion_sources >= 2
        eligible[str(label)] = is_eligible
        diagnostics.append(
            HDS直接関係診断(
                str(label), aggregate, len(per_source), proof,
                hypothesis_sources, assertion_sources,
            )
        )

    ranked = sorted(diagnostics, key=lambda item: (-item.得点, -item.独立出典数, item.候補))
    if not ranked:
        return None, tuple(diagnostics)
    top = ranked[0]
    if not eligible.get(top.候補, False) or top.得点 < 最小端点被覆 or not top.根拠事実ID:
        return None, tuple(diagnostics)
    second = ranked[1].得点 if len(ranked) > 1 else 0.0
    if top.得点 - second < 最小優位差:
        return None, tuple(diagnostics)

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
            "DIRECTED_ENDPOINT_MATCH",
            "SOURCE_DEDUPLICATED",
            "NO_GUESS",
            "hypothesis_sources:" + str(top.仮説一致出典数),
            "assertion_sources:" + str(top.命題一致出典数),
        ),
    )
    return candidate, tuple(diagnostics)


__all__ = ["HDS直接関係診断", "HDS直接関係検証"]
