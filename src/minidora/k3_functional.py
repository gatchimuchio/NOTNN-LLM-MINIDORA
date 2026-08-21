from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence
import copy
import json
import re

from .k3_generation import GenerationPlan, NonNeuralGenerator, build_generator


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"\s+", "_", text.strip().strip(".?!。？！")).lower()


@dataclass(frozen=True)
class Fact:
    predicate: str
    args: tuple[str, ...]
    polarity: bool = True
    confidence: float = 1.0
    provenance: tuple[str, ...] = ()
    depth: int = 0
    fact_id: str = ""

    def __post_init__(self) -> None:
        if not self.fact_id:
            object.__setattr__(self, "fact_id", "F-" + _digest((self.predicate, self.args, self.polarity, self.provenance))[:12])

    def key(self) -> tuple[str, tuple[str, ...], bool]:
        return self.predicate, self.args, self.polarity


@dataclass(frozen=True)
class SemanticFrame:
    kind: str
    intent: str
    raw: str
    predicate: str | None = None
    args: tuple[str | None, ...] = ()
    fact: Fact | None = None
    memory_key: str | None = None
    memory_value: str | None = None
    tags: tuple[str, ...] = ()
    language: str = "en"


class SymbolicRepresentationEngine:
    def __init__(self) -> None:
        self.labels: dict[str, str] = {}

    def _entity(self, text: str) -> str:
        key = _slug(text)
        self.labels.setdefault(key, text.strip().strip(".?!。？！"))
        return key

    def label(self, key: str) -> str:
        return self.labels.get(key, key.replace("_", " "))

    def parse(self, text: str) -> SemanticFrame:
        raw = text.strip()
        low = raw.lower().strip()
        m = re.match(r"^remember(?: that)? my (?P<key>.+?) is (?P<value>.+?)[.!?]?$", low)
        if m:
            key, value = self._entity(m.group("key")), self._entity(m.group("value"))
            return SemanticFrame("memory_write", "memory_write", raw, memory_key=key, memory_value=value, tags=("memory", key))
        m = re.match(r"^what is my (?P<key>.+?)[?]?$", low)
        if m:
            key = self._entity(m.group("key"))
            return SemanticFrame("question", "memory_recall", raw, "memory_value", (key, None), memory_key=key, tags=("memory", key))

        for pattern, predicate, intent, builder in (
            (r"^what capability does (?P<x>.+?) have[?]?$", "capability", "knowledge_query", lambda x: (self._entity(x), None)),
            (r"^who is the grandparent of (?P<x>.+?)[?]?$", "grandparent", "knowledge_query", lambda x: (None, self._entity(x))),
            (r"^what risk follows if (?P<x>.+?) is offline[?]?$", "risk", "risk_reasoning", lambda x: (None,)),
            (r"^what does (?P<x>.+?) use[?]?$", "uses", "knowledge_query", lambda x: (self._entity(x), None)),
            (r"^what color is the leftmost object[?]?$", "leftmost_color", "grid_relation", lambda x: (None,)),
        ):
            m = re.match(pattern, low, flags=re.I)
            if m:
                args = builder(m.groupdict().get("x", ""))
                return SemanticFrame("question", intent, raw, predicate, args, tags=tuple(x for x in (predicate, *args) if x))

        ja_q = re.match(r"^(?P<x>.+?)の能力は何[？?]?$", raw)
        if ja_q:
            x = self._entity(ja_q.group("x"))
            return SemanticFrame("question", "knowledge_query", raw, "capability", (x, None), tags=("capability", x), language="ja")

        neg = re.match(r"^(?P<s>.+?) does not use (?P<o>.+?)[.!?]?$", low)
        if neg:
            args = (self._entity(neg.group("s")), self._entity(neg.group("o")))
            fact = Fact("uses", args, False, provenance=("R:text",))
            return SemanticFrame("assertion", "knowledge_ingest", raw, "uses", args, fact, tags=("uses", *args))

        for pattern, predicate in (
            (r"^(?P<s>.+?) uses (?P<o>.+?)[.!?]?$", "uses"),
            (r"^(?P<s>.+?) performs (?P<o>.+?)[.!?]?$", "performs"),
            (r"^(?P<s>.+?) is (?:the )?parent of (?P<o>.+?)[.!?]?$", "parent"),
            (r"^(?P<s>.+?) supplies (?P<o>.+?)[.!?]?$", "supplies"),
            (r"^(?P<s>.+?) prevents (?P<o>.+?)[.!?]?$", "prevents"),
        ):
            m = re.match(pattern, low, flags=re.I)
            if m:
                args = (self._entity(m.group("s")), self._entity(m.group("o")))
                fact = Fact(predicate, args, provenance=("R:text",))
                return SemanticFrame("assertion", "knowledge_ingest", raw, predicate, args, fact, tags=(predicate, *args))
        m = re.match(r"^(?P<s>.+?) is offline[.!?]?$", low)
        if m:
            args = (self._entity(m.group("s")),)
            fact = Fact("offline", args, provenance=("R:text",))
            return SemanticFrame("assertion", "knowledge_ingest", raw, "offline", args, fact, tags=("offline", *args))
        ja = re.match(r"^(?P<s>.+?)は(?P<o>.+?)を使う[。.]?$", raw)
        if ja:
            args = (self._entity(ja.group("s")), self._entity(ja.group("o")))
            fact = Fact("uses", args, provenance=("R:text:ja",))
            return SemanticFrame("assertion", "knowledge_ingest", raw, "uses", args, fact, tags=("uses", *args), language="ja")
        return SemanticFrame("unknown", "unknown", raw, tags=("unknown",))


