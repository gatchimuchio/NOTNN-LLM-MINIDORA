from __future__ import annotations

import unittest

from minidora.hds_model_projection import 参照確定品質判定
from minidora.模型 import 内部言語状態, 文脈付き言語状態, 成立差, 模型結果, 関係寄与


def _result(*contributions: 関係寄与, reverse: bool = False) -> 模型結果:
    internal = 内部言語状態("", "自然言語:ja", frozenset())
    context = 文脈付き言語状態(
        internal,
        条件=("選択意図=反転",) if reverse else (),
    )
    return 模型結果(
        context,
        (成立差("A", 1, tuple(contributions)), 成立差("B", 0, ())),
        "A",
        (),
        (),
        参照最有力候補ID="A",
    )


class 参照確定品質試験(unittest.TestCase):
    def test_弱い一出典だけでは回答を閉じない(self):
        q = 参照確定品質判定(
            _result(関係寄与("候補共同参照", 1, ("再照合:r1:0:1",))),
            参照識別子=("r1",), 参照信頼=(1.0,),
        )
        self.assertFalse(q.閉包)
        self.assertEqual(q.理由, "SINGLE_WEAK_SOURCE")

    def test_弱証拠も二独立出典なら閉包できる(self):
        q = 参照確定品質判定(
            _result(関係寄与("候補共同参照", 2, ("再照合:r1:0:1", "再照合:r2:0:1"))),
            参照識別子=("r1", "r2"), 参照信頼=(0.2, 0.9),
        )
        self.assertTrue(q.閉包)
        self.assertEqual(q.理由, "MULTI_SOURCE_WEAK_EVIDENCE_CLOSED")

    def test_明示構造支持は一独立出典でも閉包する(self):
        q = 参照確定品質判定(
            _result(関係寄与("参照関係寄与", 2, ("参照:r1:2",))),
            参照識別子=("r1",), 参照信頼=(0.1,),
        )
        self.assertTrue(q.閉包)
        self.assertEqual(q.理由, "STRUCTURAL_EVIDENCE_CLOSED")

    def test_構造支持と反証は相殺せず留保する(self):
        q = 参照確定品質判定(
            _result(関係寄与("参照関係寄与", 1, ("参照:r1:2", "参照:r2:-2"))),
            参照識別子=("r1", "r2"), 参照信頼=(1.0, 1.0),
        )
        self.assertFalse(q.閉包)
        self.assertEqual(q.理由, "STRUCTURAL_EVIDENCE_CONFLICT")

    def test_同一弱出典の複製は独立証拠にならない(self):
        q = 参照確定品質判定(
            _result(関係寄与("候補共同参照", 2, ("再照合:r1:0:1", "再照合:r1:0:1"))),
            参照識別子=("r1",), 参照信頼=(1.0,),
        )
        self.assertFalse(q.閉包)

    def test_反転問題では構造差の符号を反転して読む(self):
        q = 参照確定品質判定(
            _result(関係寄与("参照関係寄与", 2, ("参照:r1:-2",)), reverse=True),
            参照識別子=("r1",), 参照信頼=(1.0,),
        )
        self.assertTrue(q.閉包)

    def test_反転aggregateだけでは出典追跡不能なので閉じない(self):
        q = 参照確定品質判定(
            _result(関係寄与("候補共同参照", 1, ("反転例外:0:0->2:3",)), reverse=True),
            参照識別子=("r1",), 参照信頼=(1.0,),
        )
        self.assertFalse(q.閉包)
        self.assertEqual(q.理由, "REVERSE_AGGREGATE_UNTRACEABLE")

    def test_信頼0の参照を証拠に数えない(self):
        q = 参照確定品質判定(
            _result(関係寄与("参照関係寄与", 2, ("参照:r1:2",))),
            参照識別子=("r1",), 参照信頼=(0.0,),
        )
        self.assertFalse(q.閉包)

    def test_参照順序で品質判定が変わらない(self):
        result = _result(関係寄与("候補共同参照", 2, ("再照合:r2:0:1", "再照合:r1:0:1")))
        a = 参照確定品質判定(result, 参照識別子=("r1", "r2"), 参照信頼=(0.2, 0.9))
        b = 参照確定品質判定(result, 参照識別子=("r2", "r1"), 参照信頼=(0.9, 0.2))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
