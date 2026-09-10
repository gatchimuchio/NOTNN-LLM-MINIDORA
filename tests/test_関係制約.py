"""差分関係の契約・状態差・独立した全順序列挙による対照。"""
from copy import deepcopy
from dataclasses import asdict, replace
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
import json
import unittest

from minidora.関係制約 import (関係式, 関係根拠, 関係問題, 関係問題を復元,
    関係制約器, 関係記録整合, 関係判定を採用, _閉包, _符号)
from minidora.能力合成 import _結果辞書
from minidora.製品版.型 import 参照資料


def 式(name, left='A', op='超', right='B', diff='0'):
    return 関係式(name, left, op, right, diff)


def 問題(facts=(), queries=None, **kw):
    return 関係問題(('A','B','C'), tuple(facts), tuple(queries or (式('q','A','超','C'),)), **kw)


class 関係制約契約試験(unittest.TestCase):
    def 判定(self, facts=(), query=None, **kw):
        p=問題(facts,(query,) if query else None,**kw)
        r=関係制約器().実行(p)
        self.assertTrue(r.成立,r.保留理由)
        self.assertTrue(関係記録整合(r))
        return r.データ['回答'][0]['判定'],r

    def test_関係の推移を導く(self):
        state,r=self.判定((式('ab'),式('bc','B','超','C')))
        self.assertEqual(state,'導出')
        self.assertEqual(r.データ['回答'][0]['根拠制約'],['ab','bc'])

    def test_入力に結論の直書きを必要としない(self):
        _,r=self.判定((式('ab'),式('bc','B','超','C')))
        self.assertFalse(any(f['左項']=='A' and f['右項']=='C' for f in r.データ['問題']['制約']))

    def test_差の加算(self):
        s,_=self.判定((式('ab',op='以上',diff='3'),式('bc','B','以上','C','2')),式('q','A','以上','C','5'))
        self.assertEqual(s,'導出')

    def test_強すぎる差は未確定(self):
        s,_=self.判定((式('ab',op='以上',diff='3'),式('bc','B','以上','C','2')),式('q','A','以上','C','6'))
        self.assertEqual(s,'未確定')

    def test_厳密性をepsilon近似しない(self):
        for first,second,want in [('超','以上','導出'),('以上','超','導出'),('以上','以上','未確定')]:
            with self.subTest(first=first,second=second):
                s,_=self.判定((式('ab',op=first,diff='3'),式('bc','B',second,'C','2')),式('q','A','超','C','5'))
                self.assertEqual(s,want)

    def test_逆向きは反証(self):
        s,_=self.判定((式('ab'),式('bc','B','超','C')),式('q','C','以上','A'))
        self.assertEqual(s,'反証')

    def test_欠けた関係を補完しない(self):
        self.assertEqual(self.判定((式('ab'),))[0],'未確定')

    def test_循環矛盾から任意の結論を出さない(self):
        s,r=self.判定((式('ab'),式('bc','B','超','C'),式('ca','C','超','A')))
        self.assertEqual(s,'前提矛盾')
        self.assertFalse(r.データ['前提整合'])
        self.assertFalse(関係判定を採用(r,'q').成立)

    def test_非厳密循環は等値(self):
        fs=(式('ab',op='以上'),式('bc','B','以上','C'),式('ca','C','以上','A'))
        self.assertEqual(self.判定(fs,式('q','A','一致','C'))[0],'導出')

    def test_正の差を一周して要求すると矛盾(self):
        self.assertEqual(self.判定((式('ab',op='以上',diff='1'),式('ba','B','以上','A')))[0],'前提矛盾')

    def test_等値の置換(self):
        self.assertEqual(self.判定((式('ab',op='一致'),式('bc','B','超','C')))[0],'導出')

    def test_相対等式を正確に連鎖(self):
        fs=(式('ab',op='一致',diff='1/3'),式('bc','B','一致','C','2/3'))
        self.assertEqual(self.判定(fs,式('q','A','一致','C','1'))[0],'導出')

    def test_小数差を丸めて等値にしない(self):
        fs=(式('ab',op='一致',diff='0.10000000000000001'),)
        self.assertEqual(self.判定(fs,式('q','A','一致','B','0.1'))[0],'反証')

    def test_否定等値だけから大小を選ばない(self):
        fs=(式('ab',op='不一致'),)
        self.assertEqual(self.判定(fs,式('q','A','超','B'))[0],'未確定')
        self.assertEqual(self.判定(fs,式('q','A','一致','B'))[0],'反証')

    def test_非厳密と非等値から厳密比較(self):
        fs=(式('ab',op='以上'),式('ne',op='不一致'))
        self.assertEqual(self.判定(fs,式('q','A','超','B'))[0],'導出')

    def test_導出等値と非等式の競合(self):
        fs=(式('ab',op='一致'),式('bc','B','一致','C'),式('ne','A','不一致','C'))
        s,r=self.判定(fs)
        self.assertEqual(s,'前提矛盾')
        self.assertEqual(r.データ['競合']['種類'],'強制等値と非等式の競合')

    def test_実数領域を整数領域にすり替えない(self):
        fs=(式('lo',op='以上'),式('hi',op='以下',diff='1'),式('n0',op='不一致'),式('n1',op='不一致',diff='1'))
        self.assertEqual(self.判定(fs,式('q','A','超','B'))[0],'導出')

    def test_自己関係の恒真と恒偽(self):
        for op,want in [('一致','導出'),('不一致','反証'),('以上','導出'),('超','反証')]:
            with self.subTest(op=op):
                self.assertEqual(self.判定((),式('q','A',op,'A'))[0],want)

    def test_無関係な部分の矛盾も黙って捨てない(self):
        self.assertEqual(self.判定((式('bad','B','超','B'),),式('q','A','一致','A'))[0],'前提矛盾')

    def test_反対関係への変更が結論を変える(self):
        a=(式('ab'),式('bc','B','超','C'))
        b=(式('ab','B','超','A'),式('bc','C','超','B'))
        self.assertEqual((self.判定(a)[0],self.判定(b)[0]),('導出','反証'))

    def test_未解釈が残れば採用しない(self):
        s,r=self.判定((式('ab'),式('bc','B','超','C')),未解釈=('条件が未解釈',))
        self.assertEqual(s,'保留')
        self.assertFalse(関係判定を採用(r,'q').成立)

    def test_条件と時点を採用結果にも保つ(self):
        _,r=self.判定((式('ab'),式('bc','B','超','C')),属性='電圧',単位='V',条件='試験',時点='2026-09-10')
        value=関係判定を採用(r,'q')
        self.assertTrue(value.成立)
        self.assertEqual((value.データ['条件'],value.データ['時点']),('試験','2026-09-10'))

    def test_反証の採用は明示期待が必要(self):
        _,r=self.判定((式('ca','C','超','A'),))
        self.assertFalse(関係判定を採用(r,'q').成立)
        self.assertTrue(関係判定を採用(r,'q','反証').成立)
        self.assertFalse(関係判定を採用(r,'none','反証').成立)

    def test_一つの問いの結果を全体へ昇格しない(self):
        p=問題((式('ab'),),(式('q1','A','超','B'),式('q2','A','超','C')))
        r=関係制約器().実行(p)
        self.assertEqual([a['判定'] for a in r.データ['回答']],['導出','未確定'])

    def test_根拠制約と原文位置を追跡(self):
        src=参照資料('s','人工関係','契約',本文='A>B。B>C。')
        p=問題((式('ab'),式('bc','B','超','C')),根拠=(関係根拠('ab','s',0,4),関係根拠('bc','s',4,8)))
        r=関係制約器().実行(p,(src,))
        self.assertTrue(r.成立,r.保留理由)
        self.assertEqual([x['原文'] for x in r.データ['回答'][0]['原文対応']],['A>B。','B>C。'])

    def test_関係順序で真偽は変わらない(self):
        fs=(式('ab'),式('bc','B','超','C'))
        self.assertEqual(self.判定(fs)[0],self.判定(fs[::-1])[0])

    def test_証明に無関係な前提を必須にしない(self):
        p=関係問題(('A','B','C','D'),(式('ab'),式('bc','B','超','C'),式('dd','D','一致','D')),(式('q','A','超','C'),))
        r=関係制約器().実行(p)
        self.assertNotIn('dd',r.データ['回答'][0]['根拠制約'])

    def test_原本の不変と返却データの分離(self):
        p=問題((式('ab'),式('bc','B','超','C')))
        before=deepcopy(p)
        r=関係制約器().実行(p)
        r.データ['問題']['問い'][0]['比較']='以下'
        self.assertEqual(p,before)
        self.assertFalse(関係記録整合(r))

    def test_hash再生成でも採用の改変は再計算で検出(self):
        _,r=self.判定((式('ab'),))
        r.データ['回答'][0]['判定']='導出'
        r.データ.pop('記録SHA256')
        r.データ['記録SHA256']=sha256(_符号(_結果辞書(r))).hexdigest()
        self.assertFalse(関係記録整合(r))
        self.assertFalse(関係判定を採用(r,'q').成立)

    def test_JSON往復(self):
        p=問題((式('ab'),))
        self.assertEqual(p,関係問題を復元(json.loads(json.dumps(asdict(p)))))

    def test_不正問題と未知演算子を拒否(self):
        for p in (None,{},replace(問題(),変数=('A','A')),問題((式('x',op='因果'),)),問題((式('q'),)),問題((式('@予約'),)),問題((式('x','Z'),))):
            with self.subTest(p=p):
                r=関係制約器().実行(p)
                self.assertFalse(r.成立)
                self.assertEqual(r.本文,'')

    def test_差の型と過大桁を拒否(self):
        for value in (0.1,True,'NaN','Infinity','1/0','1e999','1'*65,' 1','0.1 '):
            with self.subTest(value=value):
                self.assertFalse(関係制約器().実行(問題((式('x',diff=value),))).成立)

    def test_上限は入力を剪定せず保留(self):
        for p in (replace(問題(),変数=tuple(str(i) for i in range(25))),replace(問題(),問い=tuple(式(str(i)) for i in range(17))),replace(問題(),制約=tuple(式(str(i)) for i in range(129)))):
            self.assertFalse(関係制約器().実行(p).成立)
        r=関係制約器().実行(問題((式('ab'),式('bc','B','超','C'))),最大演算数=1)
        self.assertFalse(r.成立)
        self.assertIn('演算数上限',r.保留理由)

    def test_停止要求と故障を成功にしない(self):
        for callback in (lambda:True,lambda:'false',lambda:1/0):
            r=関係制約器().実行(問題(),停止要求=callback)
            self.assertFalse(r.成立)
            self.assertEqual(r.本文,'')

    def test_根拠原文の不正範囲(self):
        src=参照資料('s','t','o',本文='A>B')
        for span in ((-1,3),(0,4),(True,2),(3,3)):
            p=問題((式('ab'),),根拠=(関係根拠('ab','s',*span),))
            self.assertFalse(関係制約器().実行(p,(src,)).成立)

    def test_記録や復元の未知項目を拒否(self):
        with self.assertRaises(ValueError):
            関係問題を復元({**asdict(問題()),'未知':1})
        self.assertFalse(関係記録整合(None))

    def test_不正時点と最大演算数(self):
        for p in (問題(時点='2026-02-30'),問題(時点='明日'),問題(属性='')):
            self.assertFalse(関係制約器().実行(p).成立)
        for n in (0,True,1.5):
            self.assertFalse(関係制約器().実行(問題(),最大演算数=n).成立)


