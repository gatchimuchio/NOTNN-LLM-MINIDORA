from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .hds_data_k import HDS証拠事実
from .hds_ir import HDSIR, 値状態
from .hds_relation_scope import (
    HDS実効関係名,
    HDS関係Scope,
    HDS関係Scope一致,
    HDS関係Scope抽出,
    K事実関係Scope抽出,
)
from .k3_functional import Candidate, K3相当能力核
from .semantic_tokens import 意味語


_BLOCKING_PROVENANCE = {
    "value_state:未確定",
    "value_state:未観測",
    "value_state:矛盾",
    "value_state:留保",
}
_HYPOTHESIS_ORIGIN = "HDS候補代入仮説"
_PUBLIC_COMPILER_ORIGIN = "公開HDS Compiler"
_LANGUAGE_BASE_ORIGIN = "共有言語基底P"
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
    scope: HDS関係Scope
    始点語: frozenset[str]
    終点語: frozenset[str]
    種別: str


@dataclass(frozen=True, slots=True)
class _事実辺:
    fact: object
    関係: str
    scope: HDS関係Scope
    始点語: frozenset[str]
    終点語: frozenset[str]


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
    coords = ir.座標辞書()
    out: list[_候補辺] = []
    global_negative = _否定候補(ir)
    for relation in ir.関係:
        origin = str(relation.由来)
        if origin == _HYPOTHESIS_ORIGIN:
            mode = "hypothesis"
            if relation.値状態 not in {値状態.推定, 値状態.確定}:
                continue
        elif origin in {_PUBLIC_COMPILER_ORIGIN, _LANGUAGE_BASE_ORIGIN}:
            if relation.値状態 != 値状態.確定:
                continue
            if str(relation.種別) in _GENERIC_RELATIONS:
                continue
            mode = "assertion"
        else:
            continue

        scope = HDS関係Scope抽出(relation)
        # 旧Projectionの全体否定がrelationへscopeされていない場合だけ安全側で直接証明を止める。
        if global_negative and not scope.非既定:
            continue
        effective_relation = HDS実効関係名(relation.種別, scope)

        starts = [coords[cid] for cid in relation.始点 if cid in coords]
        ends = [coords[cid] for cid in relation.終点 if cid in coords]
        for start in starts:
            for end in ends:
                start_terms = 意味語(start.内容)
                end_terms = 意味語(end.内容)
                if start_terms and end_terms:
                    edge = _候補辺(effective_relation, scope, start_terms, end_terms, mode)
                    if edge not in out:
                        out.append(edge)
    return tuple(out)


def _fact_edge(fact: object) -> _事実辺 | None:
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
    return _事実辺(fact, relation, K事実関係Scope抽出(fact), start_terms, end_terms)


def HDS直接関係検証(
    core: K3相当能力核,
    candidates: Mapping[str, HDSIR],
    *,
    最小端点被覆: float = 0.60,
    最小優位差: float = 0.15,
) -> tuple[Candidate | None, tuple[HDS直接関係診断, ...]]:
    """候補とDataの関係・方向・scopeが直接一致する場合だけ候補証拠を返す。

    scopeは極性だけでなく、様相・量化・比較・条件・蓋然性を含む。ここでは
    `現実なら可能` 等の追加推論を行わず、観測された意味条件が一致した時だけ直接一致とする。
    """
    fact_edges = tuple(edge for fact in HDS証拠事実(core) if (edge := _fact_edge(fact)) is not None)

    diagnostics: list[HDS直接関係診断] = []
    eligible: dict[str, bool] = {}
    for label, candidate_ir in sorted(candidates.items()):
        candidate_edges = _candidate_edges(candidate_ir)
        per_source: dict[str, tuple[float, str, str]] = {}
        for expected in candidate_edges:
            for actual in fact_edges:
                if expected.関係 != actual.関係:
                    continue
                if not HDS関係Scope一致(expected.scope, actual.scope):
                    continue
                start_cov = _coverage(expected.始点語, actual.始点語)
                end_cov = _coverage(expected.終点語, actual.終点語)
                if start_cov < 最小端点被覆 or end_cov < 最小端点被覆:
                    continue
                confidence = max(0.0, min(1.0, float(getattr(actual.fact, "confidence", 1.0))))
                score = math.sqrt(start_cov * end_cov) * confidence
                source = _source_id(actual.fact)
                fid = str(getattr(actual.fact, "fact_id", ""))
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
            HDS直接関係診断(str(label), aggregate, len(per_source), proof, hypothesis_sources, assertion_sources)
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
            "EXACT_RELATION_SCOPE_MATCH",
            "SOURCE_DEDUPLICATED",
            "NO_GUESS",
            "hypothesis_sources:" + str(top.仮説一致出典数),
            "assertion_sources:" + str(top.命題一致出典数),
        ),
    )
    return candidate, tuple(diagnostics)


__all__ = ["HDS直接関係診断", "HDS直接関係検証"]