@dataclass(frozen=True)
class GridObject:
    object_id: str
    color: str
    cells: tuple[tuple[int, int], ...]
    min_row: int
    max_row: int
    min_col: int
    max_col: int


class SymbolicGridAdapter:
    def __init__(self, color_map: Mapping[int, str] | None = None) -> None:
        self.color_map = dict(color_map or {1: "red", 2: "blue", 3: "green", 4: "yellow"})

    def extract(self, grid: Sequence[Sequence[int]]) -> tuple[list[GridObject], list[Fact]]:
        rows, cols = len(grid), len(grid[0]) if grid else 0
        visited: set[tuple[int, int]] = set()
        objects: list[GridObject] = []
        for r in range(rows):
            for c in range(cols):
                color = int(grid[r][c])
                if color == 0 or (r, c) in visited:
                    continue
                stack, cells = [(r, c)], []
                visited.add((r, c))
                while stack:
                    cr, cc = stack.pop(); cells.append((cr, cc))
                    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and int(grid[nr][nc]) == color:
                            visited.add((nr, nc)); stack.append((nr, nc))
                objects.append(GridObject(f"object_{len(objects)}", self.color_map.get(color, f"color_{color}"), tuple(sorted(cells)), min(x[0] for x in cells), max(x[0] for x in cells), min(x[1] for x in cells), max(x[1] for x in cells)))
        facts: list[Fact] = []
        for obj in objects:
            facts += [Fact("object_color", (obj.object_id, _slug(obj.color)), provenance=("R:grid",)), Fact("object_min_col", (obj.object_id, str(obj.min_col)), provenance=("R:grid",)), Fact("object_area", (obj.object_id, str(len(obj.cells))), provenance=("R:grid",))]
        if objects:
            left = min(objects, key=lambda o: (o.min_col, o.min_row, o.object_id))
            facts += [Fact("leftmost", (left.object_id,), provenance=("R:grid",)), Fact("leftmost_color", (_slug(left.color),), provenance=("R:grid",))]
        return objects, facts