class 関係独立列挙試験(unittest.TestCase):
    def test_全弱順序の列挙と全演算子の対照(self):
        # 3変数、差0なら全弱順序は{0,1,2}への代入で必ず代表される。
        ops=('一致','不一致','以下','未満','以上','超')
        check={'一致':lambda a,b:a==b,'不一致':lambda a,b:a!=b,'以下':lambda a,b:a<=b,
               '未満':lambda a,b:a<b,'以上':lambda a,b:a>=b,'超':lambda a,b:a>b}
        formulas=[(x,op,y) for x,y in [('A','B'),('B','C'),('A','C')] for op in ops]
        qs=tuple(式('q'+str(i),'A',op,'C') for i,op in enumerate(ops))
        models=[dict(zip(('A','B','C'),vs)) for vs in product(range(3),repeat=3)]
        for combo in combinations(formulas,2):
            facts=tuple(式('f'+str(i),x,op,y) for i,(x,op,y) in enumerate(combo))
            valid=[m for m in models if all(check[op](m[x],m[y]) for x,op,y in combo)]
            p=問題(facts,qs)
            r=関係制約器().実行(p)
            self.assertTrue(r.成立,r.保留理由)
            for answer in r.データ['回答']:
                q=answer['問い']
                values=[check[q['比較']](m['A'],m['C']) for m in valid]
                want='前提矛盾' if not values else '導出' if all(values) else '反証' if not any(values) else '未確定'
                self.assertEqual(answer['判定'],want,(combo,q))
                proof=answer['反証検査']
                if proof:
                    subset=tuple(f for f in facts if f.識別子 in answer['根拠制約'])
                    if '仮定' in proof:
                        subset+=(関係式(**proof['仮定']),)
                    self.assertFalse(_閉包(p.変数,subset,lambda:None)[0])

    def test_長い鎖と一辺削除の対照(self):
        names=tuple('v'+str(i) for i in range(20))
        facts=tuple(式('e'+str(i),names[i],'以上',names[i+1],'1') for i in range(19))
        p=関係問題(names,facts,(式('q',names[0],'以上',names[-1],'19'),))
        r=関係制約器().実行(p)
        self.assertEqual(r.データ['回答'][0]['判定'],'導出')
        r=関係制約器().実行(replace(p,制約=facts[:9]+facts[10:]))
        self.assertEqual(r.データ['回答'][0]['判定'],'未確定')


if __name__=='__main__':
    unittest.main()
