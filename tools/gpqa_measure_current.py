"""旧英字名の互換入口。日本語正本 `GPQA現行測定.py` の公開属性を再公開する。"""
from GPQA現行測定 import *  # noqa: F401,F403
from GPQA現行測定 import main

if __name__ == "__main__":
    raise SystemExit(main())
