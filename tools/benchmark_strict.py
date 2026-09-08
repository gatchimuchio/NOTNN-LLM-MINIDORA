from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from benchmark_contract import (
    attach_contract,
    direct_comparison_verdict,
    gpqa_e2e_live_contract,
)


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _score(payload: dict) -> tuple[int | None, int | None]:
    metrics = payload.get("metrics")
    if isinstance(metrics, dict):
        return metrics.get("correct"), metrics.get("selected_total") or metrics.get("completed")
    return payload.get("correct"), payload.get("with_gold") or payload.get("total")


def run_gpqa_e2e(args: argparse.Namespace) -> int:
    # GPQA正本はMINIDORA30を固定した2026-09-09運用条件へ合わせる。
    # 固定するのは評価構成であり、参照結果そのものは毎run新規取得する。
    command = [
        sys.executable,
        str(Path(__file__).with_name("benchmark_formal.py")),
        "gpqa-diamond",
        "--controlled-ab",
        "--no-openalex",
        "--out",
        str(args.out),
    ]
    _run(command)
    payload = json.loads(args.out.read_text(encoding="utf-8"))
    try:
        contract = gpqa_e2e_live_contract(payload.get("protocol", {}))
    except ValueError as exc:
        raise SystemExit(f"GPQA_CANONICAL_PROTOCOL_VIOLATION: {exc}") from exc
    _write(args.out, attach_contract(payload, contract))
    print("BENCHMARK_ID=" + contract["benchmark_id"])
    print("EVALUATION_CLASS=" + contract["evaluation_class"])
    print("RETRIEVAL_MODE=LIVE_ONLY")
    print("FIXED_REFERENCE_DATA_ALLOWED=false")
    print("CROSS_RUN_CODE_DELTA_DIRECT=false")
    return 0


def run_compare(args: argparse.Namespace) -> int:
    left = json.loads(args.left.read_text(encoding="utf-8"))
    right = json.loads(args.right.read_text(encoding="utf-8"))
    allowed, reason = direct_comparison_verdict(left, right)
    l_correct, l_total = _score(left)
    r_correct, r_total = _score(right)
    result = {
        "direct_code_delta_allowed": allowed,
        "reason": reason,
        "left": {"correct": l_correct, "total": l_total},
        "right": {"correct": r_correct, "total": r_total},
        "score_chronology_allowed": True,
        "correct_delta": (r_correct - l_correct) if isinstance(l_correct, int) and isinstance(r_correct, int) else None,
        "correct_delta_is_code_only_causal": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.out:
        _write(args.out, result)
    return 0 if allowed else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="MINIDORA canonical benchmark contract v2 runner")
    sub = root.add_subparsers(dest="mode", required=True)

    e2e = sub.add_parser("gpqa-e2e", help="GPQA正本。198問全数をLIVE参照取得で実行する")
    e2e.add_argument("--out", type=Path, required=True)
    e2e.set_defaults(handler=run_gpqa_e2e)

    compare = sub.add_parser("compare", help="正本E2Eスナップショット間の得点差と因果帰属可否を表示する")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--out", type=Path)
    compare.set_defaults(handler=run_compare)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