class KnowledgeBase:
    def __init__(self) -> None:
        self._facts: dict[tuple[str, tuple[str, ...], bool], Fact] = {}

    def copy(self) -> "KnowledgeBase":
        other = KnowledgeBase(); other._facts = dict(self._facts); return other

    def add(self, fact: Fact) -> bool:
        old = self._facts.get(fact.key())
        if old is None or fact.depth < old.depth or fact.confidence > old.confidence:
            self._facts[fact.key()] = fact; return True
        return False

    def add_many(self, facts: Iterable[Fact]) -> int:
        return sum(1 for fact in facts if self.add(fact))

    def find(self, predicate: str, pattern: Sequence[str | None] = (), polarity: bool = True, max_depth: int | None = None) -> list[Fact]:
        result = []
        for fact in self._facts.values():
            if fact.predicate != predicate or fact.polarity != polarity: continue
            if max_depth is not None and fact.depth > max_depth: continue
            if pattern and (len(pattern) != len(fact.args) or any(p is not None and p != v for p, v in zip(pattern, fact.args))): continue
            result.append(fact)
        return sorted(result, key=lambda f: (-f.confidence, f.depth, f.args))

    def contradictions_for(self, predicate: str, pattern: Sequence[str | None]) -> list[dict[str, Any]]:
        pos, neg = self.find(predicate, pattern, True), self.find(predicate, pattern, False)
        neg_args = {f.args for f in neg}
        return [{"predicate": predicate, "args": p.args} for p in pos if p.args in neg_args]

    def infer(self, max_rounds: int = 4) -> list[Fact]:
        derived: list[Fact] = []
        for _ in range(max_rounds):
            before = len(self._facts); candidates: list[Fact] = []
            for uses in self.find("uses"):
                for performs in self.find("performs"):
                    if uses.args[1] == performs.args[0]:
                        candidates.append(Fact("capability", (uses.args[0], performs.args[1]), confidence=min(uses.confidence, performs.confidence)*0.97, provenance=(uses.fact_id, performs.fact_id, "RULE:capability"), depth=max(uses.depth, performs.depth)+1))
            parents = self.find("parent")
            for a in parents:
                for b in parents:
                    if a.args[1] == b.args[0]:
                        candidates.append(Fact("grandparent", (a.args[0], b.args[1]), confidence=0.97, provenance=(a.fact_id, b.fact_id, "RULE:grandparent"), depth=max(a.depth,b.depth)+1))
            for off in self.find("offline"):
                for supply in self.find("supplies"):
                    if off.args[0] == supply.args[0]:
                        candidates.append(Fact("unavailable", (supply.args[1],), confidence=0.96, provenance=(off.fact_id, supply.fact_id, "RULE:unavailable"), depth=max(off.depth,supply.depth)+1))
            for unavailable in self.find("unavailable"):
                for prevent in self.find("prevents"):
                    if unavailable.args[0] == prevent.args[0]:
                        candidates.append(Fact("risk", (prevent.args[1],), confidence=0.95, provenance=(unavailable.fact_id, prevent.fact_id, "RULE:risk"), depth=max(unavailable.depth,prevent.depth)+1))
            for fact in candidates:
                if self.add(fact): derived.append(fact)
            if len(self._facts) == before: break
        return derived

    def proof_closure(self, fact: Fact) -> list[Fact]:
        by_id = {f.fact_id: f for f in self._facts.values()}; out: list[Fact] = []; seen: set[str] = set()
        def visit(current: Fact) -> None:
            if current.fact_id in seen: return
            seen.add(current.fact_id); out.append(current)
            for source in current.provenance:
                if source in by_id: visit(by_id[source])
        visit(fact); return out


@dataclass(frozen=True)
class MemoryEvent:
    event_id: str
    key: str
    value: str
    salience: float
    tags: tuple[str, ...]
    provenance: tuple[str, ...]
    authorized_by: str
    cycle: int


@dataclass
class WorkingItem:
    value: str
    salience: float
    updated_cycle: int
    source: str


@dataclass(frozen=True)
class StageRecord:
    stage_id: str
    cycle: int
    name: str
    tags: tuple[str, ...]
    provenance: tuple[str, ...]


