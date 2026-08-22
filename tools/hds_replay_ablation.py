from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.hds_replay_eval import HDSReplay評価  # noqa: E402


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _summary(result: dict) -> dict:
    return {
        "total": result["total"],
        "correct": result["correct"],
        "accuracy_percent": result["accuracy_percent"],
        "answered": result["answered"],
        "suspended": result["suspended"],
        "answer_rate_percent": result["answer_rate_percent"],
        "reason_counts": result["reason_counts"],
        "effort_counts": result["effort_counts"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="同じHDS Replay bundleでeffort ablationを実行する。")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = _load(args.input)
    adaptive = HDSReplay評価(rows, effort=None)
    low = HDSReplay評価(rows, effort="low")
    high = HDSReplay評価(rows, effort="high")
    maximum = HDSReplay評価(rows, effort="max")
    result = {
        "schema": "minidora.hds-choice-replay.ablation.v1",
        "adaptive": _summary(adaptive),
        "low": _summary(low),
        "high": _summary(high),
        "max": _summary(maximum),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
