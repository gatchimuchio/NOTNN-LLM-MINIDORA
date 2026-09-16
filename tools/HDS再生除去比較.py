from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.HDS再生_eval import HDS再生評価  # noqa: E402


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _要約(結果: dict) -> dict:
    return {
        "total": 結果["total"],
        "correct": 結果["correct"],
        "accuracy_percent": 結果["accuracy_percent"],
        "answered": 結果["answered"],
        "suspended": 結果["suspended"],
        "answer_rate_percent": 結果["answer_rate_percent"],
        "reason_counts": 結果["reason_counts"],
        '計算量_counts': 結果['計算量_counts'],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='同じHDS 再生 bundleで計算量 ablationを実行する。')
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = _load(args.input)
    adaptive = HDS再生評価(rows, 計算量=None)
    low = HDS再生評価(rows, 計算量="low")
    high = HDS再生評価(rows, 計算量="high")
    maximum = HDS再生評価(rows, 計算量="max")
    結果 = {
        "契約形式": 'minidora.hds-選択肢-再生.ablation.v1',
        "adaptive": _要約(adaptive),
        "low": _要約(low),
        "high": _要約(high),
        "max": _要約(maximum),
    }
    text = json.dumps(結果, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
