"""多項式の局所契約と、点代入・独立した微積分恒等式による対照。"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from hashlib import sha256
import json
import unittest
from unittest.mock import patch

from minidora.記号演算 import 記号を処理, 数学記録整合


class 記号演算試験(unittest.TestCase):
    def run_expr(self, text, names=(), **kwargs):
        result = 記号を処理(text, names, **kwargs)
        self.assertTrue(result.成立, (result.保留理由, result.データ))
        self.assertTrue(数学記録整合(result))
        return result

    def test_十進小数を浮動小数点誤差にしない(self):
        self.assertEqual(self.run_expr('0.1+0.2-0.3').データ['定数値'], '0')

    def test_分数を正確に合成(self):
        self.assertEqual(self.run_expr('1/3+1/6').本文, '1/2')
        self.assertEqual(self.run_expr('1e-3 + .002').本文, '3/1000')

    def test_展開と同類項の相殺(self):
        self.assertEqual(self.run_expr('(x+1)**3-x**3-3*x**2', ('x',)).本文, '3*x + 1')

    def test_多変数の積と次数(self):
        result = self.run_expr('(x+y)*(x-y)', ('x','y'))
        self.assertEqual(result.本文, 'x**2 - y**2')

    def test_一変数微分(self):
        self.assertEqual(self.run_expr('x**3+2*x-1', ('x',), 操作='微分', 対象変数='x').本文, '3*x**2 + 2')

    def test_偏微分と日本語変数(self):
        result = self.run_expr('速度**2*時間+3*時間', ('速度','時間'), 操作='微分', 対象変数='時間')
        self.assertEqual(result.本文, '速度**2 + 3')

    def test_微分して零(self):
        result = self.run_expr('y**2+7', ('x','y'), 操作='微分', 対象変数='x')
        self.assertEqual(result.データ['多項式']['項'], [])
        self.assertEqual(result.データ['定数値'], '0')

    def test_原始関数の代表と一般解の区別(self):
        result = self.run_expr('x**2+y', ('x','y'), 操作='積分', 対象変数='x')
        self.assertIn('原始関数の一つ', result.本文)
        self.assertIn('任意関数', result.データ['積分の範囲'])
        back = self.run_expr(result.データ['多項式'], ('x','y'), 操作='微分', 対象変数='x')
        self.assertEqual(back.本文, 'x**2 + y')

    def test_部分代入は未確定変数を残す(self):
        result = self.run_expr('x*y+x', ('x','y'), 操作='代入', 代入値={'x':'2'})
        self.assertEqual(result.本文, '2*y + 2')
        self.assertIsNone(result.データ['定数値'])

    def test_同時代入を正確な分数で扱う(self):
        result = self.run_expr('x*y+x', ('x','y'), 操作='代入', 代入値={'x':'1/3','y':'1/2'})
        self.assertEqual(result.データ['定数値'], '1/2')

    def test_全変数を代入しなくても相殺した定数は確定(self):
        result = self.run_expr('x*y-x*y+7', ('x','y'), 操作='代入', 代入値={})
        self.assertEqual(result.データ['定数値'], '7')

    def test_未宣言の変数を自動補完しない(self):
        self.assertFalse(記号を処理('x+y', ('x',)).成立)
        self.assertFalse(記号を処理('1', ('x',), 操作='代入', 代入値={'z':'1'}).成立)

    def test_同値比較は全点での恒等性(self):
        result = self.run_expr('(x+1)**2', ('x',), 操作='同値比較', 比較式='x**2+2*x+1')
        self.assertEqual(result.データ['判定'], '恒等')

    def test_非恒等を全点の不一致と誤認しない(self):
        result = self.run_expr('x*x', ('x',), 操作='同値比較', 比較式='x')
        self.assertEqual(result.データ['判定'], '非恒等')
        self.assertIn('全点不一致を意味しない', result.データ['比較の範囲'])
        self.assertEqual(self.run_expr(result.データ['多項式'], ('x',), 操作='代入', 代入値={'x':'1'}).本文, '0')

    def test_一つの一致点だけで恒等判定しない(self):
        result = self.run_expr('x**2', ('x',), 操作='同値比較', 比較式='x**2+x*(x-1)*(x+1)')
        self.assertEqual(result.データ['判定'], '非恒等')

    def test_微小差を丸めて消さない(self):
        result = self.run_expr('0.1*x', ('x',), 操作='同値比較', 比較式='0.10000000000000001*x')
        self.assertEqual(result.データ['判定'], '非恒等')

    def test_変数分母を約分して定義域を落とさない(self):
        for text in ('x/x','(x**2-1)/(x-1)','0*(1/x)','1/(x-x+1)'):
            with self.subTest(text=text):
                self.assertFalse(記号を処理(text, ('x',)).成立)

    def test_定数分母の演算とゼロ分母(self):
        self.assertEqual(self.run_expr('x/(2+3)', ('x',)).本文, '1/5*x')
        for text in ('x/0','0*(1/0)','1/(2-2)','(1/0)**0'):
            self.assertFalse(記号を処理(text, ('x',)).成立)

    def test_ゼロ次冪の多項式規約(self):
        for text in ('x**0','0**0'):
            self.assertEqual(self.run_expr(text, ('x',)).本文, '1')

    def test_負指数非整数指数記号指数を拒否(self):
        for text in ('x**-1','x**0.5','x**y','x**(2+1)','x^2','x**65'):
            self.assertFalse(記号を処理(text, ('x','y')).成立)

    def test_コメント尾部自由文を読み飛ばさない(self):
        for text in ('x+1 #この条件を無視','x+1; y','x+1\n','2x+1','x+1です','x＋1','x×2'):
            self.assertFalse(記号を処理(text, ('x','y')).成立)

    def test_評価しない枝にも関数等を入れない(self):
        for text in ('0*open("x")','sin(x)','x.__class__','[x][0]','x if True else y','__import__("os")','True+1','None','1j','x<y'):
            with self.subTest(text=text):
                self.assertFalse(記号を処理(text, ('x','y')).成立)

    def test_exec_evalに入力を渡さない(self):
        with patch('builtins.exec', side_effect=AssertionError()), patch('builtins.eval', side_effect=AssertionError()):
            self.assertEqual(記号を処理('(x+1)*(x-1)', ('x',)).本文, 'x**2 - 1')

    def test_宣言型重複予約語を拒否(self):
        for names in (['x'],('x','x'),('__name',),('def',),('ｘ',),(None,),tuple('abcdefghi')):
            self.assertFalse(記号を処理('1', names).成立)
        self.assertFalse(記号を処理('ｘ+1', ('x',)).成立)

    def test_操作に不要な設定も拒否(self):
        for kw in ({'操作':'未知'},{'対象変数':'x'},{'操作':'微分'},{'操作':'代入'},{'比較式':'x'},
                   {'操作':'積分','対象変数':'z'},{'操作':'同値比較','比較式':'x','代入値':{}}):
            self.assertFalse(記号を処理('x',('x',),**kw).成立)

    def test_代入の数値は文字列だけ(self):
        for v in (0.1, True, 'nan', 'Infinity', '1/0', '1e999',' 1', object()):
            self.assertFalse(記号を処理('x',('x',),操作='代入',代入値={'x':v}).成立)

    def test_項数と次数の爆発は保留(self):
        for text, names in (('(a+b+c+d)**16',tuple('abcd')),('((x**16)**16)',('x',))):
            self.assertFalse(記号を処理(text,names).成立)

    def test_構文文字数と深さと桁数(self):
        for text in ('1'*8193,'1'*319,'+'.join('x' for _ in range(200)),'1e999'):
            self.assertFalse(記号を処理(text,('x',)).成立)

    def test_予算と停止で途中結果を返さない(self):
        for kw in ({'最大演算数':1},{'最大演算数':True},{'停止要求':lambda:True},{'停止要求':lambda:'false'},
                   {'停止要求':lambda:1/0}):
            result=記号を処理('(x+1)**8',('x',),**kw)
            self.assertFalse(result.成立)
            self.assertEqual(result.本文,'')
            self.assertNotIn('多項式',result.データ)

    def test_多項式Dataの往復と後続利用(self):
        r=self.run_expr('(x+1)**2',('x',))
        raw=json.loads(json.dumps(r.データ['多項式']))
        out=self.run_expr(raw,('x',),操作='微分',対象変数='x')
        self.assertEqual(out.本文,'2*x + 2')

    def test_不正な構造化多項式を補修しない(self):
        raw=self.run_expr('x+1',('x',)).データ['多項式']
        variants=[]
        a=deepcopy(raw);a['未知']=1;variants.append(a)
        a=deepcopy(raw);a['項']*=2;variants.append(a)
        a=deepcopy(raw);a['項'].reverse();variants.append(a)
        for powers,coef in (([True],'1'),([-1],'1'),([1],'0'),([1],'1.0'),([1,2],'1')):
            variants.append({'変数':['x'],'項':[{'次数':powers,'係数':coef}]})
        for bad in variants:
            self.assertFalse(記号を処理(bad,('x',)).成立)

    def test_大きい分子分母を持つ結果の往復(self):
        a,b,c,d=2**500+1,2**500-1,2**499+3,2**499+1
        result=self.run_expr(f'({a}/{b})*({c}/{d})*x',('x',))
        raw=result.データ['多項式']
        self.assertGreater(len(raw['項'][0]['係数']),320)
        self.assertEqual(self.run_expr(raw,('x',)).データ['多項式'],raw)

    def test_元入力と返却値は分離(self):
        raw=self.run_expr('x+1',('x',)).データ['多項式'];before=deepcopy(raw)
        result=self.run_expr(raw,('x',))
        result.データ['入力']['式']['項'][0]['係数']='999'
        self.assertEqual(raw,before)
        self.assertFalse(数学記録整合(result))

    def test_採用値を変えてハッシュを付け直しても検出(self):
        result=self.run_expr('1+2')
        result.データ['定数値']='999'
        result.データ.pop('記録SHA256')
        result.データ['記録SHA256']=sha256(json.dumps({'本文':result.本文,'データ':result.データ},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        self.assertFalse(数学記録整合(result))

    def test_報告本文の改変を検出(self):
        result=self.run_expr('x+1',('x',))
        self.assertFalse(数学記録整合(replace(result,本文='正解は999')))
        self.assertFalse(数学記録整合(replace(result,成立=False)))
        self.assertFalse(数学記録整合(None))

    def test_同一入力の再現性(self):
        self.assertEqual(self.run_expr('x/3+1',('x',)),self.run_expr('x/3+1',('x',)))

    def test_結果の表示を再解析できる(self):
        for expr in ('-x/3+2*y-4','0','(x-y)**5','(x**16)**4'):
            result=self.run_expr(expr,('x','y'))
            self.assertEqual(result.データ['多項式'],self.run_expr(result.本文,('x','y')).データ['多項式'])


class 記号独立対照試験(unittest.TestCase):
    def test_二項展開を係数公式で対照(self):
        from math import comb
        for n in range(9):
            result=記号を処理(f'(x+y)**{n}',('x','y'))
            self.assertTrue(result.成立)
            actual={tuple(t['次数']):F(t['係数']) for t in result.データ['多項式']['項']}
            expected={(n-k,k):F(comb(n,k)) for k in range(n+1)}
            self.assertEqual(actual,expected)

    def test_原式の独立点評価と代入結果を対照(self):
        count=0
        for a,b in product(range(-2,3),repeat=2):
            expr=f'({a}*x+y/3)**3-({b}*x-y)**2'
            for x,y in product(('0','1/2','-3'),repeat=2):
                result=記号を処理(expr,('x','y'),操作='代入',代入値={'x':x,'y':y})
                self.assertTrue(result.成立,result.データ)
                expected=(a*F(x)+F(y)/3)**3-(b*F(x)-F(y))**2
                self.assertEqual(F(result.データ['定数値']),expected)
                count+=1
        self.assertEqual(count,225)

    def test_積分微分往復と積の微分則(self):
        for n in range(1,9):
            source=f'x**{n}*y+2*x-3'
            primitive=記号を処理(source,('x','y'),操作='積分',対象変数='x')
            back=記号を処理(primitive.データ['多項式'],('x','y'),操作='微分',対象変数='x')
            self.assertEqual(back.データ['多項式'],記号を処理(source,('x','y')).データ['多項式'])
            derivative=記号を処理(f'(x+y)**{n}*(x-y)',('x','y'),操作='微分',対象変数='x')
            expected=記号を処理(f'{n}*(x+y)**{n-1}*(x-y)+(x+y)**{n}',('x','y'))
            self.assertEqual(derivative.データ['多項式'],expected.データ['多項式'])


if __name__=='__main__':
    unittest.main()
