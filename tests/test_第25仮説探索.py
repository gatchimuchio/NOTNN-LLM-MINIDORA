"""規則逆参照、健全な枝刈り、候補別の追加確認。人工有限モデルとの照合。"""
from copy import deepcopy
from itertools import combinations
import random
import unittest
from minidora.有限仮説探索 import 仮説を検討, 仮説報告を検査
from minidora.監査改善会話 import 監査改善会話セッション
from minidora.監査改善接続 import 改善回答を構成, 改善回答を検査


def rule(name,left,right):return {'識別子':name,'前件':left,'後件':right,'出典':'明示資料'}
def fact(name,value):return {'識別子':name,'命題':value,'出典':'明示資料'}
def request(rules,candidates,observed=('Z',),facts=(),**kw):
    return {'事実':list(facts),'規則':rules,'観測':list(observed),'仮説候補':candidates,**kw}
def answers(report):return {frozenset(x['仮説']) for x in report['候補']}
def opposite(x):return x[3:-1] if x.startswith('否定(') else '否定('+x+')'
def canonical(x):return x.replace('(', '（').replace(')', '）')


def exhaustive(req):
    """枝刈りなしの集合固定点。製品側の解析器・閉包・報告器は使わない。"""
    facts={f['命題'] for f in req['事実']}; obs=set(req['観測'])
    def close(hyp):
        values=facts|set(hyp)
        while True:
            new={r['後件'] for r in req['規則'] if set(r['前件'])<=values}
            if new<=values:return values
            values|=new
    def consistent(values):return not any(opposite(x) in values for x in values|obs)
    if not consistent(close(())):return set()
    valid=[]
    candidates=req['仮説候補']
    for size in range(min(len(candidates),req.get('最大仮説数',3))+1):
        for row in combinations(candidates,size):
            values=close(row)
            if consistent(values) and obs<=values:valid.append(frozenset(row))
    return {frozenset(canonical(x) for x in h) for h in valid if not any(g<h for g in valid)}


class 仮説性能試験(unittest.TestCase):
    def test_小有限系120例で枝刈りなし独立実装と一致する(self):
        rng=random.Random(250913)
        literals=['A','B','C','D','Z','否定(A)','否定(B)','否定(Z)']
        for case in range(120):
            rules=[rule('r'+str(i),rng.sample(literals,rng.randint(1,2)),rng.choice(literals)) for i in range(rng.randint(1,8))]
            req=request(rules,rng.sample(['A','B','C','D','否定(A)','否定(B)'],rng.randint(0,6)),facts=[fact('f'+str(i),v) for i,v in enumerate(rng.sample(literals,rng.randint(0,2)))])
            with self.subTest(case=case):self.assertEqual(answers(仮説を検討(req)),exhaustive(req))

    def test_関係ない候補の組合せで実評価予算を使わない(self):
        req=request([rule('r',['A'],'Z')],['A',*[f'X{i}' for i in range(15)]],最大仮説数=6,最大試行数=4)
        report=仮説を検討(req)
        self.assertEqual(report['探索範囲']['対象組合せ数'],14893)
        self.assertEqual(report['件数']['評価'],2)
        self.assertEqual(report['件数']['関連外による省略'],14891)
        self.assertEqual(answers(report),{frozenset(['A'])})
        self.assertTrue(report['探索完了'])

    def test_実評価も超える場合は途中採用しない(self):
        req=request([rule('r1',['A'],'Z'),rule('r2',['B'],'Z')],['A','B'],最大試行数=2)
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_枝刈り列挙自体も操作上限を守る(self):
        req=request([rule('r',['A'],'Z')],['A',*[f'X{i}' for i in range(15)]],最大仮説数=6,最大操作数=100)
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_観測に無関係な矛盾規則を捨てない(self):
        req=request([rule('r',['A'],'Z'),rule('c1',['A'],'X'),rule('c2',['A'],'否定(X)')],['A','B'])
        self.assertEqual(answers(仮説を検討(req)),set())

    def test_不整合集合の上位も安全に除外する(self):
        req=request([rule('r1',['A','B'],'Z'),rule('r2',['C'],'Z'),rule('r3',['A'],'X'),rule('r4',['A'],'否定(X)')],['A','B','C'])
        report=仮説を検討(req)
        self.assertEqual(answers(report),{frozenset(['C'])})
        self.assertGreater(report['件数']['不整合による省略'],0)

    def test_順番を変えても候補と由来は一致する(self):
        req=request([rule('r1',['A'],'Z'),rule('r2',['B'],'Z')],['A','B','C'])
        other=deepcopy(req);other['規則'].reverse();other['仮説候補'].reverse()
        a,b=仮説を検討(req),仮説を検討(other)
        for key in ('候補','候補生成','追加確認候補','件数'):self.assertEqual(a[key],b[key])

    def test_追加確認の構成まで操作予算へ算入する(self):
        req=request([rule('r1',['A'],'Z'),rule('r2',['B'],'Z')],'規則から生成')
        report=仮説を検討(req)
        limit=report['操作数']
        self.assertEqual(answers(仮説を検討({**req,'最大操作数':limit})),answers(report))
        with self.assertRaises(ValueError):仮説を検討({**req,'最大操作数':limit-1})

    def test_報告の候補生成履歴改変を検知する(self):
        report=仮説を検討(request([rule('r',['A'],'Z')],'規則から生成'))
        self.assertTrue(仮説報告を検査(report))
        report['候補生成']['由来']['A'][0]['出典']='別資料'
        self.assertFalse(仮説報告を検査(report))


