from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_data_k import HDSIR知識Adapter, HDS証拠事実
from minidora.hds_direct_relation_verifier import HDS直接関係検証
from minidora.hds_graph_reasoning import HDS意味Graph索引構築
from minidora.hds_relation_scope import HDS関係Scope一致, HDS関係Scope抽出, K事実関係Scope抽出
from minidora.k3_functional import K3相当能力核


def _meaning_relation(ir, kind: str):
    rows = [
        relation
        for relation in ir.関係
        if str(relation.種別) == kind
        and str(relation.由来) in {"公開HDS Compiler", "共有言語基底P"}
        and relation.値状態.value == "確定"
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one canonical relation {kind}, got {len(rows)}")
    return rows[0]


class 関係ScopeV05試験(unittest.TestCase):
    def setUp(self) -> None:
        self.compiler = 公開HDSコンパイラ()

    def test_modalと無条件は別scopeである(self) -> None:
        modal = _meaning_relation(self.compiler.コンパイル("Protein A may inhibit Protein B."), "阻害")
        plain = _meaning_relation(self.compiler.コンパイル("Protein A inhibits Protein B."), "阻害")
        self.assertFalse(HDS関係Scope一致(HDS関係Scope抽出(modal), HDS関係Scope抽出(plain)))

    def test_K事実からscopeを往復復元できる(self) -> None:
        ir = self.compiler.コンパイル("Protein A may inhibit Protein B.")
        relation = _meaning_relation(ir, "阻害")
        core = K3相当能力核()
        HDSIR知識Adapter(core).投入(ir, provenance=("fixture", "modal"))
        fact = next(f for f in HDS証拠事実(core) if str(f.predicate).startswith("hds_relation_") and "阻害" in str(f.predicate))
        self.assertTrue(HDS関係Scope一致(HDS関係Scope抽出(relation), K事実関係Scope抽出(fact)))
        self.assertIn("様相:可能", str(fact.predicate))
        self.assertIn("relation_scope_sensitive:true", {str(x) for x in fact.provenance})

    def test_modal候補を無条件Dataで直接証明しない(self) -> None:
        modal = self.compiler.コンパイル("Protein A may inhibit Protein B.")
        plain = self.compiler.コンパイル("Protein A inhibits Protein B.")
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(plain, provenance=("fixture", "plain:1"))
        adapter.投入(plain, provenance=("fixture", "plain:2"))
        candidate, diagnostics = HDS直接関係検証(core, {"MODAL": modal})
        self.assertIsNone(candidate)
        self.assertEqual(diagnostics[0].得点, 0.0)

    def test_modal候補は同scopeDataなら直接検証できる(self) -> None:
        modal = self.compiler.コンパイル("Protein A may inhibit Protein B.")
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(modal, provenance=("fixture", "modal:1"))
        adapter.投入(modal, provenance=("fixture", "modal:2"))
        candidate, diagnostics = HDS直接関係検証(core, {"MODAL": modal})
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.answer, "MODAL")
        self.assertGreater(diagnostics[0].得点, 0.0)

    def test_異なる条件表層を直接一致させない(self) -> None:
        condition_x = self.compiler.コンパイル("If condition X, Protein A inhibits Protein B.")
        condition_y = self.compiler.コンパイル("If condition Y, Protein A inhibits Protein B.")
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(condition_y, provenance=("fixture", "condition-y:1"))
        adapter.投入(condition_y, provenance=("fixture", "condition-y:2"))
        candidate, diagnostics = HDS直接関係検証(core, {"X": condition_x})
        self.assertIsNone(candidate)
        self.assertEqual(diagnostics[0].得点, 0.0)

    def test_scope付き関係はscope未対応汎用graphへ入れない(self) -> None:
        plain = self.compiler.コンパイル("Protein A inhibits Protein B.")
        modal = self.compiler.コンパイル("Protein C may inhibit Protein D.")
        core = K3相当能力核()
        adapter = HDSIR知識Adapter(core)
        adapter.投入(plain, provenance=("fixture", "plain"))
        adapter.投入(modal, provenance=("fixture", "modal"))
        graph = HDS意味Graph索引構築(core)
        # 無条件の一関係だけが汎用graphへ入る。scope付き辺は直接照合専用。
        self.assertEqual(graph.関係Fact数, 1)


if __name__ == "__main__":
    unittest.main()
