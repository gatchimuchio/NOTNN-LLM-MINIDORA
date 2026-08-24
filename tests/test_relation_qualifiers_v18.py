from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_data_k import HDSIR知識Adapter, HDS修飾Fact, HDS証拠事実, HDS証拠状態複製
from minidora.hds_runtime_projection import HDSKData射影
from minidora.k3_functional import K3相当能力核


class RelationQualifiersV18試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def _投入(self, text: str, source: str = "doc") -> K3相当能力核:
        core = K3相当能力核()
        ir = HDSKData射影(self.compiler.コンパイル(text))
        HDSIR知識Adapter(core).投入(ir, provenance=("fixture", source))
        return core

    def test_mayを様相可能の修飾Factとして保持する(self) -> None:
        core = self._投入("Compound A may inhibit Enzyme X.")
        facts = HDS証拠事実(core, 極性=True, 修飾=(("様相", "可能"),))
        rows = [fact for fact in facts if fact.predicate == "hds_relation_阻害"]
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], HDS修飾Fact)
        self.assertEqual(getattr(rows[0], "qualifiers", ()), (("様相", "可能"),))
        self.assertIn("relation_qualifier:様相=可能", rows[0].provenance)

    def test_mustをmayと別identityとして保持する(self) -> None:
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(HDSKData射影(self.compiler.コンパイル("Compound A may inhibit Enzyme X.")), provenance=("fixture", "modal"))
        adapter.投入(HDSKData射影(self.compiler.コンパイル("Compound A must inhibit Enzyme X.")), provenance=("fixture", "modal"))

        possible = [f for f in HDS証拠事実(core, 修飾=(("様相", "可能"),)) if f.predicate == "hds_relation_阻害"]
        necessary = [f for f in HDS証拠事実(core, 修飾=(("様相", "必要"),)) if f.predicate == "hds_relation_阻害"]
        self.assertEqual(len(possible), 1)
        self.assertEqual(len(necessary), 1)
        self.assertNotEqual(possible[0].fact_id, necessary[0].fact_id)

    def test_条件scopeを別identityとして保持する(self) -> None:
        core = self._投入("If condition X, Compound A inhibits Enzyme X.")
        all_evidence = HDS証拠事実(core, 極性=None, 修飾=None)
        scoped = [
            f for f in all_evidence
            if f.predicate == "hds_relation_阻害" and ("条件scope", "If condition X") in tuple(getattr(f, "qualifiers", ()))
        ]
        self.assertEqual(len(scoped), 1)

    def test_修飾Factを無条件canonical_Kへ入れない(self) -> None:
        core = self._投入("Compound A may inhibit Enzyme X.")
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(core.K.find("hds_relation_阻害", pattern, polarity=True), [])
        default = HDS証拠事実(core)
        self.assertFalse(any(f.predicate == "hds_relation_阻害" for f in default))

    def test_無条件関係は従来canonical_Kへ入る(self) -> None:
        core = self._投入("Compound A inhibits Enzyme X.")
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(len(core.K.find("hds_relation_阻害", pattern, polarity=True)), 1)
        self.assertTrue(any(f.predicate == "hds_relation_阻害" for f in HDS証拠事実(core)))

    def test_否定かつmodalも極性と修飾を同時保持する(self) -> None:
        core = self._投入("Compound A may not inhibit Enzyme X.")
        facts = HDS証拠事実(core, 極性=False, 修飾=(("様相", "可能"),))
        rows = [f for f in facts if f.predicate == "hds_relation_阻害"]
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].polarity)

    def test_証拠cloneで修飾identityを失わない(self) -> None:
        source = self._投入("Compound A may inhibit Enzyme X.")
        destination = K3相当能力核()
        HDS証拠状態複製(source, destination)
        src = [f.fact_id for f in HDS証拠事実(source, 修飾=(("様相", "可能"),)) if f.predicate == "hds_relation_阻害"]
        dst = [f.fact_id for f in HDS証拠事実(destination, 修飾=(("様相", "可能"),)) if f.predicate == "hds_relation_阻害"]
        self.assertEqual(src, dst)


if __name__ == "__main__":
    unittest.main()
