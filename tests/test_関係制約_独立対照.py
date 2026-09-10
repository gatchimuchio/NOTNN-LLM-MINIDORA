"""実装のグラフ閉包を使わず、変数消去と非等式の分岐で有理数制約を対照する。"""
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
import random
import unittest
from minidora.関係制約 import 関係式, 関係問題, 関係制約器


def 独立可解(rows):
    variables=('A','B','C')
    exclusions=[r for r in rows if r.比較=='不一致']
    for choices in product(('未満','超'),repeat=len(exclusions)):
        choice=iter(choices)
        inequalities=[]
        for r in rows:
            op=next(choice) if r.比較=='不一致' else r.比較
            vector=[F(0)]*3
            vector[variables.index(r.左項)]+=1
            vector[variables.index(r.右項)]-=1
            bound=F(r.差)
            if op in ('一致','以下','未満'):
                inequalities.append((tuple(vector),bound,op=='未満'))
            if op in ('一致','以上','超'):
                inequalities.append((tuple(-x for x in vector),-bound,op=='超'))
        feasible=True
        for column in (2,1,0):
            positive=[r for r in inequalities if r[0][column]>0]
            negative=[r for r in inequalities if r[0][column]<0]
            new=[r for r in inequalities if r[0][column]==0]
            for a,b in product(positive,negative):
                pa,nb=a[0][column],-b[0][column]
                new.append((tuple(x/pa+y/nb for x,y in zip(a[0],b[0])),a[1]/pa+b[1]/nb,a[2] or b[2]))
            inequalities=new
            if any(not any(v) and (bound<0 or bound==0 and strict) for v,bound,strict in inequalities):
                feasible=False
                break
        if feasible:
            return True
    return False


class 差分独立対照試験(unittest.TestCase):
    def test_独立消去法との有理数差分対照(self):
        # 乱数は試験入力生成だけ。実行結果の選択には使わない。
        generator=random.Random(20260910)
        ops=('一致','不一致','以下','未満','以上','超')
        opposite={'一致':'不一致','不一致':'一致','以下':'超','未満':'以上','以上':'未満','超':'以下'}
        numbers=('-2','-1','0','1','2','1/3','-1/2','0.1')
        for index in range(160):
            facts=tuple(関係式('f'+str(i),generator.choice('ABC'),generator.choice(ops),generator.choice('ABC'),generator.choice(numbers)) for i in range(4))
            qs=tuple(関係式('q'+str(i),'A',op,'C',generator.choice(numbers)) for i,op in enumerate(ops))
            result=関係制約器().実行(関係問題(tuple('ABC'),facts,qs))
            self.assertTrue(result.成立,result.保留理由)
            feasible=独立可解(facts)
            self.assertEqual(result.データ['前提整合'],feasible,index)
            for q,answer in zip(qs,result.データ['回答']):
                if not feasible:
                    expected='前提矛盾'
                elif not 独立可解(facts+(replace(q,比較=opposite[q.比較]),)):
                    expected='導出'
                elif not 独立可解(facts+(q,)):
                    expected='反証'
                else:
                    expected='未確定'
                self.assertEqual(answer['判定'],expected,(index,facts,q))


if __name__=='__main__':
    unittest.main()