class 仮説構成試験(unittest.TestCase):
    def test_規則前提から候補を作り観測は仮説にしない(self):
        report=仮説を検討(request([rule('r1',['A'],'B'),rule('r2',['B'],'Z')],'規則から生成'))
        self.assertEqual(answers(report),{frozenset(['A']),frozenset(['B'])})
        self.assertNotIn('Z',report['候補生成']['由来']);self.assertFalse(report['事実認定'])
        self.assertEqual(report['候補生成']['由来']['A'],[{'規則':'r1','出典':'明示資料'}])

    def test_既知事実を仮説に作り直さない(self):
        report=仮説を検討(request([rule('r',['A'],'Z')],'規則から生成',facts=[fact('f','A')]))
        self.assertEqual(answers(report),{frozenset()});self.assertEqual(report['候補生成']['由来'],{})

    def test_無関係な規則から候補を無闇に追加しない(self):
        report=仮説を検討(request([rule('r',['A'],'Z'),rule('x',['X'],'Y')],'規則から生成'))
        self.assertEqual(set(report['候補生成']['由来']),{'A'})

    def test_候補がなくても未知原因を捏造しない(self):
        report=仮説を検討(request([],'規則から生成'))
        self.assertEqual(answers(report),set());self.assertEqual(report['状態'],'指定範囲に説明なし')

    def test_明示否定の前提も候補へ構成する(self):
        report=仮説を検討(request([rule('r',['否定(A)'],'Z')],'規則から生成'))
        self.assertEqual(answers(report),{frozenset(['否定（A）'])})

    def test_循環は自動支持ではなく仮定が必要(self):
        report=仮説を検討(request([rule('r1',['A'],'B'),rule('r2',['B'],'A'),rule('r3',['B'],'Z')],'規則から生成'))
        self.assertNotIn(frozenset(),answers(report));self.assertEqual(answers(report),{frozenset(['A']),frozenset(['B'])})

    def test_生成候補17個を16個へ切り詰めない(self):
        req=request([rule('r'+str(i),['A'+str(i)],'Z') for i in range(17)],'規則から生成')
        with self.assertRaises(ValueError):仮説を検討(req)

    def test_候補間の未導出と反証を混同しない(self):
        report=仮説を検討(request([rule('r1',['A'],'Z'),rule('r2',['B'],'Z')],['A','B']))
        checks=report['追加確認候補'];self.assertTrue(checks)
        for check in checks:
            labels={x['判定'] for x in check['候補別導出']}
            self.assertEqual(labels,{'支持','未導出'});self.assertIn('未確認',check['留保'])

    def test_一候補で識別のための次質問を作らない(self):
        report=仮説を検討(request([rule('r',['A'],'Z')],['A']))
        self.assertEqual(report['追加確認候補'],[])

    def test_詳細説明の追加確認も根拠から再検査する(self):
        report=仮説を検討(request([rule('r1',['A'],'Z'),rule('r2',['B'],'Z')],'規則から生成'))
        out=改善回答を構成(report,詳細=True)
        self.assertIn('未導出',out['本文']);self.assertTrue(改善回答を検査(out))
        out['本文']+='必ずAが原因です。';self.assertFalse(改善回答を検査(out))

    def test_日本語会話で生成から説明まで接続する(self):
        s=監査改善会話セッション('生成')
        r=s.応答('仮説資料「例」を登録：\n規則：AならばZ\n規則：BならばZ\n候補：規則から生成')
        self.assertTrue(r.成立,r.理由)
        r=s.応答('資料「例」で観測「Z」を説明する仮説を検討して')
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(answers(r.結果.データ['報告']),{frozenset(['A']),frozenset(['B'])})
        self.assertEqual(len(r.追跡['工程作用']),3)

if __name__=='__main__':unittest.main()
