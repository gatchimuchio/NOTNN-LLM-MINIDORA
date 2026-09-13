"""関連閉包による削減を、独立な集合閉包・全列挙と比較する。"""
from copy import deepcopy
from itertools import combinations
import random
import unittest
from minidora.有限仮説探索 import 仮説を検討, 仮説報告を検査
from minidora.命題解釈 import 命題を読む


def 要求を作る(rules, candidates, observations=('Q',), facts=(), maximum=3):
    return {'事実':[{'識別子':f'f{i}','命題':入力表記(v),'出典':'人工比較用'} for i,v in enumerate(facts)],
            '規則':[{'識別子':f'r{i}','前件':list(map(入力表記,a)),'後件':入力表記(b),'出典':'人工比較用'} for i,(a,b) in enumerate(rules)],
            '仮説候補':list(map(入力表記,candidates)),'観測':list(map(入力表記,observations)),'最大仮説数':maximum,
            '最大試行数':4096,'最大操作数':1_000_000}


def 入力表記(text):
    return '否定（'+text[:-4]+'）' if text.endswith('ではない') else text


def 正負(text):
    if text.startswith('否定（') and text.endswith('）'):
        return (text[3:-1],False)
    return (text[:-4],False) if text.endswith('ではない') else (text,True)


def 独立全列挙(req):
    """製品の解析器・証明グラフ・探索枝刈りを利用しない人工記号の集合演算。"""
    obs=set(map(正負,req['観測']))
    candidates=list(map(正負,req['仮説候補']))
    facts=set(正負(f['命題']) for f in req['事実'])
    rules=[(set(map(正負,r['前件'])),正負(r['後件'])) for r in req['規則']]
    def closure(seed):
        values=set(seed)|facts
        while True:
            after=values|{b for a,b in rules if a<=values}
            if after==values:return values
            values=after
    def conflict(values):
        return any((x,not p) in values for x,p in values) or any((x,not p) in values for x,p in obs)
    if conflict(closure(set())):return set()
    successful=[]
    for n in range(min(req['最大仮説数'],len(candidates))+1):
        for subset in combinations(candidates,n):
            result=closure(subset)
            if not conflict(result) and obs<=result:successful.append(frozenset(subset))
    return {s for s in successful if not any(other<s for other in successful)}


def 出力集合(report):
    return {frozenset(正負(v) for v in c['仮説']) for c in report['候補']}


class 関連閉包試験(unittest.TestCase):
    def test_16候補6個の組合せを関連2組へ削減(self):
        req=要求を作る([(('A',),'Q')],['A',*[f'X{i}' for i in range(15)]],maximum=6)
        reduced=仮説を検討(req)
        self.assertEqual(reduced['探索範囲']['対象組合せ数'],14893)
        self.assertEqual(reduced['探索範囲']['検討組合せ数'],2)
        self.assertEqual(reduced['探索範囲']['関連性による省略組合せ数'],14891)
        self.assertEqual(出力集合(reduced),{frozenset({('A',True)})})
        self.assertTrue(仮説報告を検査(reduced));self.assertTrue(reduced['探索完了'])
        with self.assertRaises(ValueError):仮説を検討({**req,'探索方式':'全列挙'})

    def test_全候補が関連する場合は予算を突破しない(self):
        names=[f'X{i}' for i in range(16)]
        req=要求を作る([((x,),'Q') for x in names],names,maximum=6)
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_観測外への導出が矛盾を生む候補を除外(self):
        req=要求を作る([(('A',),'Q'),(('A',),'X'),(('A',),'Xではない'),(('B',),'Q')],['A','B','Y'])
        report=仮説を検討(req)
        self.assertEqual(出力集合(report),{frozenset({('B',True)})})
        self.assertGreater(report['件数']['不整合'],0)

    def test_連言前件を一部の原因だけに落とさない(self):
        req=要求を作る([(('A','B'),'X'),(('X',),'Q')],['A','B','Z'])
        self.assertEqual(出力集合(仮説を検討(req)),{frozenset({('A',True),('B',True)})})

    def test_関連外の不正候補も入力段階で拒否(self):
        req=要求を作る([(('A',),'Q')],['A','PまたはR'])
        with self.assertRaises(ValueError):仮説を検討(req)
        req=要求を作る([(('A',),'Q')],['A','Z','Z'])
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_明示否定の規則と観測を独立に扱う(self):
        req=要求を作る([(('Aではない',),'Qではない')],['A','Aではない','X'],observations=('Qではない',))
        report=仮説を検討(req)
        self.assertEqual(出力集合(report),{frozenset({('A',False)})})

    def test_無関係な候補が背景矛盾を隠さない(self):
        req=要求を作る([(('A',),'Q')],['A','Z'],facts=('X','Xではない'))
        self.assertEqual(仮説を検討(req)['状態'],'背景不整合')

    def test_循環規則でも閉包が停止し説明を保つ(self):
        req=要求を作る([(('A',),'B'),(('B',),'A'),(('B',),'Q')],['A','B','C'])
        self.assertEqual(出力集合(仮説を検討(req)),{frozenset({('A',True)}),frozenset({('B',True)})})

    def test_事実だけで説明できるなら空仮説が唯一極小(self):
        req=要求を作る([],['A','B'],facts=('Q',))
        self.assertEqual(出力集合(仮説を検討(req)),{frozenset()})

    def test_前処理にも同じ操作予算を適用(self):
        req=要求を作る([(('A',),'B'),(('B',),'Q')],['A'])
        req['最大操作数']=1
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_探索方式の未知値を既定動作に置換しない(self):
        req=要求を作る([(('A',),'Q')],['A'])
        for mode in ('自動推測','',True,None):
            with self.assertRaises(ValueError):仮説を検討({**req,'探索方式':mode})

    def test_省略記録の改変を検出(self):
        report=仮説を検討(要求を作る([(('A',),'Q')],['A','Z']))
        report['探索範囲']['除外候補']=[]
        self.assertFalse(仮説報告を検査(report))

    def test_96個の人工モデルを独立全列挙と照合(self):
        rng=random.Random(250913)
        symbols=('A','B','C','D','Q','X')
        literals=tuple(s+neg for s in symbols for neg in ('','ではない'))
        for i in range(96):
            rules=[(tuple(rng.sample(literals,rng.randint(1,2))),rng.choice(literals)) for _ in range(10)]
            # 観測Qと同値の候補は禁止。正負はともに許すが閉包の矛盾で不採用にする。
            candidates=rng.sample([v for v in literals if v not in ('Q','Qではない')],5)
            facts=tuple(rng.sample(literals,rng.randrange(3)))
            req=要求を作る(rules,candidates,facts=facts)
            with self.subTest(モデル=i):
                oracle=独立全列挙(req)
                reduced=仮説を検討(req)
                exhaustive=仮説を検討({**req,'探索方式':'全列挙'})
                self.assertEqual(出力集合(reduced),oracle)
                self.assertEqual(出力集合(exhaustive),oracle)
                self.assertEqual(reduced['候補'],exhaustive['候補'])

if __name__=='__main__':unittest.main()
