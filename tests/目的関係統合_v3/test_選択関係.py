from dataclasses import dataclass,replace
from unittest import TestCase
from minidora.駆動系.選択関係 import 言語関係を節へ,選択関係を評価
from minidora.駆動系.契約 import 関係変換契約,関係項,関係資源契約

@dataclass(frozen=True)
class 言語関係:
    種別:str
    始点:frozenset
    終点:frozenset
    肯定:bool=True
    条件:tuple=()
    述語:frozenset=frozenset()

def 関係(種,始='甲',終='乙',肯定=True):
    return 言語関係(種,frozenset({始}),frozenset({終}),肯定)

class 選択関係試験(TestCase):
    def test_連言の一節だけでは成立しない(self):
        一,二=関係('原因'),関係('必要')
        結果=選択関係を評価('p','w',(('A',(一,二)),),(('r',(一,)),))
        self.assertIsNone(結果.一意成立);self.assertEqual(結果.候補[0].状態,'未観測')
        self.assertTrue(結果.候補[0].不足)
    def test_全節支持から成立(self):
        一,二=関係('原因'),関係('必要')
        結果=選択関係を評価('p','w',(('A',(一,二)),('B',(関係('違う'),))),
            (('r',(一,二)),))
        self.assertEqual(結果.一意成立,'A')
    def test_反証は未観測と別に保持(self):
        一=関係('原因')
        結果=選択関係を評価('p','w',(('A',(一,)),),(('r',(replace(一,肯定=False),)),))
        self.assertEqual(結果.候補[0].状態,'反証');self.assertIsNone(結果.一意成立)
    def test_相対得点を受け取らず証明しない(self):
        結果=選択関係を評価('p','w',(('A',(関係('原因'),)),),())
        self.assertIsNone(結果.一意成立)
    def test_対象なしは成立でなく対象未構成(self):
        結果=選択関係を評価('p','w',(('A',()),),())
        self.assertEqual(結果.候補[0].状態,'対象未構成')
    def test_同じ出典の複製で証拠を増やさない(self):
        一=関係('原因')
        結果=選択関係を評価('p','w',(('A',(一,)),),(('r',(一,一)),('r',(一,))))
        self.assertEqual(len(結果.候補[0].証明[0].回答[0].根拠),1)
    def test_二つの成立候補から勝手に一つを選ばない(self):
        一=関係('原因')
        結果=選択関係を評価('p','w',(('A',(一,)),('B',(一,))),(('r',(一,)),))
        self.assertIsNone(結果.一意成立)
    def test_型付き規則で多段導出して学習する(self):
        一,二,三=関係('前提'),関係('中間'),関係('到達')
        def 規則(名前,前,後):
            x=関係項('x','意味端点',変数=True,束縛域='s')
            y=関係項('y','意味端点',変数=True,束縛域='s')
            def 抽象(節):return replace(言語関係を節へ(節),引数=(('始点',x),('終点',y)))
            return 関係変換契約(名前,(抽象(前),),抽象(後),('外部規則:'+名前,))
        規=(規則('r1',一,二),規則('r2',二,三))
        初=選択関係を評価('p','w',(('A',(三,)),),(('r',(一,)),),変換=規)
        self.assertEqual(初.一意成立,'A');self.assertGreater(len(初.学習提案.形成),0)
        次=選択関係を評価('p2','w2',(('Z',(関係('到達','別甲','別乙'),)),),
            (('new',(関係('前提','別甲','別乙'),)),),変換=規,学習状態=初.学習提案)
        self.assertEqual(次.一意成立,'Z');self.assertTrue(次.候補[0].使用形成)
    def test_条件を落として適用しない(self):
        一=関係('原因');対象=replace(一,条件=(frozenset({'高温'}),))
        結果=選択関係を評価('p','w',(('A',(対象,)),),(('r',(一,)),))
        self.assertIsNone(結果.一意成立)
    def test_観測事実が入力上限を越えても例外化せず未完了にする(self):
        対象=関係('原因','甲','乙')
        観測=tuple((f'r{i}',(関係('別関係',f'甲{i}',f'乙{i}'),)) for i in range(513))
        結果=選択関係を評価('p','w',(('A',(対象,)),),観測)
        self.assertIn('観測関係の入力窓上限',結果.未完了)
        self.assertIsNone(結果.一意成立)

    def test_全候補共有予算を越えて成立扱いしない(self):
        一=関係('原因')
        結果=選択関係を評価('p','w',(('A',(一,)),('B',(一,))),(('r',(一,)),),資源=関係資源契約(最大照合=1))
        self.assertTrue(結果.未完了);self.assertIsNone(結果.一意成立)

class 反転選択試験(TestCase):
    def test_明示反証された候補を選ぶ(self):
        一,二=関係('原因'),関係('必要')
        結果=選択関係を評価('p','w',(('A',(一,)),('B',(二,))),
            (('r',(一,replace(二,肯定=False))),),反転=True)
        self.assertEqual(結果.一意成立,'B')
    def test_未観測を反証へしない(self):
        結果=選択関係を評価('p','w',(('A',(関係('原因'),)),),(),反転=True)
        self.assertIsNone(結果.一意成立)
    def test_連言の一節の反証で全体を反証する(self):
        一,二=関係('原因'),関係('必要')
        結果=選択関係を評価('p','w',(('A',(一,二)),),
            (('r',(一,replace(二,肯定=False))),),反転=True)
        self.assertEqual(結果.一意成立,'A')
    def test_矛盾証拠では反転でも保留する(self):
        一=関係('原因')
        結果=選択関係を評価('p','w',(('A',(一,)),),
            (('r',(一,replace(一,肯定=False))),),反転=True)
        self.assertIsNone(結果.一意成立);self.assertEqual(結果.候補[0].状態,'競合')
