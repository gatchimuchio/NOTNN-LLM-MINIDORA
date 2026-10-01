from __future__ import annotations
import time, unittest
from minidora.HDS駆動コア import HDS駆動コア
from minidora.HDS実行主体 import HDS関数作用,HDS作用結果,HDS作用状態,HDS終端
class 目的駆動198連続試験(unittest.TestCase):
    def test_同一中核198要求で無関係学習を実行せず完走(self):
        中核=HDS駆動コア(最大作用回数=8); noise=[]; start=time.perf_counter()
        for i in range(198):
            goal=f"回答完了:{i}"
            r=中核.実行(f"synthetic-{i}",目的=("現在要求へ回答する",),要求状態=(goal,),追加作用=(HDS関数作用("回答",lambda _s,goal=goal:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({goal})),出力状態=(goal,),優先度=1),HDS関数作用("学習だけ",lambda _s,i=i:(noise.append(i) or HDS作用結果(HDS作用状態.成立,主体状態差分=((f"学習:{i}",True),))),優先度=100)))
            self.assertEqual(r.終端,HDS終端.採用,(i,r.理由))
        self.assertEqual(noise,[]); self.assertLess(time.perf_counter()-start,3.0)
    def test_答えへ接続しない学習しかない198要求は即時保留(self):
        中核=HDS駆動コア(最大作用回数=40); calls=[]; start=time.perf_counter()
        for i in range(198):
            goal=f"未到達:{i}"; r=中核.実行(f"unsolved-{i}",目的=("現在要求へ回答する",),要求状態=(goal,),追加作用=(HDS関数作用("学習だけ",lambda _s,i=i:(calls.append(i) or HDS作用結果(HDS作用状態.成立,主体状態差分=((f"内部:{i}",True),))),優先度=100),))
            self.assertEqual(r.終端,HDS終端.保留); self.assertEqual(r.計装.作用実行数,0)
        self.assertEqual(calls,[]); self.assertLess(time.perf_counter()-start,3.0)
