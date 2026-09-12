"""場合分けの健全性、仮定の隔離、予算停止、実導出に基づく説明。"""
from itertools import product
import random
import unittest
from minidora.命題解釈 import 命題を読む, 命題資料を読む
from minidora.命題推論 import 命題推論器, 推論上限
from minidora.導出談話 import 導出説明節


class 場合分け試験(unittest.TestCase):
    def result(self, source, q):
        return 命題推論器(命題資料を読む(source, 'A')).判定(命題を読む(q)[0].式)
    def test_全ての場合で結論が成立(self):
        r=self.result('PまたはQ。PならばR。QならばR。','R')
        self.assertEqual(r['判定'],'支持')
        self.assertIn('全場合を閉じた選言除去',[p['作用'] for p in r['導出'].values()])
    def test_片方の成功だけでは不足(self):
        self.assertEqual(self.result('PまたはQ。PならばR。','R')['判定'],'未確定')
    def test_どちらの場合かは未確定のまま(self):
        self.assertEqual(self.result('PまたはQ。PならばR。QならばR。','P')['判定'],'未確定')
    def test_三つの場合で全てを要求(self):
        self.assertEqual(self.result('PまたはQまたはS。PならばR。QならばR。','R')['判定'],'未確定')
        self.assertEqual(self.result('PまたはQまたはS。PならばR。QならばR。SならばR。','R')['判定'],'支持')
    def test_反証も独立に場合分け(self):
        r=self.result('PまたはQ。Pならば否定(R)。Qならば否定(R)。','R')
        self.assertEqual(r['判定'],'反証')
    def test_異なる場合の支持と反証を一つに混ぜない(self):
        self.assertEqual(self.result('PまたはQ。PならばR。Qならば否定(R)。','R')['判定'],'未確定')
    def test_矛盾を含む場合を捨てない(self):
        self.assertEqual(self.result('PまたはQ。否定(P)。QならばR。','R')['判定'],'未確定')
    def test_場合分けからの矛盾は両経路を保持(self):
        r=self.result('PまたはQ。PならばR。QならばR。否定(R)。','R')
        self.assertEqual(r['判定'],'矛盾');self.assertTrue(r['支持']);self.assertTrue(r['反証'])
    def test_場合の仮定を次の問いへ漏らさない(self):
        e=命題推論器(命題資料を読む('PまたはQ。PならばR。QならばR。','A'))
        e.判定(命題を読む('R')[0].式)
        self.assertEqual(e.判定(命題を読む('P')[0].式)['判定'],'未確定')
    def test_二つの独立した選言を使う(self):
        r=self.result('PまたはQ。SまたはT。(PかつS)ならばR。(PかつT)ならばR。(QかつS)ならばR。(QかつT)ならばR。','R')
        self.assertEqual(r['判定'],'支持')
    def test_全称規則と場合分け(self):
        r=self.result('(太郎は猫である)または(太郎は鳥である)。すべての猫は動物である。すべての鳥は動物である。','太郎は動物である')
        self.assertEqual(r['判定'],'支持')
    def test_引用内の選言を分岐材料にしない(self):
        r=self.result('太郎は「PまたはQ」と述べた。PならばR。QならばR。','R')
        self.assertEqual(r['判定'],'未確定')
    def test_予算上限で部分成功を返さない(self):
        e=命題推論器(命題資料を読む('PまたはQ。PならばR。QならばR。','A'),上限=推論上限(操作数=12))
        with self.assertRaises(ValueError):e.判定(命題を読む('R')[0].式)
    def test_根拠グラフの親が閉じる(self):
        r=self.result('PまたはQ。PならばR。QならばR。','R')
        for node in r['導出'].values(): self.assertTrue(set(node['親']) <= set(r['導出']))
    def test_同じ入力は同じ導出(self):
        source='PまたはQ。PならばR。QならばR。'
        self.assertEqual(self.result(source,'R'),self.result(source,'R'))
    def test_独立真理値表との人工対照(self):
        # 32反復は一つの試験。古典論理と一致させるのは整合した命題集合での健全性だけ。
        rng=random.Random(21)
        def truth(e, env):
            if e.種別=='原子': return env[e.述語]
            vals=[truth(c,env) for c in e.子]
            return {'否定':lambda:not vals[0], '連言':lambda:all(vals), '選言':lambda:any(vals),
                    '含意':lambda:not vals[0] or vals[1]}[e.種別]()
        checked=0
        for _ in range(32):
            atoms=['P','Q','R']
            statements=['PまたはQ']+[rng.choice(atoms)+'ならば'+rng.choice(atoms) for _ in range(4)]
            rows=命題資料を読む('。'.join(statements),'A')
            models=[dict(zip(atoms,v)) for v in product((False,True),repeat=3)
                    if all(truth(r.式,dict(zip(atoms,v))) for r in rows)]
            self.assertTrue(models)
            e=命題推論器(rows)
            for q in atoms:
                answer=e.判定(命題を読む(q)[0].式)
                if answer['支持']:self.assertTrue(all(m[q] for m in models))
                if answer['反証']:self.assertTrue(all(not m[q] for m in models))
                checked+=1
        self.assertEqual(checked,96)


class 導出談話試験(unittest.TestCase):
    def test_根拠を番号順に説明する(self):
        s=導出説明節(3,'条件適用','R',(1,2))
        self.assertEqual(s.役割,'推論');self.assertIn('規則と前件',s.本文)
    def test_仮定を事実として述べない(self):
        self.assertIn('事実の追加ではありません',導出説明節(1,'場合の仮定','P',()).本文)
    def test_未来の工程を根拠にしない(self):
        with self.assertRaises(ValueError):導出説明節(2,'条件適用','R',(3,))
    def test_未実装作用を作文で埋めない(self):
        with self.assertRaises(ValueError):導出説明節(2,'因果確定','R',(1,))

if __name__=='__main__':unittest.main()
