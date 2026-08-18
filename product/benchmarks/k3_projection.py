"""K3公開構造を同一局所課題へ射影した非ニューラル参照版。

実Kimi K3のweight/APIではない。KDA相当の選択状態、AttnRes相当のstage選択、
Sparse MoE相当のexpert routing、effort予算だけを比較対象にする。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from minidora.runtime import (
    DecisionStatus,
    Fact,
    FactGraph,
    HDSJudge,
    Rule,
    RuleEngine,
    contains_hazard,
    normalize_text,
    parse_query,
)


@dataclass(frozen=True, slots=True)
class K3Result:
    status: DecisionStatus
    answer: str
    reason_codes: tuple[str, ...]
    metrics: dict[str, Any]


class K3Projection:
    """in-memory計算核。永続化・API・監査hash chainは含まない。"""

    BUDGET = {
        "low": {"rounds": 1, "experts": 2, "stages": 1},
        "medium": {"rounds": 3, "experts": 3, "stages": 2},
        "high": {"rounds": 6, "experts": 4, "stages": 4},
        "max": {"rounds": 12, "experts": 5, "stages": 8},
    }

    def __init__(self) -> None:
        self.state: dict[str, str] = {}
        self.facts = [
            Fact("fact_atlas_uses", "uses", ("project atlas", "aurora index"), True, "seed_atlas", 1.0),
            Fact("fact_aurora_store", "stores_at", ("aurora index", "/srv/aurora"), True, "seed_aurora", 1.0),
            Fact("fact_aurora_cap", "capability", ("aurora index", "全文検索"), True, "seed_aurora", 1.0),
            Fact("fact_parent_ab", "parent", ("alice", "bob"), True, "seed_family", 1.0),
            Fact("fact_parent_bc", "parent", ("bob", "carol"), True, "seed_family", 1.0),
            Fact("fact_pump_supply", "supplies", ("pump p1", "lubrication"), True, "seed_pump", 1.0),
            Fact("fact_lube_prevents", "prevents", ("lubrication", "turbine overheating"), True, "seed_pump", 1.0),
            Fact("fact_pump_offline", "offline", ("pump p1",), True, "seed_pump", 1.0),
            Fact("fact_minidora", "definition", ("minidora", "日本語優先・監査可能な非ニューラルネットワーク言語runtime"), True, "system_minidora", 1.0),
        ]
        self.rules = [
            Rule("rule_transitive", "transitive_use", (("uses", "?a", "?b"), ("uses", "?b", "?c")), ("uses", "?a", "?c"), 10),
            Rule("rule_storage", "delegated_storage", (("uses", "?system", "?index"), ("stores_at", "?index", "?location")), ("stores_at", "?system", "?location"), 20),
            Rule("rule_cap", "delegated_capability", (("uses", "?system", "?component"), ("capability", "?component", "?ability")), ("capability", "?system", "?ability"), 20),
            Rule("rule_grandparent", "grandparent", (("parent", "?x", "?y"), ("parent", "?y", "?z")), ("grandparent", "?x", "?z"), 30),
            Rule("rule_risk", "offline_risk", (("offline", "?machine"), ("supplies", "?machine", "?resource"), ("prevents", "?resource", "?risk")), ("risk", "?machine", "?risk"), 30),
        ]
        self.stage_bank: list[tuple[str, tuple[str, ...]]] = []

    def add_fact(self, fact: Fact) -> None:
        self.facts.append(fact)

    def run(self, question: str, effort: str = "medium") -> K3Result:
        frame = parse_query(question, self.state)
        budget = self.BUDGET[effort]
        state_actions = {}
        for key, value in (("intent", frame.intent), ("predicate", frame.predicate), ("language", frame.language)):
            action = "RETAIN" if self.state.get(key) == value else "DELTA_WRITE"
            self.state[key] = value
            state_actions[key] = action
        graph = FactGraph(self.facts)
        inference = RuleEngine().infer(graph, self.rules, rounds=budget["rounds"], timeout_ms=1000)
        self.stage_bank.extend([
            ("query", frame.terms),
            ("inference", (*frame.terms, "inference")),
        ])
        selected_stages = sorted(
            self.stage_bank,
            key=lambda item: -len(set(item[1]) & set(frame.terms)),
        )[: budget["stages"]]
        candidates = []
        if frame.predicate != "search":
            matched = graph.query(frame.predicate, frame.args)
            if matched:
                index = frame.args.index(None) if None in frame.args else len(frame.args) - 1
                answer = "; ".join(sorted({fact.args[index] for fact in matched}))
                evidence = tuple(
                    __import__("minidora.runtime", fromlist=["Evidence"]).Evidence(
                        "k3_" + fact.fact_id, fact.source_id, "fact", repr(fact.args), 1.0
                    )
                    for fact in matched
                )
                contradictions = tuple(
                    __import__("minidora.runtime", fromlist=["Evidence"]).Evidence(
                        "k3_contra_" + other.fact_id, other.source_id, "contradiction", repr(other.args), 1.0
                    )
                    for fact in matched for other in graph.contradictions(fact)
                )
                Candidate = __import__("minidora.runtime", fromlist=["Candidate"]).Candidate
                candidates.append(Candidate("k3_candidate", answer, frame.predicate, 0.95, "k3_sparse_route", evidence, contradictions))
        elif "minidora" in normalize_text(question):
            Evidence = __import__("minidora.runtime", fromlist=["Evidence"]).Evidence
            Candidate = __import__("minidora.runtime", fromlist=["Candidate"]).Candidate
            candidates.append(Candidate("k3_search", "日本語優先・監査可能な非ニューラルネットワーク言語runtime", "extractive", 0.8, "k3_retrieval", (Evidence("k3_system", "system_minidora", "document", "MINIDORA", 1.0),)))
        decision = HDSJudge().decide(candidates, input_hazard=contains_hazard(question))
        if decision.status == DecisionStatus.PASS and decision.selected:
            self.state["last_answer"] = decision.selected.answer
            if frame.entities:
                self.state["last_entity"] = frame.entities[0]
        return K3Result(
            decision.status,
            decision.selected.answer if decision.selected and decision.status == DecisionStatus.PASS else "",
            decision.reason_codes,
            {
                "round_budget": budget["rounds"],
                "routed_experts": budget["experts"],
                "selected_stages": len(selected_stages),
                "state_actions": state_actions,
                "derived_facts": len(inference["derived"]),
                "persistence": False,
                "audit_hash_chain": False,
            },
        )
