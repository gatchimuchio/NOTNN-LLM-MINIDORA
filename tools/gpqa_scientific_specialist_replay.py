from __future__ import annotations

"""履歴専用: 旧GPQA科学専門能力固定Replay入口。

2026-09-09以後、GPQAでは保存済み参照・個票・Replay bundleを使う性能測定を禁止する。
2026-09-02のModule replay実測は履歴証拠として文書とGit履歴に保存するが、
現行worktreeから同じ固定Replayを再実行する入口は提供しない。

科学専門能力を含む診断が必要な場合も、GPQAではLIVE取得のcontrolled A/Bを使う。
"""

import sys


GPQA_FIXED_REFERENCE_FORBIDDEN = (
    "GPQA_FIXED_REFERENCE_FORBIDDEN: 保存済みGPQA個票を用いるscientific specialist replayは廃止されました。"
    "固定参照Dataを使わずLIVE E2Eで測定してください。"
)


def main() -> int:
    print(GPQA_FIXED_REFERENCE_FORBIDDEN, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
