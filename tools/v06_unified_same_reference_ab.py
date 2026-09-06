from __future__ import annotations

"""v0.6 unified route vs current main GPQA Diamond paired A/B.

Per case the initial Reference set is retrieved exactly once and shared by both routes.
Gold is used only after both inferences for scoring.
This file is intended for the sandbox/v0.6-score branch only.
"""

from collections import Counter
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import gpqa_measure_current as gpqa  # noqa: E402
from minidora.hds_choice_runtime import HDS選択推論実行  # noqa: E402
from minidora.hds_compiler_v1 import 公開HDSコンパイラ  # noqa: E402
from minidora.hds_reference import HDS参照検索  # noqa: E402
from minidora.hds介入制御 import 標準HDS介入制御  # noqa: E402
from minidora.hds監督選択runtime import HDS監督選択実行  # noqa: E402
from minidora.hds統一実行 import HDS統一選択評価  # noqa: E402
from minidora.hds統一状態循環 import HDS統一状態Session  # noqa: E402
from minidora.standard_reference import 一般知識参照供給器  # noqa: E402
from minidora.能力状態差循環 import 標準能力模型核  # noqa: E402
from minidora.計算実行器 import 計算実行器  # noqa: E402


def _metric(correct: int, answered: int, total: int) -> dict[str, float | int]:
    return {
        "correct": correct,
        "total": total,
        "accuracy_percent": 100.0 * correct / total if total else 0.0,
        "answered": answered,
        "answer_rate_percent": 100.0 * answered / total if total else 0.0,
        "answered_accuracy_percent": 100.0 * correct / answered if answered else 0.0,
        "suspended": total - answered,
    }


def _current_main_route(question_ir, references, *, compiler, provider):
    initial = HDS選択推論実行(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        基礎能力核=None,
        模型核=標準能力模型核(),
        正式模型評価=True,
    )
    if initial.状態 == "APPROVE" and initial.回答ラベル is not None:
        return initial, tuple(references)

    supervised = HDS監督選択実行(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        基礎能力核=None,
        模型核=標準能力模型核(),
        参照供給器=provider,
        計算実行器_=計算実行器(),
        HDS制御=標準HDS介入制御(),
        HDS介入予算=6,
        初期選択=initial,
    )
    return supervised.選択, tuple(supervised.参照)


def _v06_route(question_ir, references, *, compiler):
    query = str(getattr(question_ir, "正規化文", "") or getattr(question_ir, "原文", ""))
    session = HDS統一状態Session(
        query,
        tuple(references),
        主体状態=None,
        認知世界ID=str(getattr(question_ir, "認知世界ID", "") or ""),
    )
    return HDS統一選択評価(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        模型核=標準能力模型核(),
        統一session=session,
        主体状態=None,
    ), session


