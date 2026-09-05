from __future__ import annotations

"""24点系Coreと現行Coreを同一Question/Referenceで比較する因果A/B。

外部参照は各問題につき一度だけ取得し、その同一参照recordを両Coreへ渡す。
Goldは両推論完了後の採点にのみ使用する。
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

import benchmark as bench
import gpqa_measure_current as gpqa

from minidora.hds_choice_runtime import HDS選択推論実行 as 現行Core選択
from minidora.hds_choice_runtime_v24 import HDS選択推論実行 as Core24選択
from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.hds_reference import HDS参照検索
from minidora.standard_reference import 一般知識参照供給器
from minidora.能力状態差循環 import 標準能力模型核


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--snapshot-out", type=Path, required=True)
    p.add_argument("--cache-dir", type=Path, default=Path(".cache/minidora-core-ab"))
    p.add_argument("--start-index", type=int, default=0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-openalex", action="store_true")
    return p


def _reference_dict(r) -> dict[str, Any]:
    return {
        "識別子": str(r.識別子),
        "対象": str(r.対象),
        "内容": str(r.内容),
        "由来": str(r.由来),
        "供給器": str(r.供給器),
        "信頼": float(r.信頼),
        "意味キー": r.意味キー,
        "値": r.値,
        "時点": r.時点,
        "範囲": r.範囲,
        "条件": [[str(k), str(v)] for k, v in r.条件],
        "意味確定": bool(r.意味確定),
    }


def _result_dict(result, gold: str) -> dict[str, Any]:
    pred = result.回答ラベル
    answered = result.状態 == "APPROVE" and pred is not None
    return {
        "predicted": pred,
        "status": result.状態,
        "answered": answered,
        "correct": bool(answered and pred == gold),
        "reasons": list(result.理由),
        "checkpoint_reactivations": int(result.checkpoint再活性数),
        "global_reconciliations": int(result.大域再照合数),
        "candidate_cross_updates": int(result.候補横断更新数),
        "specialist_actions": int(result.専門作用起動数),
        "local_windows": int(result.局所Window数),
        "local_reconciliations": int(result.局所再照合数),
    }


def main() -> int:
    args = _parser().parse_args()
    csv_path, zip_hash, csv_hash = bench._prepare_gpqa_dataset(args.cache_dir, refresh=False)
    cases = gpqa._load_cases(csv_path)
    selected = bench._selected_range(len(cases), args.start_index, args.limit)

    api_key = None if args.no_openalex else (os.getenv("OPENALEX_API_KEY", "").strip() or None)
    provider = 一般知識参照供給器(
        OpenAlex_API_key=api_key,
        Wikipedia言語=("en",),
        timeout=8.0,
        最大本文文字数=6000,
        並列=True,
        最大並列=4,
    )
    compiler = 公開HDSコンパイラ()
    details: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []

    for index in selected:
        question, choices, gold = cases[index]
        question_ir = compiler.問題IR(question, choices)
        references = tuple(HDS参照検索(provider, question_ir))

        baseline = Core24選択(
            question_ir,
            references,
            コンパイル=compiler.コンパイル,
            基礎能力核=None,
            模型核=標準能力模型核(),
            正式模型評価=True,
        )
        current = 現行Core選択(
            question_ir,
            references,
            コンパイル=compiler.コンパイル,
            基礎能力核=None,
            模型核=標準能力模型核(),
            正式模型評価=True,
        )

        b = _result_dict(baseline, gold)
        c = _result_dict(current, gold)
        details.append({
            "index": index,
            "gold": gold,
            "retrieved": len(references),
            "core24": b,
            "current": c,
            "improved": bool(c["correct"] and not b["correct"]),
            "regressed": bool(b["correct"] and not c["correct"]),
            "answer_changed": b["predicted"] != c["predicted"],
        })
        snapshots.append({
            "index": index,
            "question": question,
            "choices": list(choices),
            "gold": gold,
            "references": [_reference_dict(r) for r in references],
        })
        print(
            f"CASE {index + 1:03d}/198 core24={b['predicted']} current={c['predicted']} "
            f"improved={details[-1]['improved']} regressed={details[-1]['regressed']} refs={len(references)}",
            flush=True,
        )

    baseline_correct = sum(int(x["core24"]["correct"]) for x in details)
    current_correct = sum(int(x["current"]["correct"]) for x in details)
    improved = sum(int(x["improved"]) for x in details)
    regressed = sum(int(x["regressed"]) for x in details)
    current_specialist = sum(int(x["current"]["specialist_actions"]) for x in details)
    local_selected = sum("FORMAL_LOCAL_VIEW_RECHECK_SELECTED" in x["current"]["reasons"] for x in details)

    payload = {
        "schema": "minidora.core24-current.same-reference-ab.v1",
        "protocol": {
            "dataset_zip_sha256": zip_hash,
            "dataset_csv_sha256": csv_hash,
            "choice_shuffle_seed": gpqa.SEED,
            "selected_indices": list(selected),
            "same_reference_records": True,
            "gold_boundary": "gold used only after Core24 and current inference",
            "baseline": "hds_choice_runtime_v24.HDS選択推論実行",
            "current": "hds_choice_runtime.HDS選択推論実行",
            "specialist_module": False,
            "openalex_enabled": api_key is not None,
        },
        "metrics": {
            "completed": len(details),
            "core24_correct": baseline_correct,
            "current_correct": current_correct,
            "correct_delta": current_correct - baseline_correct,
            "improved_cases": improved,
            "regressed_cases": regressed,
            "net_improved_cases": improved - regressed,
            "answer_changed_cases": sum(int(x["answer_changed"]) for x in details),
            "current_specialist_actions": current_specialist,
            "current_local_view_selected_cases": local_selected,
        },
        "details": details,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.snapshot_out.write_text(json.dumps({
        "schema": "minidora.gpqa.reference-snapshot.v1",
        "dataset_csv_sha256": csv_hash,
        "choice_shuffle_seed": gpqa.SEED,
        "cases": snapshots,
    }, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("CORE_AB=" + json.dumps(payload["metrics"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
