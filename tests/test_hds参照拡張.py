from __future__ import annotations

import unittest

from minidora.hds参照拡張 import HDS候補被覆優先統合
from minidora.参照 import 参照記録


def rec(source: str, choice: str | None = None) -> 参照記録:
    conditions = (("hds_query_choice", choice),) if choice is not None else ()
    return 参照記録(source, source, source, "test", "test", 条件=conditions)


class HDSReferenceExtensionTest(unittest.TestCase):
    def test_候補sourceをgenericより先に予算へ残す(self):
        out = HDS候補被覆優先統合(
            (rec("generic1"), rec("generic2")),
            (rec("A", "A"), rec("B", "B"), rec("C", "C"), rec("D", "D")),
            ("A", "B", "C", "D"),
            4,
        )
        self.assertEqual({row.識別子 for row in out}, {"A", "B", "C", "D"})

    def test_同一sourceはquery_provenanceだけ統合する(self):
        out = HDS候補被覆優先統合(
            (rec("shared", "A"),),
            (rec("shared", "B"),),
            ("A", "B"),
            4,
        )
        self.assertEqual(len(out), 1)
        labels = {v for k, v in out[0].条件 if k == "hds_query_choice"}
        self.assertEqual(labels, {"A", "B"})


if __name__ == "__main__":
    unittest.main()
