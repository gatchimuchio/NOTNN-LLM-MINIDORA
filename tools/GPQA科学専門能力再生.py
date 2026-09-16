from __future__ import annotations

'履歴専用: 旧GPQA科学専門能力固定再生入口。\n\n2026-09-09以後、GPQAでは保存済み参照・個票・再生 bundleを使う性能測定を禁止する。\n2026-09-02のモジュール 再生実測は履歴証拠として文書とGit履歴に保存するが、\n現行worktreeから同じ固定再生を再実行する入口は提供しない。\n\n科学専門能力を含む診断が必要な場合も、GPQAではLIVE取得のcontrolled A/Bを使う。\n'

import sys


GPQA_FIXED_参照_FORBIDDEN = (
    'GPQA_FIXED_参照_FORBIDDEN: 保存済みGPQA個票を用いるscientific specialist 再生は廃止されました。'
    '固定参照資料を使わずLIVE E2Eで測定してください。'
)


def main() -> int:
    print(GPQA_FIXED_参照_FORBIDDEN, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
