from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_runtime_projection import HDSKData射影
from minidora.k3_functional import K3相当能力核


class PolarityPreservationV17試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_否定関係をData射影で保持する(self) -> None:
        full = self.compiler.コンパイル("Compound A does not inhibit Enzyme X.")
        projected = HDSKData射影(full)
        negative = [
            relation for relation in projected.関係
            if str(relation.種別) == "阻害" and "極性=否定" in tuple(str(x) for x in relation.条件)
        ]
        self.assertTrue(negative)

    def test_否定関係をFact_polarity_falseへ写す(self) -> None:
        projected = HDSKData射影(self.compiler.コンパイル("Compound A does not inhibit Enzyme X."))
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(projected, provenance=("fixture", "negative"))

        negative = core.K.find(
            "hds_relation_阻害",
            ("Compound A", "→", "Enzyme X"),
            polarity=False,
        )
        positive = core.K.find(
            "hds_relation_阻害",
            ("Compound A", "→", "Enzyme X"),
            polarity=True,
        )
        self.assertEqual(len(negative), 1)
        self.assertEqual(positive, [])
        self.assertIn("relation_polarity:negative", negative[0].provenance)

    def test_正負の同一関係をKで別Factとして共存できる(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        positive_ir = HDSKData射影(self.compiler.コンパイル("Compound A inhibits Enzyme X."))
        negative_ir = HDSKData射影(self.compiler.コンパイル("Compound A does not inhibit Enzyme X."))
        adapter.投入(positive_ir, provenance=("fixture", "positive"))
        adapter.投入(negative_ir, provenance=("fixture", "negative"))

        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(len(core.K.find("hds_relation_阻害", pattern, polarity=True)), 1)
        self.assertEqual(len(core.K.find("hds_relation_阻害", pattern, polarity=False)), 1)
        self.assertTrue(core.K.contradictions_for("hds_relation_阻害", pattern))

    def test_既定証拠viewへnegativeを混ぜず監査viewでは保持する(self) -> None:
        projected = HDSKData射影(self.compiler.コンパイル("Compound A does not inhibit Enzyme X."))
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(projected, provenance=("fixture", "negative"))

        default_evidence = HDS証拠事実(core)
        negative_evidence = HDS証拠事実(core, 極性=False)
        all_evidence = HDS証拠事実(core, 極性=None)
        self.assertFalse(any(f.predicate == "hds_relation_阻害" and not f.polarity for f in default_evidence))
        self.assertTrue(any(f.predicate == "hds_relation_阻害" and not f.polarity for f in negative_evidence))
        self.assertGreater(len(all_evidence), len(default_evidence))

    def test_modal関係は消さず無条件canonical_Kへ昇格しない(self) -> None:
        projected = HDSKData射影(self.compiler.コンパイル("Compound A may inhibit Enzyme X."))
        self.assertTrue(any(str(relation.種別) == "阻害" for relation in projected.関係))

        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(projected, provenance=("fixture", "modal"))
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(core.K.find("hds_relation_阻害", pattern, polarity=True), [])
        self.assertFalse(any(f.predicate == "hds_relation_阻害" for f in HDS証拠事実(core)))
        qualified = HDS証拠事実(core, 極性=True, 修飾=(("様相", "可能"),))
        self.assertTrue(any(f.predicate == "hds_relation_阻害" for f in qualified))


if __name__ == "__main__":
    unittest.main()
