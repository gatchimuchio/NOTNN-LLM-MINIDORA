"""連立一次方程式の区分・解の完全性と、独立な行列式による対照。"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
import unittest

from minidora.線形方程式 import 線形を解く
from minidora.記号演算 import 数学記録整合


def eq(left,right):
    return {'左辺':left,'右辺':right}


class 線形方程式試験(unittest.TestCase):
    def solve(self, *equations, names=('x','y')):
        result=線形を解く(names,equations)
        self.assertTrue(result.成立,(result.保留理由,result.データ))
        self.assertTrue(数学記録整合(result))
        return result

    def test_連立一次方程式の一意解(self):
        result=self.solve(eq('x+y','5'),eq('x-y','1'))
        self.assertEqual(result.データ['判定'],'一意解')
        self.assertEqual(result.データ['解'],{'x':'3','y':'2'})

    def test_入力係数変更が解へ到達(self):
        for n in (9,731,10007):
            result=self.solve(eq('x+y',str(n)),eq('x-y','1'))
            self.assertEqual(F(result.データ['解']['x']),(F(n)+1)/2)

    def test_有理数と十進数の正確な解(self):
        result=self.solve(eq('0.1*x+0.2*y','0.3'),eq('x-y','0'))
        self.assertEqual(result.データ['解'],{'x':'1','y':'1'})

    def test_先頭零の行交換(self):
        result=self.solve(eq('y','2'),eq('x','3'))
        self.assertEqual(result.データ['解'],{'x':'3','y':'2'})
        self.assertTrue(any(x['操作']=='交換' for x in result.データ['行操作']))

    def test_条件不足では自由変数を勝手に固定しない(self):
        result=self.solve(eq('x+y','5'))
        self.assertEqual(result.データ['判定'],'自由解')
        self.assertIsNone(result.データ['解'])
        self.assertEqual(result.データ['自由変数'],['y'])
        self.assertEqual(result.データ['特解'],{'x':'5','y':'0'})
        self.assertEqual(result.データ['基底'][0]['係数'],{'x':'-1','y':'1'})

    def test_自由変数を含む族を元式に独立代入(self):
        result=self.solve(eq('x+2*y-z','3'),names=('x','y','z'))
        self.assertEqual(result.データ['判定'],'自由解')
        for s,t in product((F(-2),F(1,3),F(7)),repeat=2):
            values={name:F(v) for name,v in result.データ['特解'].items()}
            for parameter,basis in zip((s,t),result.データ['基底']):
                for name,v in basis['係数'].items():
                    values[name]+=parameter*F(v)
            self.assertEqual(values['x']+2*values['y']-values['z'],3)

    def test_冗長行を矛盾にしない(self):
        result=self.solve(eq('x+y','5'),eq('2*x+2*y','10'))
        self.assertEqual(result.データ['判定'],'自由解')
        self.assertEqual(result.データ['階数'],1)

    def test_矛盾を解なしとして保存(self):
        result=self.solve(eq('x+y','5'),eq('2*x+2*y','11'))
        self.assertEqual(result.データ['判定'],'解なし')
        proof=result.データ['矛盾証明']
        self.assertEqual(proof['導出左辺'],['0','0'])
        self.assertNotEqual(F(proof['導出右辺']),0)

    def test_矛盾証明を元の行から独立に再現(self):
        result=self.solve(eq('x+y','5'),eq('x-y','1'),eq('2*x','7'))
        weights=list(map(F,result.データ['矛盾証明']['元方程式の係数']))
        rows=[[F(x) for x in r] for r in result.データ['元拡大行列']]
        combined=[sum((w*r[i] for w,r in zip(weights,rows)),F(0)) for i in range(3)]
        self.assertEqual(combined[:2],[F(0),F(0)])
        self.assertNotEqual(combined[-1],0)

    def test_零方程式と空方程式集合(self):
        for equations in ((),(eq('0','0'),)):
            result=self.solve(*equations)
            self.assertEqual(result.データ['判定'],'自由解')
            self.assertEqual(result.データ['自由変数'],['x','y'])
            self.assertEqual(len(result.データ['基底']),2)

    def test_定数矛盾の検出(self):
        result=self.solve(eq('0','1'))
        self.assertEqual(result.データ['判定'],'解なし')

    def test_多項式の厳密相殺後に線形なら解く(self):
        result=self.solve(eq('x*x-x*x+x','3'),eq('y','2'))
        self.assertEqual(result.データ['解'],{'x':'3','y':'2'})

    def test_非線形変数分母不等号を別問題に変換しない(self):
        for equation in (eq('x*y','1'),eq('1/x','2'),eq('x<y','0')):
            result=線形を解く(('x','y'),(equation,))
            self.assertFalse(result.成立)
            self.assertNotIn('判定',result.データ)

    def test_余分な条件や不正な配列型を捨てない(self):
        for equations in ([eq('x','1')],({'左辺':'x','右辺':'1','整数':True},),(None,)):
            self.assertFalse(線形を解く(('x',),equations).成立)

    def test_変数がなければ線形問題として受けない(self):
        self.assertFalse(線形を解く((),()).成立)

    def test_過剰決定系の一致と不一致(self):
        ok=self.solve(eq('x','3'),eq('y','2'),eq('x+y','5'))
        bad=self.solve(eq('x','3'),eq('y','2'),eq('x+y','6'))
        self.assertEqual((ok.データ['判定'],bad.データ['判定']),('一意解','解なし'))

    def test_行順と変数順を変えても解は同じ(self):
        a=self.solve(eq('x+y','5'),eq('x-y','1'))
        b=self.solve(eq('x-y','1'),eq('x+y','5'),names=('y','x'))
        self.assertEqual(a.データ['解'],b.データ['解'])

    def test_表示用の特解を一意解に偽装すると検出(self):
        result=self.solve(eq('x+y','5'))
        result.データ['判定']='一意解'
        result.データ['解']=result.データ['特解']
        self.assertFalse(数学記録整合(result))

    def test_証明行列改変を検出(self):
        result=self.solve(eq('x+y','5'),eq('x-y','1'))
        result.データ['行変換行列'][0][0]='999'
        self.assertFalse(数学記録整合(result))

    def test_入力と結果の分離(self):
        equations=(eq('x+y','5'),)
        before=deepcopy(equations)
        result=線形を解く(('x','y'),equations)
        result.データ['入力']['方程式'][0]['右辺']='999'
        self.assertEqual(equations,before)

    def test_予算と停止は解なしに読み替えない(self):
        for options in ({'最大演算数':1},{'停止要求':lambda:True},{'停止要求':lambda:1/0}):
            result=線形を解く(('x','y'),(eq('x+y','5'),eq('x-y','1')),**options)
            self.assertFalse(result.成立)
            self.assertNotIn('判定',result.データ)

    def test_方程式上限は剪定しない(self):
        self.assertFalse(線形を解く(('x',),(eq('x','1'),)*17).成立)


class 線形独立対照試験(unittest.TestCase):
    def test_二元系の行列式とクラメル則で対照(self):
        count=0
        for a,b,c,d in product((-1,0,1),repeat=4):
            for u,v in ((0,0),(1,2),(-2,3)):
                r=線形を解く(('x','y'),(eq(f'{a}*x+{b}*y',str(u)),eq(f'{c}*x+{d}*y',str(v))))
                self.assertTrue(r.成立,r.データ)
                det=a*d-b*c
                if det:
                    self.assertEqual(r.データ['判定'],'一意解')
                    self.assertEqual(F(r.データ['解']['x']),F(u*d-b*v,det))
                    self.assertEqual(F(r.データ['解']['y']),F(a*v-u*c,det))
                else:
                    # rank(A)=0の場合を別扱い。それ以外は拡大行列の2次小行列を検査。
                    impossible=(u!=0 or v!=0) if not any((a,b,c,d)) else (a*v-u*c!=0 or b*v-u*d!=0)
                    self.assertEqual(r.データ['判定'],'解なし' if impossible else '自由解')
                count+=1
        self.assertEqual(count,243)

    def test_有理三元系は別の行列式展開で対照(self):
        from itertools import permutations
        def det(a):
            total=F(0)
            for p in permutations(range(3)):
                inversions=sum(p[i]>p[j] for i in range(3) for j in range(i+1,3))
                value=F((-1)**inversions)
                for i in range(3):value*=a[i][p[i]]
                total+=value
            return total
        count=0
        for t in range(-4,5):
            a=[[F(1),F(1,3),F(t)],[F(0),F(2),F(1,2)],[F(1),F(-1),F(2)]]
            b=[F(t,3),F(1),F(-2)]
            determinant=det(a)
            if not determinant:continue
            equations=tuple(eq('+'.join(f'({x})*{n}' for x,n in zip(row,('x','y','z'))),str(rhs)) for row,rhs in zip(a,b))
            result=線形を解く(('x','y','z'),equations)
            self.assertTrue(result.成立,result.データ)
            for j,name in enumerate(('x','y','z')):
                matrix=deepcopy(a)
                for i in range(3):matrix[i][j]=b[i]
                self.assertEqual(F(result.データ['解'][name]),det(matrix)/determinant)
            count+=1
        self.assertEqual(count,9)


if __name__=='__main__':
    unittest.main()
