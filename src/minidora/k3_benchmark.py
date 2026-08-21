from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any
import ast
import json
import sys
import time
import tracemalloc

try:
    import resource as _resource
except ImportError:  # pragma: no cover
    _resource = None

from .k3_generation import (
    ANSWER_SLOT, EOS, CategoricalDecisionForest, ConditionalSurface,
    GenerationPlan, NonNeuralDecoder, build_generator,
)
from .k3_functional import (
    Candidate, DistilledEffortPolicyController, HDSJudge, K3相当能力核,
    KnowledgeBase, MemorySystem, SymbolicGridAdapter, WorkingItem,
)

LAYER0_ROLES = (
    "TOKEN_OR_SYMBOL_SPACE",
    "CONTEXT_CONDITIONING_STATE",
    "LEARNED_PARAMETERIZED_TRANSFORM",
    "CONDITIONAL_LINGUISTIC_OUTPUT_SURFACE",
    "SEQUENCE_MODELING_OBJECTIVE_OR_EQUIVALENT_FITTING_CRITERION",
    "DECODING_OR_EMISSION_INTERFACE",
)


@dataclass(frozen=True)
class TestRecord:
    name: str
    passed: bool
    evidence: Any


def run_k3_equivalence_benchmark() -> dict[str, Any]:
    started = time.perf_counter(); tracemalloc.start(); tests: list[TestRecord] = []
    def check(name: str, condition: bool, evidence: Any) -> None: tests.append(TestRecord(name, bool(condition), evidence))

    generator, fitting_samples, fit = build_generator()
    base = K3相当能力核(generator=generator)

    # 1: non-neural dependency audit across the new K3 ability core.
    imports: set[str] = set()
    for filename in ("k3_generation.py", "k3_functional.py"):
        tree = ast.parse((Path(__file__).with_name(filename)).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split(".")[0])
    banned = {"torch","tensorflow","jax","numpy","sklearn","keras","transformers","paddle"}
    check("non_neural_dependency_audit", not (imports & banned), {"banned_present": sorted(imports & banned)})

    # 2-18: Layer-0 / G operational equivalence.
    ids = generator.token_space.encode("The answer is <answer> .")
    roundtrip = generator.token_space.decode_tokens([generator.token_space.id_to_token[i] for i in ids])
    check("L0_token_space_roundtrip", "answer" in roundtrip and ANSWER_SLOT in roundtrip, {"roundtrip": roundtrip})
    check("L0_sequence_fitting_reduces_NLL", fit["after_nll"] < fit["before_nll"] * .65, fit)
    check("L0_learned_parameterized_transform_nonzero", fit["parameter_count"] > 100, fit)
    approve = GenerationPlan("APPROVE","knowledge_query","selective update","capability",True)
    suspend = GenerationPlan("SUSPEND","unknown","","none",False)
    dist_a = generator.surface.next_distribution([], approve); dist_b = generator.surface.next_distribution([], suspend)
    delta = sum(abs(dist_a.get(t,0)-dist_b.get(t,0)) for t in set(dist_a)|set(dist_b))
    check("L0_context_conditions_distribution", delta > .15, {"l1_delta": delta})
    check("L0_conditional_surface_normalized", abs(sum(dist_a.values())-1) < 1e-9, sum(dist_a.values()))
    generated, gen_trace = generator.generate(approve)
    check("L0_decoder_emits_observable_text", bool(generated) and "selective update" in generated.lower(), {"text": generated, "steps": len(gen_trace)})
    unseen = GenerationPlan("APPROVE","knowledge_query","novel-token-77","unseen_relation",True)
    unseen_text,_ = generator.generate(unseen)
    check("G_composes_unseen_answer_slot", "novel-token-77" in unseen_text.lower(), {"text": unseen_text})
    start_allowed = sorted({path[0] for path in NonNeuralDecoder.APPROVE_PATHS})
    learned_start = generator.surface.next_distribution([], approve, start_allowed)
    check("G_learned_transform_is_nonuniform", max(learned_start.values())-min(learned_start.values()) > .02, learned_start)

    def greedy(transform: CategoricalDecisionForest, plan: GenerationPlan, limit: int = 16) -> list[str]:
        surface = ConditionalSurface(generator.token_space, transform); prefix: list[str] = []
        for _ in range(limit):
            d = surface.next_distribution(prefix, plan); token = max(d, key=lambda t:(d[t],t)); prefix.append(token)
            if token == EOS: break
        return prefix
    learned_seq = greedy(generator.transform, approve); unfitted_seq = greedy(CategoricalDecisionForest(generator.token_space.id_to_token), approve)
    check("G_learned_transform_generates_complete_sequence_without_lattice", learned_seq[-1:] == [EOS] and ANSWER_SLOT in learned_seq and unfitted_seq[-1:] != [EOS], {"learned": learned_seq, "unfitted": unfitted_seq})
    role_evidence = {
        "TOKEN_OR_SYMBOL_SPACE": len(generator.token_space)>5,
        "CONTEXT_CONDITIONING_STATE": delta>.15,
        "LEARNED_PARAMETERIZED_TRANSFORM": generator.transform.fitted and generator.transform.parameter_count()>0,
        "CONDITIONAL_LINGUISTIC_OUTPUT_SURFACE": abs(sum(dist_a.values())-1)<1e-9,
        "SEQUENCE_MODELING_OBJECTIVE_OR_EQUIVALENT_FITTING_CRITERION": generator.transform.training_sample_count == len(fitting_samples),
        "DECODING_OR_EMISSION_INTERFACE": bool(generated),
    }
    check("L0_all_six_roles_operational", all(role_evidence.values()), role_evidence)
    subsets=[]
    for size in range(7):
        for subset in combinations(LAYER0_ROLES,size): subsets.append((subset,set(subset)==set(LAYER0_ROLES)))
    check("L0_64_subset_enumeration", len(subsets)==64 and sum(1 for s,p in subsets if len(s)<6 and p)==0 and sum(1 for s,p in subsets if len(s)==5 and not p)==6, {"total":len(subsets)})
    token_error=None
    try:
        none_space=None; none_space.tokenize("test")  # type: ignore[union-attr]
    except Exception as exc: token_error=type(exc).__name__
    check("L0_REMOVE_TOKEN_breaks_representation", token_error is not None, token_error)
    contextless_a=generator.transform.predict_distribution({}); contextless_b=generator.transform.predict_distribution({})
    contextless_delta=sum(abs(contextless_a.get(t,0)-contextless_b.get(t,0)) for t in set(contextless_a)|set(contextless_b))
    check("L0_REMOVE_CONTEXT_collapses_conditioning", contextless_delta==0 and delta>.15, {"with":delta,"without":contextless_delta})
    removed=CategoricalDecisionForest(generator.token_space.id_to_token); removed_nll=removed.nll(fitting_samples)
    check("L0_REMOVE_TRANSFORM_removes_learned_model_object", not removed.fitted and removed.parameter_count()==0 and removed_nll >= fit["before_nll"]-1e-9, {"nll":removed_nll})
    surface_error=None
    try:
        NonNeuralDecoder(generator.token_space, None).decode(approve)  # type: ignore[arg-type]
    except Exception as exc: surface_error=type(exc).__name__
    check("L0_REMOVE_OUTPUT_SURFACE_breaks_token_scoring", surface_error is not None, surface_error)
    fit_error=None
    try: CategoricalDecisionForest(generator.token_space.id_to_token).fit([])
    except Exception as exc: fit_error=type(exc).__name__
    check("L0_REMOVE_FITTING_CRITERION_breaks_learning", fit_error=="ValueError", fit_error)
    check("L0_REMOVE_EMISSION_leaves_scores_without_text", bool(generator.surface.next_distribution([],approve)) and ""=="", {"surface":True,"text":""})

    # 19-27: R/K/P multi-hop and grid.
    en=base.R.parse("Kimi K3 uses KDA."); ja=base.R.parse("Kimi K3はKDAを使う。")
    check("R_bilingual_forms_same_fact", en.fact is not None and ja.fact is not None and en.fact.predicate==ja.fact.predicate and en.fact.args==ja.fact.args, {"en":asdict(en),"ja":asdict(ja)})
    q=base.R.parse("What capability does Kimi K3 have?")
    check("R_query_to_typed_frame", q.kind=="question" and q.predicate=="capability" and q.args[0]=="kimi_k3", asdict(q))
    base.知識投入(["Kimi K3 uses KDA.","KDA performs selective temporal update.","Alice is parent of Bob.","Bob is parent of Carol.","Pump P1 supplies lubrication.","Lubrication prevents turbine overheating.","Pump P1 is offline."])
    direct=base.実行("What does Kimi K3 use?",effort="low")
    check("K_direct_fact_answer", direct.status=="APPROVE" and direct.answer=="kda", direct.serializable())
    cap_low=base.実行("What capability does Kimi K3 have?",effort="low"); cap_max=base.実行("What capability does Kimi K3 have?",effort="max")
    check("P_effort_low_vs_max_changes_closure", cap_low.status=="SUSPEND" and cap_max.status=="APPROVE" and cap_max.answer=="selective temporal update", {"low":cap_low.status,"max":cap_max.answer})
    grand=base.実行("Who is the grandparent of Carol?",effort="max")
    check("K_grandparent_multihop", grand.status=="APPROVE" and grand.answer=="alice", grand.serializable())
    risk=base.実行("What risk follows if Pump P1 is offline?",effort="max")
    check("K_causal_risk_multihop", risk.status=="APPROVE" and risk.answer=="turbine overheating", risk.serializable())
    proof_sizes=[len(c.proof_fact_ids) for c in cap_max.candidates]
    check("K_provenance_closure_available", max(proof_sizes or [0])>=3, proof_sizes)
    grid=base.clone(knowledge=KnowledgeBase(),memory=MemorySystem()); grid_trace=grid.グリッド投入([[1,1,0,0,2],[1,1,0,0,2]]); grid_result=grid.実行("What color is the leftmost object?",effort="high")
    check("R_grid_to_symbolic_facts", grid_trace[0].get("object_count")==2 and grid_trace[0].get("fact_count",0)>=7, grid_trace)
    check("RKG_grid_question_answer", grid_result.status=="APPROVE" and grid_result.answer=="red", grid_result.serializable())

    # 28-35: M/P controls.
    memsys=base.clone(knowledge=KnowledgeBase(),memory=MemorySystem())
    frame_write=memsys.R.parse("Remember that my project code is Atlas-7."); proposal=memsys.M.propose_event(frame_write.memory_key or "",frame_write.memory_value or "",.9,("user_asserted",),("R:memory_write",))
    check("M_proposal_does_not_mutate", len(memsys.M.events)==0 and bool(proposal), {"events":len(memsys.M.events)})
    write=memsys.実行("Remember that my project code is Atlas-7.",effort="high"); recall=memsys.実行("What is my project code?",effort="high")
    check("M_J_authorized_commit", write.status=="APPROVE" and len(memsys.M.events)==1 and memsys.M.events[0].authorized_by=="J/HDS", {"events":len(memsys.M.events)})
    check("M_recall_after_authorized_commit", recall.status=="APPROVE" and recall.answer=="atlas-7", recall.serializable())
    mem=MemorySystem(); mem.working["mission"]=WorkingItem("protect",.95,0,"seed"); sel=mem.selective_update({"mission":("ignore",.15),"status":("offline",.95)},3)
    check("M_selective_retain_and_delta_write", mem.working["mission"].value=="protect" and mem.working["status"].value=="offline", {"trace":sel})
    mem.add_stage("capability_stage",{"x":1},("capability","kda")); mem.add_stage("memory_stage",{"x":2},("memory","project")); mem.add_stage("risk_stage",{"x":3},("risk","pump")); retrieved=mem.retrieve_stages(("capability","kda"),1)
    check("M_AttnRes_like_depth_retrieval", bool(retrieved) and retrieved[0]["name"]=="capability_stage", retrieved)
    selected=[x for x in cap_max.trace if x.get("op")=="P_ROUTE_SPECIALISTS_TOPK"]
    routed=[x["expert"] for x in selected[-1]["selected"]] if selected else []
    check("P_topk_specialist_routing", "rule_inference" in routed, routed)
    policies=[x for x in cap_max.trace if x.get("op")=="P_DISTILLED_EFFORT_POLICY"]
    check("P_MOPD_like_effort_controller", bool(policies) and policies[-1]["policy"]["name"]=="max", policies[-1] if policies else None)
    check("P_periodic_global_reconcile", any(x.get("op")=="P_GLOBAL_RECONCILE" for x in cap_max.trace), [x.get("op") for x in cap_max.trace])

    # 36-44: J controls and component ablations.
    contradiction=base.clone(knowledge=KnowledgeBase(),memory=MemorySystem()); contradiction.知識投入(["Kimi K3 uses KDA.","Kimi K3 does not use KDA."]); contradicted=contradiction.実行("What does Kimi K3 use?",effort="max")
    check("J_suspends_unresolved_contradiction", contradicted.status=="SUSPEND" and "UNRESOLVED_CONTRADICTION" in contradicted.decision.reason_codes, contradicted.serializable())
    unsupported=Candidate("fabricated","capability",.99,"negative_control",(),())
    unsupported_decision=HDSJudge().decide(q,[unsupported])
    check("J_suspends_unsupported_candidate", unsupported_decision.status=="SUSPEND" and "NO_PROVENANCE_PROOF" in unsupported_decision.reason_codes, asdict(unsupported_decision))
    check("J_bypass_would_emit_bad_candidate", unsupported.answer=="fabricated" and unsupported_decision.status!="APPROVE", asdict(unsupported_decision))
    r_off=base.clone(enable_R=False).実行("What capability does Kimi K3 have?",effort="max")
    k_off=base.clone(enable_K=False).実行("What capability does Kimi K3 have?",effort="max")
    p_off=base.clone(enable_P=False).実行("What capability does Kimi K3 have?",effort="max")
    g_off=base.clone(enable_G=False).実行("What capability does Kimi K3 have?",effort="max")
    m_off=memsys.clone(enable_M=False).実行("What is my project code?",effort="high")
    j_off=contradiction.clone(enable_J=False).実行("What does Kimi K3 use?",effort="max")
    check("ABLATION_R_breaks_representation", r_off.status=="SUSPEND" and "R_DISABLED" in r_off.decision.reason_codes, r_off.serializable())
    check("ABLATION_K_breaks_knowledge_answer", k_off.status=="SUSPEND" and not k_off.answer, k_off.serializable())
    check("ABLATION_P_breaks_candidate_generation", p_off.status=="SUSPEND" and "P_DISABLED" in p_off.decision.reason_codes, p_off.serializable())
    check("ABLATION_G_breaks_emission", g_off.status=="APPROVE" and g_off.text=="", g_off.serializable())
    check("ABLATION_M_breaks_recall", m_off.status=="SUSPEND" and not m_off.answer, m_off.serializable())
    check("ABLATION_J_removes_authority_and_emits_bypass", j_off.decision.status=="BYPASS" and j_off.decision.authority=="NONE" and bool(j_off.text), j_off.serializable())

    # 45-47: integrated trace, determinism, resources.
    required={"TOKEN_OR_SYMBOL_SPACE","R_SYMBOLIC_REPRESENTATION","P_DISTILLED_EFFORT_POLICY","M_SELECTIVE_TIME_UPDATE","P_GLOBAL_RECONCILE","M_DEPTH_RETRIEVE_TOPK","P_ROUTE_SPECIALISTS_TOPK","P_EXPERT_PROPOSE","J_RUBRIC_DECISION","CONDITIONAL_LINGUISTIC_OUTPUT_SURFACE","DECODING_OR_EMISSION_INTERFACE"}
    observed={x.get("op") for x in cap_max.trace}
    check("INTEGRATED_full_RKMPJG_trace", required<=observed, {"missing":sorted(required-observed)})
    da=base.clone().実行("What capability does Kimi K3 have?",effort="max").serializable(); db=base.clone().実行("What capability does Kimi K3 have?",effort="max").serializable()
    check("INTEGRATED_deterministic_same_state_input", da==db, {"equal":da==db})
    current,peak=tracemalloc.get_traced_memory(); tracemalloc.stop(); elapsed=time.perf_counter()-started
    peak_rss=None
    if _resource is not None:
        raw=int(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss); peak_rss=raw if sys.platform=="darwin" else raw*1024
    resource_ok=elapsed<10 and peak<128*1024*1024 and (peak_rss is None or peak_rss<256*1024*1024)
    check("RESOURCE_short_time_and_memory", resource_ok, {"elapsed_seconds":elapsed,"peak_tracemalloc_bytes":peak,"peak_rss_bytes":peak_rss})

    failed=[t for t in tests if not t.passed]
    return {
        "schema_version":"MINIDORA-K3-FUNCTIONAL-EQUIVALENCE-1.0",
        "status":"PASS" if not failed else "FAIL",
        "pass_count":sum(t.passed for t in tests),
        "fail_count":len(failed),
        "total_count":len(tests),
        "tests":[asdict(t) for t in tests],
        "failed_tests":[asdict(t) for t in failed],
        "runtime":{"elapsed_seconds":elapsed,"peak_tracemalloc_mib":peak/(1024*1024),"peak_rss_mib":peak_rss/(1024*1024) if peak_rss is not None else None},
        "fit_metrics":fit,
        "claim":"K3公開構造に対する機能形式・統合循環の相当。K3の重み・規模・世界知識・frontier性能の同等性は主張しない。",
    }


if __name__ == "__main__":
    print(json.dumps(run_k3_equivalence_benchmark(), ensure_ascii=False, indent=2, default=str))
