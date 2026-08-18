#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from minidora_k3.挙動変換 import load_probes, compile_behavior_probes, dump_templates


def main() -> int:
    parser = argparse.ArgumentParser(description="K3の観測I/O試験を日本語命令雛形へ変換する")
    parser.add_argument("入力", type=Path, help="挙動試験JSON。各行ではなくroot list")
    parser.add_argument("--出力", "--output", dest="出力", type=Path, default=Path("台帳/挙動命令雛形.json"))
    args = parser.parse_args()

    probes = load_probes(args.入力)
    templates = compile_behavior_probes(probes)
    dump_templates(args.出力, templates)
    print(f"挙動試験数: {len(probes)}")
    print(f"命令雛形数: {len(templates)}")
    print(f"出力: {args.出力}")
    print("注意: 十分なheld-out・摂動・反実仮想検証前はK3意味同等と扱わない")
    return 0 if probes and templates else 2


if __name__ == "__main__":
    raise SystemExit(main())
