from __future__ import annotations
import argparse
import json
from pathlib import Path
from .実行系 import ミニドラK3
from .型 import 計算量
from .日本語化 import 日本語辞書

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minidora-k3", description="K3公開構造を日本語命令へ射影したミニドラ非ニューラル実行系")
    parser.add_argument("本文")
    parser.add_argument("--参照庫", "--reference-dir", dest="参照庫", type=Path, help="外部参照資料庫。省略時は同梱標準資料")
    parser.add_argument("--計算量", "--effort", dest="計算量", choices=[row.value for row in 計算量], default=計算量.最大.value)
    parser.add_argument("--履歴", "--trace", dest="履歴", action="store_true")
    args = parser.parse_args(argv)
    runtime = ミニドラK3.参照庫から構築(args.参照庫) if args.参照庫 else ミニドラK3.内蔵参照から構築()
    result = runtime.実行(args.本文, 計算量=計算量(args.計算量))
    payload = 日本語辞書(result)
    if not args.履歴:
        payload.pop("履歴", None)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if result.status == result.status.合格 else 2

if __name__ == "__main__":
    raise SystemExit(main())
