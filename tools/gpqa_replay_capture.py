from __future__ import annotations

"""履歴専用: 旧GPQA固定参照Replay capture入口。

2026-09-09以後、GPQA正本性能評価では固定参照Dataを禁止する。
旧実装はGit履歴に保存されており、現行worktreeでは再実行入口を提供しない。

現行GPQA正本:
    python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
"""

import sys


GPQA_FIXED_REFERENCE_FORBIDDEN = (
    "GPQA_FIXED_REFERENCE_FORBIDDEN: 2026-09-09以後、GPQAでは固定参照Dataを禁止しています。"
    "この旧capture入口は履歴専用で実行できません。"
)


def main() -> int:
    print(GPQA_FIXED_REFERENCE_FORBIDDEN, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
