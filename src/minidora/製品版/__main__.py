from __future__ import annotations
import argparse, os
from .製品チャット import 製品ミニドラ
from .監査 import 監査台帳
from .api import serve

def _core():
    try:
        from minidora import ミニドラ
        return ミニドラ()
    except Exception:
        return None

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--serve", action="store_true")
    p.add_argument("--session", default="cli")
    p.add_argument("message", nargs="*")
    a = p.parse_args()
    audit = 監査台帳(os.getenv("MINIDORA_AUDIT_LOG") or None)
    app = 製品ミニドラ(基礎ミニドラ=_core(), 監査台帳_=audit)
    if a.serve: serve(app); return 0
    if a.message:
        r=app.応答(" ".join(a.message), セッションID=a.session); print(r.本文); print(f"trace_id={r.追跡ID}\ntrace_hash={r.監査ハッシュ}"); return 0
    print("MINIDORA Product Chat / exit で終了")
    while True:
        try: text=input("> ").strip()
        except EOFError: return 0
        if text.casefold() in {"exit","quit"}: return 0
        r=app.応答(text,セッションID=a.session); print(r.本文); print(f"[trace:{r.追跡ID}]")
if __name__ == "__main__": raise SystemExit(main())