class MemorySystem:
    def __init__(self) -> None:
        self.events: list[MemoryEvent] = []; self.working: dict[str, WorkingItem] = {}; self.stages: list[StageRecord] = []; self.cycle = 0

    def copy(self) -> "MemorySystem": return copy.deepcopy(self)

    def propose_event(self, key: str, value: str, salience: float, tags: Sequence[str], provenance: Sequence[str]) -> dict[str, Any]:
        return {"key": key, "value": value, "salience": salience, "tags": tuple(tags), "provenance": tuple(provenance)}

    def commit(self, proposal: Mapping[str, Any], authorized_by: str) -> MemoryEvent:
        if authorized_by != "J/HDS": raise PermissionError("Only J/HDS may authorize memory commit")
        self.cycle += 1
        event = MemoryEvent("M-" + _digest((self.cycle, dict(proposal)))[:12], str(proposal["key"]), str(proposal["value"]), float(proposal.get("salience", .7)), tuple(proposal.get("tags", ())), tuple(proposal.get("provenance", ())), authorized_by, self.cycle)
        self.events.append(event); self.working[event.key] = WorkingItem(event.value, event.salience, self.cycle, event.event_id); return event

    def recall(self, key: str) -> MemoryEvent | None:
        matches = [e for e in self.events if e.key == key]; return max(matches, key=lambda e: e.cycle) if matches else None

    def selective_update(self, observations: Mapping[str, tuple[str, float]], local_steps: int) -> list[dict[str, Any]]:
        trace = []
        for step in range(1, local_steps + 1):
            detail = {}
            for key, (incoming, relevance) in observations.items():
                old = self.working.get(key)
                if old is None:
                    self.working[key] = WorkingItem(incoming, relevance, self.cycle, "selective"); detail[key] = {"action":"WRITE_NEW","value":incoming}; continue
                write = 0.65*relevance + (0.35 if old.value != incoming else 0.0); retain = old.salience*(1-0.45*relevance)
                if write > retain:
                    self.working[key] = WorkingItem(incoming, max(relevance,old.salience*.8), self.cycle, "selective"); action, value = "DELTA_WRITE", incoming
                else: action, value = "RETAIN", old.value
                detail[key] = {"action":action,"retain":round(retain,6),"write":round(write,6),"value":value}
            trace.append({"op":"M_SELECTIVE_TIME_UPDATE","step":step,"detail":detail})
        return trace

    def add_stage(self, name: str, payload: Any, tags: Sequence[str], provenance: Sequence[str] = ()) -> StageRecord:
        self.cycle += 1; stage = StageRecord(f"S-{self.cycle:04d}-{_digest(payload)[:8]}", self.cycle, name, tuple(sorted(set(tags))), tuple(provenance)); self.stages.append(stage); return stage

    def retrieve_stages(self, query_tags: Sequence[str], top_k: int) -> list[dict[str, Any]]:
        q = set(query_tags); max_cycle = max((s.cycle for s in self.stages), default=1); scored = []
        for stage in self.stages:
            tags = set(stage.tags); semantic = len(q & tags)/(len(q | tags) or 1); score = .85*semantic + .15*(stage.cycle/max_cycle); scored.append((score, stage))
        scored.sort(key=lambda x:(-x[0],-x[1].cycle,x[1].stage_id))
        return [{"stage_id":s.stage_id,"name":s.name,"score":round(score,6),"tags":list(s.tags)} for score,s in scored[:top_k] if score>0]


@dataclass(frozen=True)
class Candidate:
    answer: str
    relation: str
    confidence: float
    expert: str
    proof_fact_ids: tuple[str, ...]
    provenance: tuple[str, ...]
    contradiction: tuple[dict[str, Any], ...] = ()
    proposed_memory_write: dict[str, Any] | None = None


@dataclass(frozen=True)
class EffortPolicy:
    name: str; local_steps: int; depth_top_k: int; expert_top_k: int; max_rule_rounds: int; global_reconcile: bool


class DistilledEffortPolicyController:
    POLICIES = {"low":EffortPolicy("low",1,1,1,0,False),"high":EffortPolicy("high",2,2,2,2,True),"max":EffortPolicy("max",3,3,3,4,True)}
    def select(self, frame: SemanticFrame, requested: str | None) -> EffortPolicy:
        if requested in self.POLICIES: return self.POLICIES[requested]
        return self.POLICIES["max" if frame.predicate in {"capability","grandparent","risk"} else "high" if frame.intent in {"memory_recall","grid_relation"} else "low"]


class HDSJudge:
    def decide(self, frame: SemanticFrame, candidates: Sequence[Candidate]) -> "JudgeDecision":
        if not candidates: return JudgeDecision("SUSPEND", None, ("NO_CANDIDATE",))
        top = sorted(candidates, key=lambda c:(-c.confidence,-len(c.proof_fact_ids),c.expert,c.answer))[0]
        if top.contradiction: return JudgeDecision("SUSPEND", top, ("UNRESOLVED_CONTRADICTION","NO_COMMIT"))
        if frame.intent in {"knowledge_query","risk_reasoning","grid_relation"} and not top.proof_fact_ids: return JudgeDecision("SUSPEND", top, ("NO_PROVENANCE_PROOF","NO_COMMIT"))
        if frame.intent == "memory_write": return JudgeDecision("APPROVE", top, ("USER_ASSERTED_WRITE","AUTHORITY_SEPARATED"), True)
        return JudgeDecision("APPROVE", top, ("EVIDENCE_PRESENT","RUBRIC_PASS","AUTHORITY_SEPARATED"))


@dataclass(frozen=True)
class JudgeDecision:
    status: str
    selected_candidate: Candidate | None
    reason_codes: tuple[str, ...]
    authorized_memory_write: bool = False
    authority: str = "J/HDS"


