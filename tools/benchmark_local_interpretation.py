from __future__ import annotations

import json
from pathlib import Path

from minidora.hds_compiler_v1 import 公開HDSコンパイラ
from minidora.runtime import ミニドラ, 要求


def has_coreference(ir) -> bool:
    return any(getattr(rel, "種別", None) == "共参照" for rel in getattr(ir, "関係", ()))


def has_unresolved_coreference(ir) -> bool:
    return any(getattr(res, "種別", None) == "未解共参照" for res in getattr(ir, "残差", ()))


def run_case(a: int, b: int, c: int) -> dict:
    retained = ミニドラ(HDSコンパイラ_=公開HDSコンパイラ())
    first = retained.実行(要求(f"{a}+{b}"))
    expected = a + b
    second_query = f"それに{c}を足して"
    second = retained.実行(要求(second_query))

    reset = ミニドラ(HDSコンパイラ_=公開HDSコンパイラ())
    reset_first = reset.実行(要求(f"{a}+{b}"))
    reset.局所解釈を初期化()
    reset_second = reset.実行(要求(second_query))

    retained_origin = second.状態.get("局所解釈起点", {})
    reset_origin = reset_second.状態.get("局所解釈起点", {})

    return {
        "inputs": [a, b, c],
        "first_expected": expected,
        "retained_first_value": first.値,
        "reset_first_value": reset_first.値,
        "retained_origin_value": retained_origin.get("直前結果"),
        "reset_origin_value": reset_origin.get("直前結果"),
        "retained_coreference": has_coreference(second.HDS_IR),
        "reset_coreference": has_coreference(reset_second.HDS_IR),
        "retained_unresolved_coreference": has_unresolved_coreference(second.HDS_IR),
        "reset_unresolved_coreference": has_unresolved_coreference(reset_second.HDS_IR),
        "retained_status": second.採否.状態.value,
        "reset_status": reset_second.採否.状態.value,
        "retained_value": second.値,
        "reset_value": reset_second.値,
        "target_value": expected + c,
        "retained_answer_correct": second.値 == expected + c,
        "reset_answer_correct": reset_second.値 == expected + c,
    }


def main() -> int:
    cases = []
    for i in range(1, 101):
        a = i
        b = (i * 3) % 17 + 1
        c = (i * 5) % 13 + 1
        cases.append(run_case(a, b, c))

    n = len(cases)
    count = lambda key: sum(1 for row in cases if row[key])
    inherited = sum(1 for row in cases if row["retained_origin_value"] == row["first_expected"])
    reset_empty = sum(1 for row in cases if row["reset_origin_value"] is None)

    metrics = {
        "cases": n,
        "state_origin_inheritance": inherited / n,
        "reset_origin_empty": reset_empty / n,
        "coreference_resolved_retained": count("retained_coreference") / n,
        "coreference_resolved_reset": count("reset_coreference") / n,
        "unresolved_coreference_retained": count("retained_unresolved_coreference") / n,
        "unresolved_coreference_reset": count("reset_unresolved_coreference") / n,
        "final_answer_correct_retained": count("retained_answer_correct") / n,
        "final_answer_correct_reset": count("reset_answer_correct") / n,
        "final_answer_improvement": (count("retained_answer_correct") - count("reset_answer_correct")) / n,
    }
    verdict = {
        "local_state_is_preserved": metrics["state_origin_inheritance"] == 1.0,
        "local_state_changes_interpretation": metrics["coreference_resolved_retained"] > metrics["coreference_resolved_reset"],
        "local_state_reaches_final_decision": metrics["final_answer_correct_retained"] > metrics["final_answer_correct_reset"],
    }
    out = {
        "protocol": "MINIDORA local interpretation continuity A/B v1",
        "metrics": metrics,
        "verdict": verdict,
        "cases": cases,
    }
    Path("local_interpretation_benchmark.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps({"metrics": metrics, "verdict": verdict}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
