from __future__ import annotations

"""Sandbox-only segmented GPQA paired A/B for current main route vs v0.6 unified route."""

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


def _current_route(question_ir, references, *, compiler, provider):
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
    result = HDS統一選択評価(
        question_ir,
        tuple(references),
        コンパイル=compiler.コンパイル,
        模型核=標準能力模型核(),
        統一session=session,
        主体状態=None,
    )
    return result, session.snapshot()


def main() -> int:
    start = int(os.environ["MINIDORA_V06_AB_START"])
    end = int(os.environ["MINIDORA_V06_AB_END"])
    out = Path(os.environ.get("MINIDORA_V06_AB_OUT", f"v06_ab_{start:03d}-{end - 1:03d}.json"))
    if not (0 <= start < end <= 198):
        raise ValueError(f"invalid range {start}:{end}")

    with tempfile.TemporaryDirectory(prefix="minidora-v06-ab-") as td:
        csv_path, zip_hash, csv_hash = gpqa._download_dataset(Path(td))
        all_cases = gpqa._load_cases(csv_path)
        if len(all_cases) != 198:
            raise RuntimeError(f"GPQA Diamond expected 198 rows, got {len(all_cases)}")
        cases = all_cases[start:end]

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
        initial_docs = current_final_docs = retrieval_empty = 0
        details: list[dict[str, object]] = []

        for index, (question, choices, gold) in enumerate(cases, start=start):
            question_ir = compiler.問題IR(question, choices)
            references = tuple(HDS参照検索(provider, question_ir))
            initial_docs += len(references)
            retrieval_empty += int(not references)

            current, current_refs = _current_route(question_ir, references, compiler=compiler, provider=provider)
            v06, snapshot = _v06_route(question_ir, references, compiler=compiler)
            current_final_docs += len(current_refs)

            c_pred = current.回答ラベル
            c_answered_case = current.状態 == "APPROVE" and c_pred is not None
            c_correct_case = bool(c_answered_case and c_pred == gold)
            v_pred = v06.回答ラベル
            v_answered_case = v06.状態 == "APPROVE" and v_pred is not None
            v_correct_case = bool(v_answered_case and v_pred == gold)

            current_correct += int(c_correct_case)
            current_answered += int(c_answered_case)
            v06_correct += int(v_correct_case)
            v06_answered += int(v_answered_case)
            improved_case = not c_correct_case and v_correct_case
            regressed_case = c_correct_case and not v_correct_case
            changed_case = current.状態 != v06.状態 or c_pred != v_pred
            improved += int(improved_case)
            regressed += int(regressed_case)
            changed += int(changed_case)

            details.append({
                "index": index,
                "gold": gold,
                "initial_reference_count": len(references),
                "current_final_reference_count": len(current_refs),
                "current_status": current.状態,
                "current_predicted": c_pred,
                "current_correct": c_correct_case,
                "v06_status": v06.状態,
                "v06_predicted": v_pred,
                "v06_correct": v_correct_case,
                "v06_cycle": snapshot.cycle,
                "v06_action_history": list(snapshot.作用履歴),
                "improved": improved_case,
                "regressed": regressed_case,
                "changed": changed_case,
            })
            print(
                f"CASE {index + 1:03d}/198 current={current.状態}:{c_pred} "
                f"v06={v06.状態}:{v_pred} gold={gold} improved={improved_case} regressed={regressed_case}",
                flush=True,
            )

        total = end - start
        current_metric = _metric(current_correct, current_answered, total)
        v06_metric = _metric(v06_correct, v06_answered, total)
        payload = {
            "schema": "minidora.gpqa.v06-unified-same-reference-ab.segment.v1",
            "protocol": {
                "benchmark": "GPQA Diamond",
                "dataset_zip_sha256": zip_hash,
                "dataset_csv_sha256": csv_hash,
                "choice_shuffle_seed": gpqa.SEED,
                "selected_start": start,
                "selected_end_exclusive": end,
                "initial_reference_rule": "retrieve exactly once per case and share the same initial Reference tuple",
                "current_route": "current formal MINIDORA choice then current HDS supervisory safety valve when not closed",
                "v06_route": "HDS unified request-local state session -> unified selection evaluation -> HDS/J",
                "gold_boundary": "gold used only after both outputs for scoring",
                "openalex_enabled": api_key is not None,
                "main_modified": False,
                "sandbox_branch_only": True,
            },
            "current_main": current_metric,
            "v06_unified": v06_metric,
            "delta": {
                "correct_delta": v06_correct - current_correct,
                "answered_delta": v06_answered - current_answered,
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
            "details": details,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("SEGMENT_RESULT=" + json.dumps({"range": [start, end], "current": current_metric, "v06": v06_metric, "delta": payload["delta"]}, ensure_ascii=False), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
