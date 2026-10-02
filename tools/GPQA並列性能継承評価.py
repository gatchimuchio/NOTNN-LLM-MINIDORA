"""独立問題の分割実測。採否は全数集計で決める。"""
from __future__ import annotations
import argparse
from pathlib import Path
try:
    from .GPQA実測管理 import GPQAを測定
except ImportError:
    from GPQA実測管理 import GPQAを測定


def 引数解析器():
    parser = argparse.ArgumentParser(description="GPQA問題独立並列の分割実行器")
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--started-epoch", type=float)
    parser.add_argument("--deadline-epoch", type=float)
    return parser


def main():
    args = 引数解析器().parse_args()
    if not 0 <= args.start_index < 198 or args.limit <= 0:
        raise SystemExit("開始は0..197、件数は1以上")
    if (args.started_epoch is None) != (args.deadline_epoch is None):
        raise SystemExit("共通開始と締切は対で指定する")
    内容 = GPQAを測定(
        args.out,
        方式="並列",
        開始番号=args.start_index,
        件数=args.limit,
        期限epoch=args.deadline_epoch,
        並列数=1,
        共通開始epoch=args.started_epoch,
    )
    return 0 if 内容.get("実測", {}).get("完走") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
