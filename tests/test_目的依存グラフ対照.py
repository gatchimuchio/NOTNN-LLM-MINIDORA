from __future__ import annotations
import random, unittest
from minidora.HDS実行主体 import HDS実行主体,HDS実行状態,HDS関数作用,HDS作用結果,HDS作用状態,HDS終端
class 目的依存グラフ対照試験(unittest.TestCase):
    def test_80乱数グラフで目的逆算経路外を実行しない(self):
        rng=random.Random(20261001)
        for case in range(80):
            n=rng.randint(2,7); states=[f"c{case}:{i}" for i in range(n+1)]; goal=states[-1]; actions=[]
            for i in range(n):
                out=states[i+1]; inp=(states[i],) if i else ()
                actions.append(HDS関数作用(f"goal:{case}:{i}",lambda _s,out=out:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({out})),入力状態=inp,出力状態=(out,)))
            for j in range(rng.randint(4,12)):
                out=f"noise:{case}:{j}"; actions.append(HDS関数作用(f"noise:{case}:{j}",lambda _s,out=out:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({out})),出力状態=(out,),優先度=1000+j))
            rng.shuffle(actions); r=HDS実行主体(tuple(actions),最大作用回数=32).実行(HDS実行状態(目的=(f"case-{case}",),要求状態=frozenset({goal})))
            self.assertEqual(r.終端,HDS終端.採用,(case,r.理由)); used=[x.作用ID for x in r.履歴 if x.作用ID!="内的/経験形成"]; self.assertTrue(all(x.startswith(f"goal:{case}:") for x in used),(case,used))
    def test_80到達不能グラフは無関係作用を一度も実行しない(self):
        rng=random.Random(20261002)
        for case in range(80):
            actions=tuple(HDS関数作用(f"noise:{case}:{j}",lambda _s,j=j:HDS作用結果(HDS作用状態.成立,追加状態=frozenset({f"n:{j}"})),出力状態=(f"n:{j}",),優先度=100+j) for j in range(rng.randint(3,15)))
            r=HDS実行主体(actions,max作用回数=40) if False else HDS実行主体(actions,最大作用回数=40)
            out=r.実行(HDS実行状態(目的=(f"u-{case}",),要求状態=frozenset({f"goal:{case}"})))
            self.assertEqual(out.終端,HDS終端.保留); self.assertEqual(out.履歴,()); self.assertEqual(out.計装.作用実行数,0)