def main() -> int:
    out = Path(os.environ.get("MINIDORA_V06_AB_OUT", "v06_unified_same_reference_ab.json"))
    with tempfile.TemporaryDirectory(prefix="minidora-v06-ab-") as td:
        work = Path(td)
        csv_path, zip_hash, csv_hash = gpqa._download_dataset(work)
        cases = gpqa._load_cases(csv_path)
        if len(cases) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(cases)}")

        api_key = os.getenv("OPENALEX_API_KEY", "").strip() or None
        provider = 一般知識参照供給器(
            OpenAlex_API_key=api_key,
            Wikipedia言語=("en",),
            timeout=8.0,
            最大本文文字数=6000,
            並列=True,
            最大並列=4,
        )
        compiler = 公開HDSコンパイラ()

        current_correct = current_answered = 0
        v06_correct = v06_answered = 0
        improved = regressed = changed = 0
        retrieval_empty = initial_docs = current_final_docs = 0
        current_reasons: Counter[str] = Counter()
        v06_reasons: Counter[str] = Counter()
        v06_actions: Counter[str] = Counter()
        details: list[dict[str, object]] = []

        for index, (question, choices, gold) in enumerate(cases):
            question_ir = compiler.問題IR(question, choices)
            references = tuple(HDS参照検索(provider, question_ir))
            retrieval_empty += int(not references)
            initial_docs += len(references)

            current, current_refs = _current_main_route(
                question_ir, references, compiler=compiler, provider=provider
            )
            v06, session = _v06_route(question_ir, references, compiler=compiler)
            current_final_docs += len(current_refs)

            c_pred = current.回答ラベル
            c_answered = current.状態 == "APPROVE" and c_pred is not None
            c_correct = bool(c_answered and c_pred == gold)
            v_pred = v06.回答ラベル
            v_answered = v06.状態 == "APPROVE" and v_pred is not None
            v_correct = bool(v_answered and v_pred == gold)

            current_correct += int(c_correct)
            current_answered += int(c_answered)
            v06_correct += int(v_correct)
            v06_answered += int(v_answered)
            improved_case = not c_correct and v_correct
            regressed_case = c_correct and not v_correct
            changed_case = current.状態 != v06.状態 or c_pred != v_pred
            improved += int(improved_case)
            regressed += int(regressed_case)
            changed += int(changed_case)
            current_reasons.update(str(x) for x in current.理由)
            v06_reasons.update(str(x) for x in v06.理由)
            snapshot = session.snapshot()
            v06_actions.update(snapshot.作用履歴)

            details.append({
                "index": index,
                "gold": gold,
                "initial_reference_count": len(references),
                "current_final_reference_count": len(current_refs),
                "current_status": current.状態,
                "current_predicted": c_pred,
                "current_correct": c_correct,
                "v06_status": v06.状態,
                "v06_predicted": v_pred,
                "v06_correct": v_correct,
                "v06_cycle": snapshot.cycle,
                "v06_action_history": list(snapshot.作用履歴),
                "improved": improved_case,
                "regressed": regressed_case,
                "changed": changed_case,
            })
            print(
                f"CASE {index + 1:03d}/198 current={current.状態}:{c_pred} "
                f"v06={v06.状態}:{v_pred} gold={gold} "
                f"improved={improved_case} regressed={regressed_case}",
                flush=True,
            )

        total = len(cases)
        current_metric = _metric(current_correct, current_answered, total)
        v06_metric = _metric(v06_correct, v06_answered, total)
        result = {
            "schema": "minidora.gpqa.v06-unified-same-reference-ab.v1",
            "protocol": {
                "benchmark": "GPQA Diamond",
                "dataset": "official idavidrein/gpqa dataset.zip / gpqa_diamond.csv",
                "dataset_zip_sha256": zip_hash,
                "dataset_csv_sha256": csv_hash,
                "choice_shuffle_seed": gpqa.SEED,
                "problem_count": total,
                "initial_reference_rule": "retrieve exactly once per case and pass the same initial Reference tuple to current-main and v0.6 routes",
                "current_route": "current formal MINIDORA choice -> HDS supervisory safety valve when not closed",
                "v06_route": "HDS unified request-local state session -> HDS unified selection evaluation -> HDS/J",
                "gold_boundary": "gold used only after both route outputs for scoring",
                "openalex_enabled": api_key is not None,
                "wikipedia_languages": ["en"],
                "main_modified": False,
                "sandbox_branch_only": True,
            },
            "current_main": current_metric,
            "v06_unified": v06_metric,
            "delta_v06_minus_current": {
                "correct_delta": v06_correct - current_correct,
                "accuracy_points": v06_metric["accuracy_percent"] - current_metric["accuracy_percent"],
                "answered_delta": v06_answered - current_answered,
                "answer_rate_points": v06_metric["answer_rate_percent"] - current_metric["answer_rate_percent"],
                "answered_accuracy_points": v06_metric["answered_accuracy_percent"] - current_metric["answered_accuracy_percent"],
                "changed_cases": changed,
                "improved_cases": improved,
                "regressed_cases": regressed,
                "net_improved_cases": improved - regressed,
            },
            "retrieval": {
                "initial_reference_documents": initial_docs,
                "current_final_reference_documents": current_final_docs,
                "retrieval_empty_cases": retrieval_empty,
            },
            "current_reason_counts": dict(sorted(current_reasons.items())),
            "v06_reason_counts": dict(sorted(v06_reasons.items())),
            "v06_action_counts": dict(sorted(v06_actions.items())),
            "details": details,
        }
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("MINIDORA_V06_AB_RESULT=" + json.dumps({
            "current_main": current_metric,
            "v06_unified": v06_metric,
            "delta": result["delta_v06_minus_current"],
            "retrieval": result["retrieval"],
        }, ensure_ascii=False), flush=True)
        print(f"RESULT_FILE={out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
