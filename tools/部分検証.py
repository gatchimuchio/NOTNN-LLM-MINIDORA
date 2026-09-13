"""取得済み原本と第22・23バッチ差分の部分試験。全製品回帰の代替ではない。"""
from pathlib import Path
import sys
import unittest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
sys.path.insert(0,str(root/'tools'))
from minidora.標準入出力 import 標準入出力をUTF8にする
if __name__=='__main__':
    標準入出力をUTF8にする()
    print('対象：取得済み部分ソース。Windows・全製品・LIVE Webは別途未検証。',flush=True)
    suite=unittest.defaultTestLoader.discover(str(root/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
