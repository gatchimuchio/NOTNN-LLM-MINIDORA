"""旧英字名の互換入口。日本語正本 `評価.py` の公開属性と旧内部フック名を再公開する。"""
from 評価 import *  # noqa: F401,F403
from 評価 import _結果構造, main

_result_payload = _結果構造

if __name__ == "__main__":
    raise SystemExit(main())
