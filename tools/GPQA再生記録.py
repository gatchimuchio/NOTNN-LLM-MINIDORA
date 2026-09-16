from __future__ import annotations

'履歴専用: 旧GPQA固定参照再生 記録入口。\n\n2026-09-09以後、GPQA正本性能評価では固定参照資料を禁止する。\n旧実装はGit履歴に保存されており、現行worktreeでは再実行入口を提供しない。\n\n現行GPQA正本:\n    python tools/外部評価_strict.py gpqa-e2e --out gpqa_e2e.json\n'

import sys


GPQA_FIXED_参照_FORBIDDEN = (
    'GPQA_FIXED_参照_FORBIDDEN: 2026-09-09以後、GPQAでは固定参照資料を禁止しています。'
    'この旧記録入口は履歴専用で実行できません。'
)


def main() -> int:
    print(GPQA_FIXED_参照_FORBIDDEN, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
