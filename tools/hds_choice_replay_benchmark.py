from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.hds_data_k import HDSIR知識Adapter  # noqa: E402
from minidora.hds_replay import HDSIR復元  # noqa: E402
from minidora.k3_functional import K3相当能力核  # noqa: E402
from minidora.k3_hds_native import HDSIRネイティブAdapter  # noqa: E402


SCHEMA = "minidora.hds-choice-replay.v1"


def _load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("schema") not in {None, SCHEMA}:
            raise ValueError(f"line {line_no}: unsupported schema {row.get('schema')!r}")
        rows.append(row)
    return rows


def _run_case(row: dict[str, Any], *, effort: str | None) -> tuple[dict[str, Any], str | None]:
    # goldはmodel inputから先に分離する。以下のpayloadだけがMINIDORAへ渡る。
    payload = dict(row)
    gold = payload.pop("gold", None)
    case_id = str(payload.get("id", ""))

    question = HDSIR復元(payload["question_ir"])
    choices = {
        str(label): HDSIR復元(ir_data)
        for label, ir_data in dict(payload.get("choices_ir", {})).items()
    }

    core = K3相当能力核()
    ingest = HDSIR知識Adapter(core)
    data_fact_count = 0
    evidence_fact_count = 0
    for item in payload.get("data", ()):
        ir = HDSIR復元(item["ir"])
        provenance = tuple(str(x) for x in item.get("provenance", ()))
        result = ingest.投入(ir, provenance=provenance)
        data_fact_count += result.追加事実数
        evidence_fact_count += result.証拠事実数

    result = HDSIRネイティブAdapter(core).実行(question, 候補IR=choices, 努力=effort)
    candidate_rows = [
        {
            "answer": candidate.answer,
            "confidence": candidate.confidence,
            "expert": candidate.expert,
            "proof_fact_count": len(candidate.proof_fact_ids),
            "provenance": list(candidate.provenance),
        }
        for candidate in result.候補
    ]
    confidence_margin = None
    if candidate_rows:
        ordered = sorted((row["confidence"] for row in candidate_rows), reverse=True)
        confidence_margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]

    detail = {
        "id": case_id,
        "status": result.状態,
        "predicted": result.回答ラベル,
        "correct": (result.回答ラベル == gold) if gold is not None else None,
        "reasons": list(result.理由),
        "effort": result.努力水準,
        "graph_depth_limit": result.探索深さ上限,
        "evidence_limit": result.証拠上限,
        "proof_fact_count": result.根拠事実数,
        "k_facts_added": data_fact_count,
        "evidence_facts": evidence_fact_count,
        "candidate_confidence_margin": confidence_margin,
        "candidates": candidate_rows,
    }
    return detail, (str(gold) if gold is not None else None)


def run(path: Path, *, effort: str | None = None) -> dict[str, Any]:
    rows = _load(path)
    details: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    effort_counts: Counter[str] = Counter()
    total_with_gold = 0
    correct = 0
    answered = 0
    suspended = 0

    for row in rows:
        detail, gold = _run_case(row, effort=effort)
        details.append(detail)
        effort_counts[detail["effort"]] += 1
        reason_counts.update(detail["reasons"])
        if detail["status"] == "APPROVE" and detail["predicted"] is not None:
            answered += 1
        else:
            suspended += 1
        if gold is not None:
            total_with_gold += 1
            if detail["correct"]:
                correct += 1

    total = len(details)
    summary = {
        "schema": "minidora.hds-choice-replay.result.v1",
        "input": str(path),
        "total": total,
        "with_gold": total_with_gold,
        "correct": correct if total_with_gold else None,
        "accuracy_percent": (100.0 * correct / total_with_gold) if total_with_gold else None,
        "answered": answered,
        "suspended": suspended,
        "answer_rate_percent": (100.0 * answered / total) if total else 0.0,
        "effort_override": effort,
        "effort_counts": dict(sorted(effort_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "details": details,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="固定済みHDS-IRだけでMINIDORA choice reasoningを再評価する。"
    )
    parser.add_argument("input", type=Path, help="minidora.hds-choice-replay.v1 JSONL")
    parser.add_argument("--out", type=Path, help="結果JSON保存先")
    parser.add_argument("--effort", choices=("low", "high", "max"), help="effortを固定してablationする")
    args = parser.parse_args()

    result = run(args.input, effort=args.effort)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
