from __future__ import annotations

import argparse
import os

from minidora import ミニドラ
from .ガバナンス import JSONL監査保存先, 監査台帳
from .チャット import ハッカソンチャット


def _監査台帳() -> 監査台帳:
    path = os.getenv("MINIDORA_AUDIT_LOG", "").strip()
    return 監査台帳(JSONL監査保存先(path)) if path else 監査台帳()


def main() -> int:
    parser = argparse.ArgumentParser(description="MINIDORA Hackathon chat")
    parser.add_argument("message", nargs="*")
    parser.add_argument("--session", default="cli")
    args = parser.parse_args()
    chat = ハッカソンチャット(基礎ミニドラ=ミニドラ(), 監査台帳_=_監査台帳())

    if args.message:
        result = chat.応答(" ".join(args.message), セッションID=args.session)
        print(result.本文)
        print(f"\ntrace_id={result.追跡ID}\ntrace_hash={result.監査ハッシュ}")
        return 0

    print("MINIDORA Hackathon Chat / exit で終了")
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            return 0
        if text.casefold() in {"exit", "quit"}:
            return 0
        result = chat.応答(text, セッションID=args.session)
        print(result.本文)
        print(f"[trace:{result.追跡ID} hash:{result.監査ハッシュ}]")


if __name__ == "__main__":
    raise SystemExit(main())
