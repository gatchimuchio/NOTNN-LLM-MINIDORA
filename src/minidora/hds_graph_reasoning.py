from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Iterable, Mapping

from .k3_functional import K3相当能力核
from .semantic_tokens import 意味語


_GENERIC = {"意味原子→節", "談話順序", "節→述語"}
_BLOCKING_PROVENANCE = {
    "value_state:未確定",
    "value_state:未観測",
    "value_state:矛盾",
    "value_state:留保",
}
_GRAPH_REVISION_ATTR = "_hds_graph_revision"
_GRAPH_CACHE_ATTR = "_hds_graph_index_cache"


@dataclass(frozen=True, slots=True)
class HDS意味経路結果:
    得点: float
    事実ID: tuple[str, ...]
    深さ: int | None


@dataclass(frozen=True, slots=True)
class _辺:
    行先: str
    関係: str
    信頼度: float
    事実ID: str
    逆向き: bool = False


@dataclass(frozen=True, slots=True)
class HDS意味Graph索引:
    隣接: Mapping[str, tuple[_辺, ...]]
    node_terms: Mapping[str, frozenset[str]]
    関係Fact数: int
    revision: int


def _relation(predicate: str) -> str | None:
    prefix = "hds_relation_"
    if not predicate.startswith(prefix):
        return None
    return predicate[len(prefix):].replace("_", " ")


def _node_key(text: str) -> str:
    return " ".join(str(text).casefold().split())


def _coverage(query: frozenset[str], node_terms: frozenset[str]) -> float:
    if not query:
        return 0.0
    return len(query & node_terms) / len(query)


def _fact_blocked(fact: object) -> bool:
    provenance = {str(x) for x in getattr(fact, "provenance", ())}
    if provenance & _BLOCKING_PROVENANCE:
        return True
    return any(item.startswith("residual_blocked:") for item in provenance)


def HDS意味Graph索引構築(core: K3相当能力核) -> HDS意味Graph索引:
    revision = int(getattr(core.K, _GRAPH_REVISION_ATTR, 0))
    cached = getattr(core.K, _GRAPH_CACHE_ATTR, None)
    if cached is not None and cached.revision == revision:
        return cached

    store = getattr(core.K, "_facts", {})
    adjacency: dict[str, list[_辺]] = {}
    node_terms: dict[str, frozenset[str]] = {}
    relation_fact_count = 0

    for fact in store.values():
        if _fact_blocked(fact):
            continue
        predicate = str(getattr(fact, "predicate", ""))
        relation = _relation(predicate)
        if relation is None:
            continue
        args = [str(x) for x in getattr(fact, "args", ())]
        if "→" not in args:
            continue
        split = args.index("→")
        starts = [x for x in args[:split] if x]
        ends = [x for x in args[split + 1:] if x]
        if not starts or not ends:
            continue
        relation_fact_count += 1
        confidence = float(getattr(fact, "confidence", 1.0))
        fid = str(getattr(fact, "fact_id", ""))
        for start in starts:
            sk = _node_key(start)
            node_terms.setdefault(sk, 意味語(start))
            for end in ends:
                ek = _node_key(end)
                node_terms.setdefault(ek, 意味語(end))
                adjacency.setdefault(sk, []).append(_辺(ek, relation, confidence, fid, False))
                adjacency.setdefault(ek, []).append(_辺(sk, relation, confidence * 0.82, fid, True))

    index = HDS意味Graph索引(
        {node: tuple(edges) for node, edges in adjacency.items()},
        dict(node_terms),
        relation_fact_count,
        revision,
    )
    setattr(core.K, _GRAPH_CACHE_ATTR, index)
    return index


def HDS意味経路探索(
    core: K3相当能力核,
    問い語: frozenset[str],
    候補語: frozenset[str],
    優先関係: Iterable[str] = (),
    *,
    最大深さ: int = 4,
    索引: HDS意味Graph索引 | None = None,
) -> HDS意味経路結果:
    graph = 索引 or HDS意味Graph索引構築(core)
    adjacency = graph.隣接
    node_terms = graph.node_terms
    preferred = {str(x) for x in 優先関係}

    if not adjacency or not 問い語 or not 候補語:
        return HDS意味経路結果(0.0, (), None)

    starts = [(_coverage(問い語, terms), node) for node, terms in node_terms.items()]
    starts = [(score, node) for score, node in starts if score > 0]
    if not starts:
        return HDS意味経路結果(0.0, (), None)

    heap: list[tuple[float, int, str, tuple[str, ...], tuple[str, ...]]] = []
    best_state: dict[tuple[str, int], float] = {}
    for qcov, node in starts:
        score = 2.0 * qcov
        heapq.heappush(heap, (-score, 0, node, (), (node,)))
        best_state[(node, 0)] = score

    best_goal = HDS意味経路結果(0.0, (), None)
    while heap:
        neg_score, depth, node, proof, visited = heapq.heappop(heap)
        score = -neg_score
        candidate_cov = _coverage(候補語, node_terms.get(node, frozenset()))
        if candidate_cov > 0 and proof:
            goal = score + 5.0 * candidate_cov - 0.25 * depth
            if goal > best_goal.得点:
                best_goal = HDS意味経路結果(goal, proof, depth)
        if depth >= 最大深さ:
            continue

        for edge in adjacency.get(node, ()):
            if edge.行先 in visited:
                continue
            relation_bonus = 0.8 if edge.関係 in preferred else (0.25 if edge.関係 not in _GENERIC else 0.0)
            direction_penalty = 0.78 if edge.逆向き else 1.0
            edge_gain = edge.信頼度 * direction_penalty * (1.0 + relation_bonus)
            new_score = score * 0.88 + edge_gain
            state = (edge.行先, depth + 1)
            if new_score <= best_state.get(state, -1.0):
                continue
            best_state[state] = new_score
            new_proof = proof + ((edge.事実ID,) if edge.事実ID and edge.事実ID not in proof else ())
            heapq.heappush(heap, (-new_score, depth + 1, edge.行先, new_proof, visited + (edge.行先,)))

    return best_goal


__all__ = ["HDS意味経路結果", "HDS意味Graph索引", "HDS意味Graph索引構築", "HDS意味経路探索"]
