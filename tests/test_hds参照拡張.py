from __future__ import annotations

import unittest

from minidora.hds参照拡張 import HDS候補被覆優先統合, HDS参照履歴統合, HDS観測窓更新
from minidora.参照 import 参照記録


def rec(情報源: str, 選択肢: str | None = None) -> 参照記録:
    conditions = (('hds_query_選択肢', 選択肢),) if 選択肢 is not None else ()
    return 参照記録(情報源, 情報源, 情報源, "test", "test", 条件=conditions)


class HDS参照ExtensionTest(unittest.TestCase):
    def test_候補情報源をgenericより先に予算へ残す(self):
        out = HDS候補被覆優先統合(
            (rec("generic1"), rec("generic2")),
            (rec("A", "A"), rec("B", "B"), rec("C", "C"), rec("D", "D")),
            ("A", "B", "C", "D"),
            4,
        )
        self.assertEqual({row.識別子 for row in out}, {"A", "B", "C", "D"})

    def test_満杯の旧窓でも新観測を再評価窓へ入れる(self):
        現行 = tuple(rec(f"old{i}") for i in range(4))
        新規 = (rec("newA", "A"), rec("newB", "B"), rec("newX"))
        窓 = HDS観測窓更新(現行, 新規, ("A", "B"), 4)
        self.assertEqual(len(窓), 4)
        self.assertIn("newA", {x.識別子 for x in 窓})
        self.assertIn("newB", {x.識別子 for x in 窓})
        self.assertTrue({"A", "B"}.issubset({
            v for x in 窓 for k, v in x.条件 if k == "hds_query_選択肢"
        }))

    def test_参照履歴は窓から外れた旧観測も保持する(self):
        現行 = (rec("old1"), rec("old2"))
        新規 = (rec("new1"), rec("new2"))
        履歴 = HDS参照履歴統合(現行, 新規)
        self.assertEqual({x.識別子 for x in 履歴}, {"old1", "old2", "new1", "new2"})

    def test_同一情報源はquery_provenanceだけ統合する(self):
        out = HDS候補被覆優先統合(
            (rec("shared", "A"),),
            (rec("shared", "B"),),
            ("A", "B"),
            4,
        )
        self.assertEqual(len(out), 1)
        labels = {v for k, v in out[0].条件 if k == 'hds_query_選択肢'}
        self.assertEqual(labels, {"A", "B"})


if __name__ == "__main__":
    unittest.main()
