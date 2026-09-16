from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.hds_data_k import HDSIR知識適合器, HDS証拠事実
from minidora.HDS実行系射影 import HDSK資料射影
from minidora.k3_functional import K3相当能力核


class 極性保持V17試験(unittest.TestCase):
    def setUp(self) -> None:
        self.構文化器 = 公開HDSコンパイラ()

    def test_否定関係を資料射影で保持する(self) -> None:
        full = self.構文化器.コンパイル("Compound A does not inhibit Enzyme X.")
        projected = HDSK資料射影(full)
        negative = [
            関係 for 関係 in projected.関係
            if str(関係.種別) == "阻害" and "極性=否定" in tuple(str(x) for x in 関係.条件)
        ]
        self.assertTrue(negative)

    def test_否定関係をFact_極性_falseへ写す(self) -> None:
        projected = HDSK資料射影(self.構文化器.コンパイル("Compound A does not inhibit Enzyme X."))
        模型核 = K3相当能力核()
        HDSIR知識適合器(模型核).投入(projected, provenance=("fixture", "negative"))

        negative = 模型核.K.find(
            'hds_関係_阻害',
            ("Compound A", "→", "Enzyme X"),
            極性=False,
        )
        positive = 模型核.K.find(
            'hds_関係_阻害',
            ("Compound A", "→", "Enzyme X"),
            極性=True,
        )
        self.assertEqual(len(negative), 1)
        self.assertEqual(positive, [])
        self.assertIn('関係_極性:negative', negative[0].provenance)

    def test_正負の同一関係をKで別Factとして共存できる(self) -> None:
        模型核 = K3相当能力核()
        適合器 = HDSIR知識適合器(模型核)
        positive_ir = HDSK資料射影(self.構文化器.コンパイル("Compound A inhibits Enzyme X."))
        negative_ir = HDSK資料射影(self.構文化器.コンパイル("Compound A does not inhibit Enzyme X."))
        適合器.投入(positive_ir, provenance=("fixture", "positive"))
        適合器.投入(negative_ir, provenance=("fixture", "negative"))

        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(len(模型核.K.find('hds_関係_阻害', pattern, 極性=True)), 1)
        self.assertEqual(len(模型核.K.find('hds_関係_阻害', pattern, 極性=False)), 1)
        self.assertTrue(模型核.K.contradictions_for('hds_関係_阻害', pattern))

    def test_既定証拠viewへnegativeを混ぜず監査viewでは保持する(self) -> None:
        projected = HDSK資料射影(self.構文化器.コンパイル("Compound A does not inhibit Enzyme X."))
        模型核 = K3相当能力核()
        HDSIR知識適合器(模型核).投入(projected, provenance=("fixture", "negative"))

        default_証拠 = HDS証拠事実(模型核)
        negative_証拠 = HDS証拠事実(模型核, 極性=False)
        all_証拠 = HDS証拠事実(模型核, 極性=None)
        self.assertFalse(any(f.predicate == 'hds_関係_阻害' and not f.極性 for f in default_証拠))
        self.assertTrue(any(f.predicate == 'hds_関係_阻害' and not f.極性 for f in negative_証拠))
        self.assertGreater(len(all_証拠), len(default_証拠))

    def test_modal関係は消さず無条件canonical_Kへ昇格しない(self) -> None:
        projected = HDSK資料射影(self.構文化器.コンパイル("Compound A may inhibit Enzyme X."))
        self.assertTrue(any(str(関係.種別) == "阻害" for 関係 in projected.関係))

        模型核 = K3相当能力核()
        HDSIR知識適合器(模型核).投入(projected, provenance=("fixture", "modal"))
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(模型核.K.find('hds_関係_阻害', pattern, 極性=True), [])
        self.assertFalse(any(f.predicate == 'hds_関係_阻害' for f in HDS証拠事実(模型核)))
        qualified = HDS証拠事実(模型核, 極性=True, 修飾=(("様相", "可能"),))
        self.assertTrue(any(f.predicate == 'hds_関係_阻害' for f in qualified))


if __name__ == "__main__":
    unittest.main()
