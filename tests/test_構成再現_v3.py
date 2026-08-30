from __future__ import annotations
import unittest
from minidora.能力作用則 import 関係寄与, 証拠状態寄与, 証拠状態合計寄与
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_model_projection import HDSMINIDORA模型評価
from minidora.模型 import (
    LLM成立規定版, LLM構成再現区別, MINIDORA模型核, 成立候補, 言語状態,
    関係規則, 意味連続関係, 標準模型核,
)
from minidora.言語構造 import 言語関係構造

def relation(kind,s,o,pred,positive=True):
    return 言語関係構造(kind,frozenset({s}),frozenset({o}),positive,(),frozenset({pred}))

def ir(text,coords=(),relations=(),*,language="en"):
    return HDSIR(
        原文=text, 正規化文=text, 認知世界ID="v3-test", 座標=tuple(coords), 関係=tuple(relations),
        残差=(), 意味作用履歴=(), 実行核=HDS実行核(), 種別="knowledge_query", 入力言語=language,
    )

class 構成再現v3試験(unittest.TestCase):
    def test_v3正本と7条件(self):
        self.assertEqual(LLM成立規定版,"2026-08-27-成立規定-3")
        self.assertEqual(len(LLM構成再現区別),7)

    def test_問い専用関係を検索述語でDataへ接続する(self):
        target=relation("問い適合","enzyme","beta","stabilize")
        evidence=relation("作用","enzyme","beta","stabilize")
        self.assertGreater(関係寄与(target,evidence),0)

    def test_1参照内の複数関係を最大1件へ潰さない(self):
        targets=(relation("作用","a","b","p1"),relation("作用","c","d","p2"))
        evidence=(relation("作用","a","b","p1"),relation("作用","c","d","p2"))
        self.assertEqual(証拠状態寄与(targets,evidence),2)
        self.assertEqual(証拠状態合計寄与(targets,evidence),4)

    def test_形成済み関係を一般作用と分離する(self):
        formed=関係規則("形成済み",候補必須=frozenset({"form"}),差=3)
        core=MINIDORA模型核((意味連続関係(),),形成済み関係群=(formed,),能力作用群=())
        result=core.評価言語状態(
            言語状態("question"),
            (成立候補("A",言語状態("formed")),成立候補("B",言語状態("other"))),
        )
        self.assertEqual(result.最有力候補ID,"A")
        self.assertTrue(any(cp.段階=="FORMED_RELATIONS" for cp in result.checkpoint))

    def test_checkpointが再活性される(self):
        result=標準模型核().評価言語状態(
            言語状態("which"),
            (成立候補("A",言語状態("alpha")),成立候補("B",言語状態("beta")),成立候補("C",言語状態("gamma"))),
            参照状態=(言語状態("beta",識別子="r"),),
        )
        self.assertGreaterEqual(result.統計.checkpoint再活性数,1)
        self.assertGreaterEqual(result.統計.大域再照合数,1)
        self.assertTrue(any(cp.段階.startswith("RECONCILE_") for cp in result.checkpoint))

    def test_反証だけで正の候補へしない(self):
        a=言語状態("alpha",関係構造=(relation("作用","x","alpha","p",True),))
        b=言語状態("beta")
        ref=言語状態("r",識別子="r",関係構造=(relation("作用","x","alpha","p",False),))
        result=標準模型核().評価言語状態(言語状態("which"),(成立候補("A",a),成立候補("B",b)),参照状態=(ref,))
        self.assertIsNone(result.参照最有力候補ID)

    def test_反転は相対例外差として正に戻す(self):
        a=言語状態("alpha",関係構造=(relation("作用","x","alpha","p"),))
        b=言語状態("beta",関係構造=(relation("作用","x","beta","p"),))
        c=言語状態("gamma",関係構造=(relation("作用","x","gamma","p"),))
        refs=(
            言語状態("r1",識別子="r1",関係構造=(relation("作用","x","alpha","p"),)),
            言語状態("r2",識別子="r2",関係構造=(relation("作用","x","beta","p"),)),
        )
        result=標準模型核().評価言語状態(
            言語状態("except"),(成立候補("A",a),成立候補("B",b),成立候補("C",c)),
            条件=("選択意図=反転",),参照状態=refs,
        )
        self.assertEqual(result.参照最有力候補ID,"C")

    def test_knowledge_choiceはMINIDORA能力核自身が終端形成する(self):
        question=ir("alpha alpha alpha which")
        a=ir("alpha alpha alpha")
        b=ir("beta",(
            HDS座標("s","対象","enzyme"),HDS座標("o","目的","beta"),
        ),(HDS関係("r",("s",),("o",),"問い適合",("検索述語=stabilize",)),))
        data=ir("evidence",(
            HDS座標("s","対象","enzyme"),HDS座標("o","目的","beta"),
        ),(HDS関係("e",("s",),("o",),"作用",("検索述語=stabilize",)),))
        result=HDSMINIDORA模型評価(question,{"A":a,"B":b},(data,))
        self.assertEqual(result.状態,"APPROVE")
        self.assertEqual(result.回答ラベル,"B")
        self.assertIn("MINIDORA_MODEL_CORE_SELECTED",result.理由)
        self.assertIn("MINIDORA_CAPABILITY_CORE_TERMINAL",result.理由)
        self.assertNotIn("HDS_OUTPUT_APPROVED",result.理由)
        self.assertNotIn("HDS_OUTPUT_ONLY_BOUNDARY",result.理由)
        self.assertIsNone(result.HDS判断)
        self.assertIsNone(result.MINIDORA出力)
        self.assertIn("CAPABILITY_PROJECTION_V1",result.理由)

    def test_参照差なしはMINIDORAがSUSPENDする(self):
        result=HDSMINIDORA模型評価(ir("which"),{"A":ir("alpha"),"B":ir("beta")},())
        self.assertEqual(result.状態,"SUSPEND")
        self.assertIsNone(result.回答ラベル)
        self.assertIn("NO_GUESS",result.理由)
        self.assertIn("MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION",result.理由)
        self.assertIsNone(result.HDS判断)
        self.assertIsNone(result.MINIDORA出力)

    def test_候補順参照順に依存しない(self):
        core=標準模型核();q=言語状態("which")
        a=成立候補("A",言語状態("alpha",関係構造=(relation("作用","x","alpha","p"),)))
        b=成立候補("B",言語状態("beta",関係構造=(relation("作用","x","beta","p"),)))
        r1=言語状態("r1",識別子="r1",関係構造=(relation("作用","x","beta","p"),));r2=言語状態("r2",識別子="r2")
        x=core.評価言語状態(q,(a,b),参照状態=(r1,r2));y=core.評価言語状態(q,(b,a),参照状態=(r2,r1))
        self.assertEqual(x.候補辞書(),y.候補辞書());self.assertEqual(x.参照候補辞書(),y.参照候補辞書())

if __name__ == "__main__": unittest.main()
