from __future__ import annotations

import unittest

from minidora import 公開HDSコンパイラ
from minidora.HDS資料K import HDSIR知識適合器, HDS修飾Fact, HDS証拠事実, HDS証拠状態複製
from minidora.HDS実行系射影 import HDSK資料射影
from minidora.K3機能 import K3相当能力核


class 関係修飾V18試験(unittest.TestCase):
    def setUp(self) -> None:
        self.構文化器 = 公開HDSコンパイラ()

    def _投入(self, text: str, 情報源: str = "doc") -> K3相当能力核:
        模型核 = K3相当能力核()
        ir = HDSK資料射影(self.構文化器.コンパイル(text))
        HDSIR知識適合器(模型核).投入(ir, provenance=("fixture", 情報源))
        return 模型核

    def test_mayを様相可能の修飾Factとして保持する(self) -> None:
        模型核 = self._投入("Compound A may inhibit Enzyme X.")
        facts = HDS証拠事実(模型核, 極性=True, 修飾=(("様相", "可能"),))
        rows = [fact for fact in facts if fact.predicate == 'hds_関係_阻害']
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], HDS修飾Fact)
        self.assertEqual(getattr(rows[0], '修飾', ()), (("様相", "可能"),))
        self.assertIn('関係_修飾:様相=可能', rows[0].provenance)

    def test_mustをmayと別identityとして保持する(self) -> None:
        模型核 = K3相当能力核()
        適合器 = HDSIR知識適合器(模型核)
        適合器.投入(HDSK資料射影(self.構文化器.コンパイル("Compound A may inhibit Enzyme X.")), provenance=("fixture", "modal"))
        適合器.投入(HDSK資料射影(self.構文化器.コンパイル("Compound A must inhibit Enzyme X.")), provenance=("fixture", "modal"))

        possible = [f for f in HDS証拠事実(模型核, 修飾=(("様相", "可能"),)) if f.predicate == 'hds_関係_阻害']
        necessary = [f for f in HDS証拠事実(模型核, 修飾=(("様相", "必要"),)) if f.predicate == 'hds_関係_阻害']
        self.assertEqual(len(possible), 1)
        self.assertEqual(len(necessary), 1)
        self.assertNotEqual(possible[0].fact_id, necessary[0].fact_id)

    def test_条件範囲を別identityとして保持する(self) -> None:
        模型核 = self._投入("If condition X, Compound A inhibits Enzyme X.")
        all_証拠 = HDS証拠事実(模型核, 極性=None, 修飾=None)
        scoped = [
            f for f in all_証拠
            if f.predicate == 'hds_関係_阻害' and ('条件範囲', "If condition X") in tuple(getattr(f, '修飾', ()))
        ]
        self.assertEqual(len(scoped), 1)

    def test_修飾Factを無条件canonical_Kへ入れない(self) -> None:
        模型核 = self._投入("Compound A may inhibit Enzyme X.")
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(模型核.K.find('hds_関係_阻害', pattern, 極性=True), [])
        default = HDS証拠事実(模型核)
        self.assertFalse(any(f.predicate == 'hds_関係_阻害' for f in default))

    def test_無条件関係は従来canonical_Kへ入る(self) -> None:
        模型核 = self._投入("Compound A inhibits Enzyme X.")
        pattern = ("Compound A", "→", "Enzyme X")
        self.assertEqual(len(模型核.K.find('hds_関係_阻害', pattern, 極性=True)), 1)
        self.assertTrue(any(f.predicate == 'hds_関係_阻害' for f in HDS証拠事実(模型核)))

    def test_否定かつmodalも極性と修飾を同時保持する(self) -> None:
        模型核 = self._投入("Compound A may not inhibit Enzyme X.")
        facts = HDS証拠事実(模型核, 極性=False, 修飾=(("様相", "可能"),))
        rows = [f for f in facts if f.predicate == 'hds_関係_阻害']
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].極性)

    def test_証拠cloneで修飾identityを失わない(self) -> None:
        情報源 = self._投入("Compound A may inhibit Enzyme X.")
        destination = K3相当能力核()
        HDS証拠状態複製(情報源, destination)
        src = [f.fact_id for f in HDS証拠事実(情報源, 修飾=(("様相", "可能"),)) if f.predicate == 'hds_関係_阻害']
        dst = [f.fact_id for f in HDS証拠事実(destination, 修飾=(("様相", "可能"),)) if f.predicate == 'hds_関係_阻害']
        self.assertEqual(src, dst)


if __name__ == "__main__":
    unittest.main()
