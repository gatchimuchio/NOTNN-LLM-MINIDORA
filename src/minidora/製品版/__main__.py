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
    import sys
    from ..標準入出力 import 標準入出力をUTF8にする
    標準入出力をUTF8にする()
    p = argparse.ArgumentParser()
    p.add_argument("--serve", action="store_true")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--汎用", action="store_true", help="目的・複数資料・確認継続の会話入口だけを利用")
    mode.add_argument("--従来", action="store_true", help="従来Module専用入口。省略時は単一の自動入口")
    p.add_argument("--外部読取", action="store_true", help="汎用入口で要求された公開資料取得を許可")
    p.add_argument("--session", default="cli")
    p.add_argument("message", nargs="*")
    a = p.parse_args()
    if a.汎用:
        for stream in (sys.stdin,sys.stdout,sys.stderr):
            if hasattr(stream,"reconfigure"):
                stream.reconfigure(encoding="utf-8",errors="strict")
    audit = 監査台帳(os.getenv("MINIDORA_AUDIT_LOG") or None)
    if a.外部読取 and a.従来:
        p.error("--外部読取は--従来と併用できません")
    app = 製品ミニドラ(基礎ミニドラ=None if a.汎用 else _core(), 監査台帳_=audit,
                      汎用会話=True if a.汎用 else False if a.従来 else None, 汎用外部読取許可=a.外部読取)
    if a.serve:
        if not a.従来: serve(app, host="127.0.0.1", 同一生成元限定=True)
        else: serve(app)
        return 0
    if a.message:
        r=app.応答(" ".join(a.message), セッションID=a.session); print(r.本文); print(f"trace_id={r.追跡ID}\ntrace_hash={r.監査ハッシュ}"); return 0
    print("MINIDORA Product Chat / exit で終了")
    while True:
        try: text=input("> ").strip()
        except EOFError: return 0
        except UnicodeError:
            print("標準入力はUTF-8で指定してください。", file=sys.stderr)
            return 2
        if text.casefold() in {"exit","quit"}: return 0
        r=app.応答(text,セッションID=a.session); print(r.本文); print(f"[trace:{r.追跡ID}]")
if __name__ == "__main__": raise SystemExit(main())
