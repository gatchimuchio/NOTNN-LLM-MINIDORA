"""日本語基底の道具が出す文字列を、OSロケールから分離する。"""
from __future__ import annotations

import sys


def 標準出力をUTF8化() -> None:
    """実行入口からだけ呼び、埋め込み先の文字列捕捉器は変更しない。"""
    for 出力先 in (sys.stdout, sys.stderr):
        再設定 = getattr(出力先, "reconfigure", None)
        if callable(再設定):
            再設定(encoding="utf-8", errors="strict")
