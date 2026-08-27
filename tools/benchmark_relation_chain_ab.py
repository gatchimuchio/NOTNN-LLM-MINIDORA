from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import gpqa_measure_current as gpqa
import minidora.hds_model_projection as model_projection
from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照検索
from minidora.k3_functional import K3相当能力核
from minidora.standard_reference import 一般知識参照供給器
from minidora.模型 import 標準模型核


def _formal(question_ir, references, compiler, base_core, *, chain: bool):
    original = model_projection.関係連鎖模型核V2
    if not chain:
        model_projection.関係連鎖模型核V2 = lambda core: core
    try:
        return HDS選択推論実行(
            question_ir,
            tuple(references),
            コンパイル=compiler.コンパイル,
            基礎能力核=base_core,
            作業再作用=True,
            局所再照合=True,
            模型核=標準模型核(),
            正式模型評価=True,
        )
    finally:
        model_projection.関係連鎖模型核V2 = original


def _metrics(rows, prefix: str):
    total=len(rows)
    correct=sum(bool(row[f"{prefix}_correct"]) for row in rows)
    answered=sum(bool(row[f"{prefix}_answered"]) for row in rows)
    return {
        "correct":correct,
        "total":total,
        "accuracy_percent":100.0*correct/total if total else 0.0,
        "answered":answered,
        "answer_rate_percent":100.0*answered/total if total else 0.0,
        "answered_accuracy_percent":100.0*correct/answered if answered else 0.0,
        "suspended":total-answered,
    }


def main()->int:
    with tempfile.TemporaryDirectory(prefix="minidora-chain-ab-") as td:
        work=Path(td)
        csv_path,zip_hash,csv_hash=gpqa._download_dataset(work)
        cases=gpqa._load_cases(csv_path)
        if len(cases)!=198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")

        api_key=os.getenv("OPENALEX_API_KEY","").strip() or None
        provider=一般知識参照供給器(
            OpenAlex_API_key=api_key,
            Wikipedia言語=("en",),
            timeout=8.0,
            最大本文文字数=6000,
            並列=True,
            最大並列=4,
        )
        compiler=公開HDSコンパイラ()
        base_core=K3相当能力核()
        details=[]

        for index,(question,choices,gold) in enumerate(cases):
            question_ir=compiler.問題IR(question,choices)
            references=HDS参照検索(provider,question_ir)
            off=_formal(question_ir,references,compiler,base_core,chain=False)
            on=_formal(question_ir,references,compiler,base_core,chain=True)

            off_answered=off.状態=="APPROVE" and off.回答ラベル is not None
            on_answered=on.状態=="APPROVE" and on.回答ラベル is not None
            off_correct=bool(off_answered and off.回答ラベル==gold)
            on_correct=bool(on_answered and on.回答ラベル==gold)
            applied="RELATION_CHAIN_APPLIED" in on.理由
            details.append({
                "index":index,
                "gold":gold,
                "retrieved":len(references),
                "off_predicted":off.回答ラベル,
                "off_answered":off_answered,
                "off_correct":off_correct,
                "off_status":off.状態,
                "on_predicted":on.回答ラベル,
                "on_answered":on_answered,
                "on_correct":on_correct,
                "on_status":on.状態,
                "chain_applied":applied,
                "on_reasons":list(on.理由),
                "off_reasons":list(off.理由),
            })
            print(
                f"CASE {index+1:03d}/198 chain={int(applied)} off={off.回答ラベル} on={on.回答ラベル} "
                f"off_correct={off_correct} on_correct={on_correct}",
                flush=True,
            )

        off_metrics=_metrics(details,"off")
        on_metrics=_metrics(details,"on")
        improved=sum(row["on_correct"] and not row["off_correct"] for row in details)
        regressed=sum(row["off_correct"] and not row["on_correct"] for row in details)
        changed=sum(row["off_predicted"]!=row["on_predicted"] or row["off_status"]!=row["on_status"] for row in details)
        applied_rows=[row for row in details if row["chain_applied"]]
        applied_improved=sum(row["on_correct"] and not row["off_correct"] for row in applied_rows)
        applied_regressed=sum(row["off_correct"] and not row["on_correct"] for row in applied_rows)
        result={
            "schema":"minidora.relation-chain-ab.v1",
            "protocol":{
                "dataset":"GPQA Diamond official",
                "dataset_zip_sha256":zip_hash,
                "dataset_csv_sha256":csv_hash,
                "choice_shuffle_seed":gpqa.SEED,
                "same_retrieved_references":True,
                "same_hds_compiler":True,
                "same_formal_model_boundary":True,
                "same_output_only_hds_gate":True,
                "difference_only":"relation-chain v2 action enabled vs disabled",
                "openalex_enabled":api_key is not None,
            },
            "chain_off":off_metrics,
            "chain_on":on_metrics,
            "delta":{
                "correct":on_metrics["correct"]-off_metrics["correct"],
                "accuracy_points":on_metrics["accuracy_percent"]-off_metrics["accuracy_percent"],
                "answered":on_metrics["answered"]-off_metrics["answered"],
                "answer_rate_points":on_metrics["answer_rate_percent"]-off_metrics["answer_rate_percent"],
                "answered_accuracy_points":on_metrics["answered_accuracy_percent"]-off_metrics["answered_accuracy_percent"],
                "changed_outputs":changed,
                "improved_cases":improved,
                "regressed_cases":regressed,
                "net_improved_cases":improved-regressed,
            },
            "chain_application":{
                "applied_cases":len(applied_rows),
                "improved_cases":applied_improved,
                "regressed_cases":applied_regressed,
                "net_improved_cases":applied_improved-applied_regressed,
            },
            "details":details,
        }
        out=Path(os.getenv("MINIDORA_CHAIN_AB_OUT","relation_chain_ab.json"))
        out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("RELATION_CHAIN_AB="+json.dumps({
            "off":off_metrics,
            "on":on_metrics,
            "delta":result["delta"],
            "chain_application":result["chain_application"],
        },ensure_ascii=False),flush=True)
        print(f"RESULT_FILE={out}",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