@dataclass(frozen=True)
class SystemResult:
    status: str; text: str; answer: str | None; decision: JudgeDecision; trace: tuple[dict[str, Any], ...]; candidates: tuple[Candidate, ...]
    def serializable(self) -> dict[str, Any]: return asdict(self)


class K3相当能力核:
    """K3公開構造のR/K/M/P/J/G機能形式をMINIDORA内で実装する非ニューラル能力核。"""

    def __init__(self, *, representation: SymbolicRepresentationEngine | None = None, knowledge: KnowledgeBase | None = None, memory: MemorySystem | None = None, generator: NonNeuralGenerator | None = None, judge: HDSJudge | None = None, enable_R: bool = True, enable_K: bool = True, enable_M: bool = True, enable_P: bool = True, enable_J: bool = True, enable_G: bool = True) -> None:
        self.R = representation or SymbolicRepresentationEngine(); self.K = knowledge or KnowledgeBase(); self.M = memory or MemorySystem(); self.G = generator or build_generator()[0]; self.J = judge or HDSJudge(); self.policy_controller = DistilledEffortPolicyController(); self.enable_R=enable_R; self.enable_K=enable_K; self.enable_M=enable_M; self.enable_P=enable_P; self.enable_J=enable_J; self.enable_G=enable_G

    def clone(self, **overrides: Any) -> "K3相当能力核":
        params = dict(representation=copy.deepcopy(self.R), knowledge=self.K.copy(), memory=self.M.copy(), generator=self.G, judge=copy.deepcopy(self.J), enable_R=True, enable_K=True, enable_M=True, enable_P=True, enable_J=True, enable_G=True); params.update(overrides); return K3相当能力核(**params)

    def 知識投入(self, statements: Iterable[str]) -> list[dict[str, Any]]:
        if not self.enable_R or not self.enable_K: return [{"op":"INGEST_BLOCKED"}]
        trace=[]
        for statement in statements:
            frame=self.R.parse(statement)
            if frame.fact is not None: trace.append({"op":"R_TO_K_INGEST","added":self.K.add(frame.fact),"fact_id":frame.fact.fact_id})
        return trace

    def グリッド投入(self, grid: Sequence[Sequence[int]]) -> list[dict[str, Any]]:
        if not self.enable_R or not self.enable_K: return [{"op":"GRID_INGEST_BLOCKED"}]
        objects,facts=SymbolicGridAdapter().extract(grid); count=self.K.add_many(facts); return [{"op":"R_GRID_TO_K","object_count":len(objects),"fact_count":count}]

    def _fact_candidates(self, frame: SemanticFrame, policy: EffortPolicy) -> tuple[list[Candidate], str]:
        expert="direct_fact"; facts=[]
        if frame.intent == "memory_recall" and frame.memory_key:
            event=self.M.recall(frame.memory_key) if self.enable_M else None
            if event: return [Candidate(self.R.label(event.value),"memory_value",event.salience,"memory_recall",(),(event.event_id,))], "memory_recall"
        if frame.intent == "memory_write" and frame.memory_key and frame.memory_value:
            proposal=self.M.propose_event(frame.memory_key,frame.memory_value,.9,("user_asserted",),("R:memory_write",)) if self.enable_M else None
            return ([Candidate(self.R.label(frame.memory_value),"memory_write",.9,"memory_write",(),("R:memory_write",),proposed_memory_write=proposal)] if proposal else []), "memory_write"
        if not self.enable_K or not frame.predicate: return [], expert
        if frame.intent == "risk_reasoning": self.K.infer(policy.max_rule_rounds); facts=self.K.find("risk",(None,),max_depth=policy.max_rule_rounds); expert="risk_causal"
        elif frame.predicate in {"capability","grandparent"} and policy.max_rule_rounds>0: self.K.infer(policy.max_rule_rounds); facts=self.K.find(frame.predicate,frame.args,max_depth=policy.max_rule_rounds); expert="rule_inference"
        else: facts=self.K.find(frame.predicate,frame.args,max_depth=0)
        contradictions=self.K.contradictions_for(frame.predicate,frame.args)
        candidates=[]
        for fact in facts:
            proof=self.K.proof_closure(fact); answer_key=fact.args[0] if fact.predicate=="grandparent" else fact.args[-1]
            candidates.append(Candidate(self.R.label(answer_key),fact.predicate,fact.confidence,expert,tuple(x.fact_id for x in proof),fact.provenance,tuple(contradictions)))
        return candidates, expert

    def 実行(self, request: str, effort: str | None = None) -> SystemResult:
        trace: list[dict[str, Any]]=[]
        if not self.enable_R:
            return SystemResult("SUSPEND","",None,JudgeDecision("SUSPEND",None,("R_DISABLED",)),(),())
        trace.append({"op":"TOKEN_OR_SYMBOL_SPACE","tokens":self.G.token_space.tokenize(request)})
        frame=self.R.parse(request); trace.append({"op":"R_SYMBOLIC_REPRESENTATION","frame":asdict(frame)})
        if frame.kind=="unknown": return self._emit(frame,JudgeDecision("SUSPEND",None,("R_PARSE_FAILED",)),[],trace)
        if not self.enable_P: return self._emit(frame,JudgeDecision("SUSPEND",None,("P_DISABLED",)),[],trace)
        policy=self.policy_controller.select(frame,effort); trace.append({"op":"P_DISTILLED_EFFORT_POLICY","policy":asdict(policy)})
        if self.enable_M:
            trace += self.M.selective_update({"intent":(frame.intent,.92),"predicate":(frame.predicate or "none",.88)},policy.local_steps)
            stage=self.M.add_stage("representation",asdict(frame),frame.tags,("R",)); trace.append({"op":"M_STAGE_APPEND","stage_id":stage.stage_id})
        else: trace.append({"op":"M_DISABLED"})
        contradictions=self.K.contradictions_for(frame.predicate,frame.args) if self.enable_K and frame.predicate and policy.global_reconcile else []
        trace.append({"op":"P_GLOBAL_RECONCILE","contradictions":contradictions} if policy.global_reconcile else {"op":"P_GLOBAL_RECONCILE_SKIPPED"})
        if self.enable_M: trace.append({"op":"M_DEPTH_RETRIEVE_TOPK","selected":self.M.retrieve_stages(frame.tags,policy.depth_top_k)})
        candidates, expert=self._fact_candidates(frame,policy)
        trace.append({"op":"P_ROUTE_SPECIALISTS_TOPK","selected":[{"expert":expert,"score":100}] if candidates or expert else [],"shared_guard":"evidence_and_contradiction_rubric"})
        trace.append({"op":"P_EXPERT_PROPOSE","expert":expert,"candidate_count":len(candidates)})
        trace.append({"op":"P_NORMALIZE_CANDIDATES","count":len(candidates),"authority":"candidate_only; J/HDS required"})
        if not self.enable_J:
            top=candidates[0] if candidates else None; return self._emit(frame,JudgeDecision("BYPASS",top,("J_DISABLED_UNAUTHORIZED",),authority="NONE"),candidates,trace)
        decision=self.J.decide(frame,candidates); trace.append({"op":"J_RUBRIC_DECISION","status":decision.status,"reason_codes":list(decision.reason_codes),"authority":decision.authority})
        if decision.status=="APPROVE" and decision.authorized_memory_write and decision.selected_candidate and decision.selected_candidate.proposed_memory_write and self.enable_M:
            event=self.M.commit(decision.selected_candidate.proposed_memory_write,"J/HDS"); trace.append({"op":"M_COMMIT_AUTHORIZED","event_id":event.event_id})
        return self._emit(frame,decision,candidates,trace)

    def _emit(self, frame: SemanticFrame, decision: JudgeDecision, candidates: Sequence[Candidate], trace: list[dict[str, Any]]) -> SystemResult:
        selected=decision.selected_candidate; answer=selected.answer if selected else ""; plan=GenerationPlan("APPROVE" if decision.status in {"APPROVE","BYPASS"} else "SUSPEND",frame.intent,answer,selected.relation if selected else (frame.predicate or "none"),bool(selected and (selected.proof_fact_ids or selected.provenance)),frame.language)
        if not self.enable_G: trace.append({"op":"G_DISABLED"}); return SystemResult(decision.status,"",answer or None,decision,tuple(trace),tuple(candidates))
        text,gtrace=self.G.generate(plan); trace += gtrace; return SystemResult(decision.status,text,answer or None,decision,tuple(trace),tuple(candidates))


__all__ = ["Fact","SemanticFrame","SymbolicRepresentationEngine","SymbolicGridAdapter","KnowledgeBase","MemorySystem","WorkingItem","Candidate","EffortPolicy","DistilledEffortPolicyController","HDSJudge","JudgeDecision","SystemResult","K3相当能力核"]
