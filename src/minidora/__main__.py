from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .runtime import ミニドラ, 要求


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="minidora",
        description="MINIDORA v0.3 非ニューラルネットワークLLM Runtime",
    )
    parser.add_argument("query", nargs="?", help="MINIDORAへ渡す自然言語入力")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="値・採否・理由・計画をJSONで出力する",
    )
    return parser


def _run_once(body: ミニドラ, query: str, *, json_mode: bool) -> None:
    if json_mode:
        result = body.実行(要求(query))
        payload = {
            "query": query,
            "value": result.値,
            "status": result.採否.状態.value,
            "reasons": list(result.採否.理由),
            "plan": result.言語計画,
            "reference_count": len(result.参照),
            "hds_ir": result.HDS_IR is not None,
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return
    print(body.応答(query))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    body = ミニドラ()

    if args.query is not None:
        query = args.query.strip()
        if not query:
            raise SystemExit("入力が空です。")
        _run_once(body, query, json_mode=args.json_mode)
        return 0

    try:
        while True:
            query = input("MINIDORA> ").strip()
            if not query:
                continue
            _run_once(body, query, json_mode=args.json_mode)
    except (EOFError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
