"""実HDSの局所意味射影・会話行為。未知日本語一般化の認定ではない。"""
from dataclasses import replace
import unittest
from minidora.会話要求 import 会話を解釈, 会話要求
from minidora.hds_compiler import 公開HDSコンパイラ
from minidora.hds_ir import HDS残差

class 会話意味試験(unittest.TestCase):
    def parse(self, q): return 会話を解釈(公開HDSコンパイラ().コンパイル(q))
    def test_対象属性単位を分離(self):
        r=self.parse('「装置A」と「装置B」の電圧をVで比較して')
        self.assertEqual(r.行為,'依頼');self.assertEqual(r.要求,会話要求('比較',('装置A','装置B'),'電圧','V'))
    def test_質問と依頼は同じ目的へ(self):
        for tail in ('どちらが大きい？','どちらが小さい?','どちらが高い','どちらが低い'):
            r=self.parse('「装置A」と「装置B」の電圧はVで'+tail)
            self.assertEqual(r.行為,'質問');self.assertEqual(r.要求.種別,'比較')
    def test_不足した単位を事実として補完しない(self):
        r=self.parse('「装置A」と「装置B」の電圧を比べて')
        self.assertIsNone(r.要求.単位)
    def test_接頭条件は順序非依存(self):
        a='条件「通常」で、';b='2026-09-11時点、';q='「装置A」の電圧をVで教えて'
        x,y=self.parse(a+b+q),self.parse(b+a+q)
        self.assertEqual(x.要求,y.要求);self.assertEqual(x.要求.条件,'通常');self.assertEqual(x.要求.時点,'2026-09-11')
    def test_単一照会(self):
        self.assertEqual(self.parse('「装置A」の電圧をVで調べてください').要求.種別,'照会')
    def test_補充訂正取消再開(self):
        for q,kind in (('単位はVです','補充'),('訂正：単位はmVです','訂正'),('時点は2026-09-11です','補充'),
                       ('条件は「通常」です','補充'),('取り消して','取消'),('再開して','再開')):
            self.assertEqual(self.parse(q).行為,kind,q)
    def test_未知尾部は命令だけで進めない(self):
        self.assertIsNone(self.parse('「装置A」と「装置B」の電圧をVで比較して、低い方を買って').要求)
    def test_否定の尾部は無視しない(self):
        self.assertIsNone(self.parse('「装置A」と「装置B」の電圧をVで比較して。ただし実行しないで').要求)
    def test_比較の同じ対象を拒否(self):
        self.assertIsNone(self.parse('「装置A」と「装置A」の電圧をVで比較して').要求)
    def test_未知単位を拒否(self):
        self.assertIsNone(self.parse('「装置A」の電圧をXYZで調べて').要求)
    def test_不正時点と重複条件を拒否(self):
        for prefix in ('2026-02-30時点、','条件「通常」で、条件「高温」で、'):
            self.assertIsNone(self.parse(prefix+'「装置A」の電圧をVで調べて').要求)
    def test_属性を対象の中の助詞で分割しない(self):
        r=self.parse('「を含む装置」と「は含む装置」の電圧をVで比較して')
        self.assertEqual(r.要求.対象,('を含む装置','は含む装置'))
    def test_数式は既存候補へ(self):
        self.assertTrue(self.parse('「2+3」を計算して').既存候補)
    def test_HDS残差を無視しない(self):
        ir=公開HDSコンパイラ().コンパイル('「装置A」の電圧をVで調べて')
        r=会話を解釈(replace(ir,残差=(HDS残差('r','semantic_loss','条件','未解釈'),)))
        self.assertIsNone(r.要求)
    def test_HDS原文不一致を拒否(self):
        ir=公開HDSコンパイラ().コンパイル('「装置A」の電圧をVで調べて')
        self.assertIsNone(会話を解釈(replace(ir,原文='「装置B」の電圧をVで調べて')).要求)

if __name__=='__main__': unittest.main()
