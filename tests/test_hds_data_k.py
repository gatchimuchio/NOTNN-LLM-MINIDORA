from __future__ import annotations

import unittest

from minidora.hds_data_k import HDSIR知識Adapter
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差
from minidora.k3_functional import K3相当能力核


class HDSDataK試験(unittest.TestCase):
    def test_取得DataはHDS_IRから構造FactとしてKへ入る(self) -> None:
        ir = HDSIR(
            原文="Foo binds Bar when Baz is absent.",
            正規化文="Foo binds Bar when Baz is absent.",
            認知世界ID="cw:test",
            座標=(
                HDS座標("src", "source_text", "Foo binds Bar when Baz is absent."),
                HDS座標("raw", "対象.原文保持", "Foo binds Bar when Baz is absent."),
                HDS座標("foo", "対象.実体", "Foo"),
                HDS座標("bar", "対象.実体", "Bar"),
                HDS座標("baz", "対象.実体", "Baz is absent"),
            ),
            関係=(
                HDS関係("r1", ("foo",), ("bar",), "作用"),
                HDS関係("r2", ("baz",), ("foo", "bar"), "条件"),
            ),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核(),
            種別="意味構造",
            閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
            入力言語="en",
        )
        core = K3相当能力核()
        result = HDSIR知識Adapter(core).投入(ir, provenance=("web", "https://example.test"))

        self.assertEqual(result.関係事実数, 2)
        self.assertEqual(result.座標事実数, 3)
        self.assertGreaterEqual(result.追加事実数, 5)
        facts = tuple(core.K._facts.values())
        self.assertTrue(any(f.predicate == "hds_relation_条件" and "Baz is absent" in f.args for f in facts))
        self.assertTrue(any(f.predicate == "hds_relation_作用" and "Foo" in f.args and "Bar" in f.args for f in facts))
        self.assertFalse(any(f.predicate == "retrieved_document" for f in facts))
        self.assertFalse(any(f.predicate == "hds_coordinate" and f.args[0] in {"source_text", "対象.原文保持"} for f in facts))

    def test_残差も捨てずKへ保持する(self) -> None:
        ir = HDSIR(
            原文="It changes.",
            正規化文="It changes.",
            認知世界ID="cw:test",
            座標=(HDS座標("src", "対象.原文保持", "It changes."),),
            関係=(),
            残差=(HDS残差("res:1", "coreference_unresolved", "It", "参照先未確定"),),
            意味作用履歴=(),
            実行核=HDS実行核(),
            種別="意味構造",
            閉包状態="PARTIALLY_CLOSED",
            入力言語="en",
        )
        core = K3相当能力核()
        result = HDSIR知識Adapter(core).投入(ir)
        self.assertEqual(result.残差数, 1)
        self.assertTrue(core.K.find("hds_residual"))
        self.assertFalse(core.K.find("hds_coordinate"))


if __name__ == "__main__":
    unittest.main()
