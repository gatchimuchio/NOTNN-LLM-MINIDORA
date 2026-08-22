from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .hds_compiler import 公開HDSコンパイラ
from .runtime import ミニドラ, 要求


def _標準入出力をUTF8化() -> None:
    """日本語基底CLIの標準入出力をOSロケールから分離する。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


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


def _標準ミニドラ() -> ミニドラ:
    """公開HDS Compilerを正規入口として接続した標準CLI Runtimeを返す。"""
    return ミニドラ(HDSコンパイラ_=公開HDSコンパイラ())


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
            "compiler": "公開HDSコンパイラ",
        }
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return
    print(body.応答(query))


def main(argv: Sequence[str] | None = None) -> int:
    _標準入出力をUTF8化()
    args = _parser().parse_args(argv)
    body = _標準ミニドラ()

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
