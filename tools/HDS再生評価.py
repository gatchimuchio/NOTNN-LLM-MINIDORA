from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from minidora.HDS再生評価 import HDS再生評価  # noqa: E402


SCHEMA = 'minidora.hds-選択肢-再生.v1'


def _load(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("契約形式") not in {None, SCHEMA}:
            raise ValueError(f"line {line_no}: unsupported schema {row.get('契約形式')!r}")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description='固定HDS-IR bundleをMINIDORA 実行系で再評価する。')
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--effort", choices=("low", "high", "max"))
    args = parser.parse_args()

    結果 = HDS再生評価(_load(args.input), 計算量=args.effort)
    text = json.dumps(結果, ensure_ascii=False, indent=2)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
