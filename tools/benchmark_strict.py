from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from benchmark_contract import (
    attach_contract,
    direct_comparison_verdict,
    fixed_replay_contract,
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
    command = [
        sys.executable,
        str(Path(__file__).with_name("benchmark_formal.py")),
        "gpqa-diamond",
        "--controlled-ab",
        "--out",
        str(args.out),
        "--start-index",
        str(args.start_index),
    ]
    if args.limit is not None:
        command += ["--limit", str(args.limit)]
    if args.no_openalex:
        command.append("--no-openalex")
    _run(command)
    payload = json.loads(args.out.read_text(encoding="utf-8"))
    contract = gpqa_e2e_live_contract(payload.get("protocol", {}))
    _write(args.out, attach_contract(payload, contract))
    print("BENCHMARK_ID=" + contract["benchmark_id"])
    print("EVALUATION_CLASS=" + contract["evaluation_class"])
    print("CROSS_RUN_CODE_DELTA_DIRECT=false")
    return 0


def run_fixed_replay(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="minidora-fixed-replay-") as tmp:
        raw = Path(tmp) / "raw.json"
        command = [
            sys.executable,
            str(Path(__file__).with_name("hds_choice_replay_benchmark.py")),
            str(args.input),
            "--out",
            str(raw),
        ]
        if args.effort:
            command += ["--effort", args.effort]
        _run(command)
        payload = json.loads(raw.read_text(encoding="utf-8"))
    contract = fixed_replay_contract(args.input)
    _write(args.out, attach_contract(payload, contract))
    print("BENCHMARK_ID=" + contract["benchmark_id"])
    print("EVALUATION_CLASS=" + contract["evaluation_class"])
    print("INPUT_SNAPSHOT_SHA256=" + contract["input_snapshot_sha256"])
    return 0


def run_compare(args: argparse.Namespace) -> int:
    left = json.loads(args.left.read_text(encoding="utf-8"))
    right = json.loads(args.right.read_text(encoding="utf-8"))
    allowed, reason = direct_comparison_verdict(left, right)
    l_correct, l_total = _score(left)
    r_correct, r_total = _score(right)
    result = {
        "direct_comparison_allowed": allowed,
        "reason": reason,
        "left": {"correct": l_correct, "total": l_total},
        "right": {"correct": r_correct, "total": r_total},
        "correct_delta": (r_correct - l_correct) if allowed and isinstance(l_correct, int) and isinstance(r_correct, int) else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.out:
        _write(args.out, result)
    return 0 if allowed else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="MINIDORA canonical benchmark contract v1 runner")
    sub = root.add_subparsers(dest="mode", required=True)

    e2e = sub.add_parser("gpqa-e2e", help="GPQA汎用E2Eスナップショット。LIVE参照取得を含む")
    e2e.add_argument("--out", type=Path, required=True)
    e2e.add_argument("--start-index", type=int, default=0)
    e2e.add_argument("--limit", type=int)
    e2e.add_argument("--no-openalex", action="store_true")
    e2e.set_defaults(handler=run_gpqa_e2e)

    replay = sub.add_parser("gpqa-fixed-replay", help="固定Replay入力による実装差分測定")
    replay.add_argument("input", type=Path)
    replay.add_argument("--out", type=Path, required=True)
    replay.add_argument("--effort", choices=("low", "high", "max"))
    replay.set_defaults(handler=run_fixed_replay)

    compare = sub.add_parser("compare", help="benchmark contract v1に従って直接比較可否を判定")
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
