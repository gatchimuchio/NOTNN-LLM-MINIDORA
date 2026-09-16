"""旧英字名の互換入口。日本語正本 `評価.py` の公開属性と正本内部フックを再公開する。"""
from 評価 import *  # noqa: F401,F403
from 評価 import _result_payload, main

if __name__ == "__main__":
    raise SystemExit(main())
