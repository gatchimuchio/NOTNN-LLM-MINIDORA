from __future__ import annotations
import unittest
from minidora.能力作用則 import 関係寄与, 証拠状態寄与, 証拠状態合計寄与
from minidora.HDS中間表現 import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.HDS模型射影 import HDSMINIDORA模型評価
from minidora.模型 import (
    LLM成立規定版, LLM構成再現区別, MINIDORA模型核, 成立候補, 言語状態,
    関係規則, 意味連続関係, 標準模型核,
)
from minidora.言語構造 import 言語関係構造

def 関係(kind,s,o,pred,positive=True):
    return 言語関係構造(kind,frozenset({s}),frozenset({o}),positive,(),frozenset({pred}))

def ir(text,coords=(),relations=(),*,言語="en"):
    return HDSIR(
        原文=text, 正規化文=text, 認知世界ID="v3-test", 座標=tuple(coords), 関係=tuple(relations),
        残差=(), 意味作用履歴=(), 実行核=HDS実行核(), 種別="knowledge_query", 入力言語=言語,
    )

class 構成再現v3試験(unittest.TestCase):
    def test_v3正本と7条件(self):
        self.assertEqual(LLM成立規定版,"2026-08-27-成立規定-3")
        self.assertEqual(len(LLM構成再現区別),7)

    def test_問い専用関係を検索述語で資料へ接続する(self):
        target=関係("問い適合","enzyme","beta","stabilize")
        証拠=関係("作用","enzyme","beta","stabilize")
        self.assertGreater(関係寄与(target,証拠),0)

    def test_1参照内の複数関係を最大1件へ潰さない(self):
        targets=(関係("作用","a","b","p1"),関係("作用","c","d","p2"))
        証拠=(関係("作用","a","b","p1"),関係("作用","c","d","p2"))
        self.assertEqual(証拠状態寄与(targets,証拠),2)
        self.assertEqual(証拠状態合計寄与(targets,証拠),4)

    def test_形成済み関係を一般作用と分離する(self):
        formed=関係規則("形成済み",候補必須=frozenset({"form"}),差=3)
        模型核=MINIDORA模型核((意味連続関係(),),形成済み関係群=(formed,),能力作用群=())
        結果=模型核.評価言語状態(
            言語状態("question"),
            (成立候補("A",言語状態("formed")),成立候補("B",言語状態("other"))),
        )
        self.assertEqual(結果.最有力候補ID,"A")
        self.assertTrue(any(cp.段階=="形成済み関係" for cp in 結果.検査点))

    def test_検査点が再活性される(self):
        結果=標準模型核().評価言語状態(
            言語状態("which"),
            (成立候補("A",言語状態("alpha")),成立候補("B",言語状態("beta")),成立候補("C",言語状態("gamma"))),
            参照状態=(言語状態("beta",識別子="r"),),
        )
        self.assertGreaterEqual(結果.統計.検査点再活性数,1)
        self.assertGreaterEqual(結果.統計.大域再照合数,1)
        self.assertTrue(any(cp.段階.startswith("RECONCILE_") for cp in 結果.検査点))

    def test_反証だけで正の候補へしない(self):
        a=言語状態("alpha",関係構造=(関係("作用","x","alpha","p",True),))
        b=言語状態("beta")
        ref=言語状態("r",識別子="r",関係構造=(関係("作用","x","alpha","p",False),))
        結果=標準模型核().評価言語状態(言語状態("which"),(成立候補("A",a),成立候補("B",b)),参照状態=(ref,))
        self.assertIsNone(結果.参照最有力候補ID)

    def test_反転は相対例外差として正に戻す(self):
        a=言語状態("alpha",関係構造=(関係("作用","x","alpha","p"),))
        b=言語状態("beta",関係構造=(関係("作用","x","beta","p"),))
        c=言語状態("gamma",関係構造=(関係("作用","x","gamma","p"),))
        refs=(
            言語状態("r1",識別子="r1",関係構造=(関係("作用","x","alpha","p"),)),
            言語状態("r2",識別子="r2",関係構造=(関係("作用","x","beta","p"),)),
        )
        結果=標準模型核().評価言語状態(
            言語状態("except"),(成立候補("A",a),成立候補("B",b),成立候補("C",c)),
            条件=("選択意図=反転",),参照状態=refs,
        )
        self.assertEqual(結果.参照最有力候補ID,"C")

    def test_knowledge_選択肢はMINIDORA能力核自身が終端形成する(self):
        question=ir("alpha alpha alpha which")
        a=ir("alpha alpha alpha")
        b=ir("beta",(
            HDS座標("s","対象","enzyme"),HDS座標("o","目的","beta"),
        ),(HDS関係("r",("s",),("o",),"問い適合",("検索述語=stabilize",)),))
        資料=ir('証拠',(
            HDS座標("s","対象","enzyme"),HDS座標("o","目的","beta"),
        ),(HDS関係("e",("s",),("o",),"作用",("検索述語=stabilize",)),))
        結果=HDSMINIDORA模型評価(question,{"A":a,"B":b},(資料,))
        self.assertEqual(結果.状態,"APPROVE")
        self.assertEqual(結果.回答ラベル,"B")
        self.assertIn('MINIDORA_模型_模型核_SELECTED',結果.理由)
        self.assertIn('MINIDORA_能力_模型核_TERMINAL',結果.理由)
        self.assertNotIn("HDS_OUTPUT_APPROVED",結果.理由)
        self.assertNotIn('HDS_OUTPUT_ONLY_境界',結果.理由)
        self.assertIsNone(結果.HDS判断)
        self.assertIsNone(結果.MINIDORA出力)
        self.assertIn('能力_射影_V1',結果.理由)

    def test_参照差なしはMINIDORAがSUSPENDする(self):
        結果=HDSMINIDORA模型評価(ir("which"),{"A":ir("alpha"),"B":ir("beta")},())
        self.assertEqual(結果.状態,"SUSPEND")
        self.assertIsNone(結果.回答ラベル)
        self.assertIn("NO_GUESS",結果.理由)
        self.assertIn('MINIDORA_模型_模型核_NO_参照_CONTRIBUTION',結果.理由)
        self.assertIsNone(結果.HDS判断)
        self.assertIsNone(結果.MINIDORA出力)

    def test_候補順参照順に依存しない(self):
        模型核=標準模型核();q=言語状態("which")
        a=成立候補("A",言語状態("alpha",関係構造=(関係("作用","x","alpha","p"),)))
        b=成立候補("B",言語状態("beta",関係構造=(関係("作用","x","beta","p"),)))
        r1=言語状態("r1",識別子="r1",関係構造=(関係("作用","x","beta","p"),));r2=言語状態("r2",識別子="r2")
        x=模型核.評価言語状態(q,(a,b),参照状態=(r1,r2));y=模型核.評価言語状態(q,(b,a),参照状態=(r2,r1))
        self.assertEqual(x.候補辞書(),y.候補辞書());self.assertEqual(x.参照候補辞書(),y.参照候補辞書())

if __name__ == "__main__": unittest.main()
