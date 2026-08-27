from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS座標, HDS関係, HDS残差, HDS実行核, 値状態
from minidora.hds_model_projection import HDSMINIDORA模型評価


def ir(text, coords=(), rels=(), residuals=(), *, kind="knowledge_query"):
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="hds-j-test",
        座標=tuple(coords),
        関係=tuple(rels),
        残差=tuple(residuals),
        意味作用履歴=(),
        実行核=HDS実行核(),
        入力言語="en",
        種別=kind,
    )


def candidate(name, pred="stabilize", positive=True):
    conditions = (f"検索述語={pred}", "極性=否定") if not positive else (f"検索述語={pred}",)
    return ir(
        name,
        (HDS座標("s", "対象.始点", "enzyme"), HDS座標("o", "対象.終点", name)),
        (HDS関係("r", ("s",), ("o",), "作用", conditions),),
    )


def evidence(name, pred="stabilize", positive=True):
    return candidate(name, pred, positive)


def question(*, reverse=False, residual=False):
    cond = ["検索述語=stabilize", "不足位置=終点"]
    if reverse:
        cond.append("選択意図=反転")
    return ir(
        "Which option?",
        (
            HDS座標("s", "対象.始点", "enzyme"),
            HDS座標("u", "目的.未知終点", "option", 値状態.未観測),
        ),
        (HDS関係("q", ("s",), ("u",), "問い適合", tuple(cond), 値状態.未観測),),
        (HDS残差("loss", "semantic_loss", "?", "unresolved"),) if residual else (),
    )


class HDS判断主体試験(unittest.TestCase):
    def test_HDS_Jが最終権限を持ち一意な完全証拠を採用する(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        result = HDSMINIDORA模型評価(q, c, (evidence("beta"),), 参照識別子=("source-b",), 参照信頼=(1.0,))
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        self.assertIsNotNone(result.HDS判断)
        self.assertEqual(result.HDS判断.運用状態, "COMMIT")
        self.assertIn("HDS_JUDGEMENT_SELECTED", result.理由)

    def test_同一sourceが複数候補を支持したらCommitしない(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        data = ir(
            "both",
            (
                HDS座標("s", "対象.始点", "enzyme"),
                HDS座標("a", "対象.終点", "alpha"),
                HDS座標("b", "対象.終点", "beta"),
            ),
            (
                HDS関係("ra", ("s",), ("a",), "作用", ("検索述語=stabilize",)),
                HDS関係("rb", ("s",), ("b",), "作用", ("検索述語=stabilize",)),
            ),
        )
        result = HDSMINIDORA模型評価(q, c, (data,), 参照識別子=("shared",))
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)

    def test_独立sourceが競合候補を完全支持したら順位づけせず保留する(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        result = HDSMINIDORA模型評価(q, c, (evidence("alpha"), evidence("beta")), 参照識別子=("sa", "sb"))
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIn("HDS_COMPETING_EVIDENCE", result.理由)

    def test_完全支持と完全反証が共存したら矛盾を保持して保留する(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        result = HDSMINIDORA模型評価(
            q,
            c,
            (evidence("alpha"), evidence("alpha", positive=False)),
            参照識別子=("pos", "neg"),
        )
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIn("HDS_UNRESOLVED_CONTRADICTION", result.理由)

    def test_弱いscope支持は保持するがCommitしない(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        weak = ir(
            "weak",
            (HDS座標("s", "対象.始点", "enzyme"), HDS座標("o", "対象.終点", "alpha")),
            (HDS関係("r", ("s",), ("o",), "作用", ("検索述語=stabilize", "条件scope=special")),),
        )
        result = HDSMINIDORA模型評価(q, c, (weak,), 参照識別子=("weak-source",))
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIn(result.HDS判断.候補状態[0].状態, {"WEAK_EVIDENCE", "UNSUPPORTED"})

    def test_反転は最低得点投票でなくN_minus_1消去で閉じる(self):
        q = question(reverse=True)
        c = {"A": candidate("alpha"), "B": candidate("beta"), "C": candidate("gamma")}
        result = HDSMINIDORA模型評価(q, c, (evidence("alpha"), evidence("beta")), 参照識別子=("sa", "sb"))
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "C")
        self.assertIn("HDS_EXCEPTION_N_MINUS_ONE", result.理由)

    def test_semantic_lossはCommit前に保留する(self):
        q = question(residual=True)
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        result = HDSMINIDORA模型評価(q, c, (evidence("alpha"),), 参照識別子=("sa",))
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIn("HDS_FRAME_UNCLOSED", result.理由)

    def test_候補順と参照順で判断が変わらない(self):
        q = question()
        a = candidate("alpha")
        b = candidate("beta")
        ra = evidence("alpha")
        x = HDSMINIDORA模型評価(q, {"A": a, "B": b}, (ra,), 参照識別子=("sa",))
        y = HDSMINIDORA模型評価(q, {"B": b, "A": a}, (ra,), 参照識別子=("sa",))
        self.assertEqual((x.状態, x.回答ラベル, x.HDS判断.候補状態), (y.状態, y.回答ラベル, y.HDS判断.候補状態))

    def test_Cの参照最大候補は提案でありJの最終権限ではない(self):
        q = question()
        c = {"A": ir("alpha distinctive"), "B": candidate("beta")}
        token_refs = tuple(ir("alpha distinctive") for _ in range(4))
        relation_ref = ir(
            "beta relation",
            (HDS座標("s", "対象.始点", "enzyme"), HDS座標("o", "対象.終点", "beta")),
            (HDS関係("r", ("s",), ("o",), "作用", ("検索述語=stabilize",)),),
        )
        refs = (*token_refs, relation_ref)
        ids = ("ta1", "ta2", "ta3", "ta4", "rb")
        result = HDSMINIDORA模型評価(q, c, refs, 参照識別子=ids)
        self.assertEqual(result.模型結果.参照最有力候補ID, "A")
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        self.assertEqual(result.HDS判断.選択候補ID, "B")

    def test_参照なしをHDSが勝手に承認しない(self):
        q = question()
        c = {"A": candidate("alpha"), "B": candidate("beta")}
        result = HDSMINIDORA模型評価(q, c, ())
        self.assertEqual(result.状態, "SUSPEND")
        self.assertIsNone(result.回答ラベル)


if __name__ == "__main__":
    unittest.main()