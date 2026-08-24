from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_direct_relation_verifier import HDS直接関係検証
from minidora.k3_functional import K3相当能力核


def _条件値(relation, key: str) -> str:
    prefix = key + "="
    for raw in relation.条件:
        value = str(raw)
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return ""


def _関係(ir, kind: str):
    candidates = [
        relation
        for relation in ir.関係
        if str(relation.種別) == kind
        and str(relation.由来) in {"公開HDS Compiler", "共有言語基底P"}
        and relation.値状態.value == "確定"
    ]
    if len(candidates) != 1:
        raise AssertionError(f"expected exactly one canonical relation: {kind}, got {len(candidates)}")
    return candidates[0]


class 関係ScopeV04試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_否定activeを肯定関係へ潰さない(self) -> None:
        ir = self.compiler.コンパイル("Protein A does not inhibit Protein B.")
        relation = _関係(ir, "阻害")
        coords = ir.座標辞書()
        self.assertEqual(coords[relation.始点[0]].内容, "Protein A")
        self.assertEqual(coords[relation.終点[0]].内容, "Protein B")
        self.assertEqual(_条件値(relation, "極性"), "否定")
        self.assertFalse(
            any(
                str(item.種別) == "阻害"
                and str(item.由来) == "公開HDS Compiler"
                for item in ir.関係
            )
        )

    def test_否定passiveも意味方向と極性を保持する(self) -> None:
        ir = self.compiler.コンパイル("Protein A is not inhibited by Protein B.")
        relation = _関係(ir, "阻害")
        coords = ir.座標辞書()
        self.assertEqual(coords[relation.始点[0]].内容, "Protein B")
        self.assertEqual(coords[relation.終点[0]].内容, "Protein A")
        self.assertEqual(_条件値(relation, "極性"), "否定")

    def test_modalを主語へ取り込まず関係scopeへ保持する(self) -> None:
        ir = self.compiler.コンパイル("Protein A may inhibit Protein B.")
        relation = _関係(ir, "阻害")
        coords = ir.座標辞書()
        self.assertEqual(coords[relation.始点[0]].内容, "Protein A")
        self.assertEqual(coords[relation.終点[0]].内容, "Protein B")
        self.assertEqual(_条件値(relation, "極性"), "肯定")
        self.assertEqual(_条件値(relation, "様相"), "可能")

    def test_単一条件命題では既存関係へ条件scopeを付与する(self) -> None:
        ir = self.compiler.コンパイル("If condition X, Protein A inhibits Protein B.")
        relation = _関係(ir, "阻害")
        # 同一意味の関係を共有P側で二重生成せず、既存関係へscopeする。
        self.assertEqual(str(relation.由来), "公開HDS Compiler")
        self.assertEqual(_条件値(relation, "条件種別"), "条件")
        self.assertIn("condition X", _条件値(relation, "条件表層"))

    def test_Kへ否定関係とrelation_conditionsをそのまま渡す(self) -> None:
        ir = self.compiler.コンパイル("Protein A does not inhibit Protein B.")
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(ir, provenance=("fixture", "negative-doc"))
        facts = HDS証拠事実(core)
        negative = next(fact for fact in facts if str(fact.predicate) == "hds_relation_否定.阻害")
        provenance = {str(value) for value in negative.provenance}
        self.assertIn("relation_condition:極性=否定", provenance)
        self.assertIn("relation_effective_type:否定.阻害", provenance)

    def test_直接検証でも肯定と否定を別関係として扱う(self) -> None:
        negative_ir = self.compiler.コンパイル("Protein A does not inhibit Protein B.")
        positive_ir = self.compiler.コンパイル("Protein A inhibits Protein B.")
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(negative_ir, provenance=("fixture", "doc:1"))
        adapter.投入(negative_ir, provenance=("fixture", "doc:2"))

        candidate, diagnostics = HDS直接関係検証(core, {"NEG": negative_ir, "POS": positive_ir})
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.answer, "NEG")
        self.assertGreater(next(item for item in diagnostics if item.候補 == "NEG").得点, 0.0)
        self.assertEqual(next(item for item in diagnostics if item.候補 == "POS").得点, 0.0)


if __name__ == "__main__":
    unittest.main()
