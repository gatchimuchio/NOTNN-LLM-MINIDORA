from __future__ import annotations
import math
import unittest
from minidora.HDS中間表現 import HDSIR, HDS実行核, HDS座標, 値状態
from minidora.科学専門能力 import 科学専門能力解決

class 科学専門能力健全性試験(unittest.TestCase):
    def test_数値を変えた対生成閾値を解く(self):
        eps = 0.004
        target = 510998.95 ** 2 / eps / 1000000000.0
        choices = (f'{target:.3g} GeV', f'{target * 3:.3g} GeV', '2 GeV', '9 GeV')
        結果 = 科学専門能力解決(f'For head-on gamma-gamma creation of an electron-positron pair, background photon energy is {eps} eV. What high-energy photon threshold is required?', choices)
        self.assertIsNotNone(結果)
        self.assertEqual(結果.index, 0)

    def test_正解候補欠落なら推測しない(self):
        結果 = 科学専門能力解決('For head-on gamma-gamma creation of an electron-positron pair, background photon energy is 0.004 eV. What high-energy photon threshold is required?', ('1 GeV', '2 GeV', '3 GeV', '4 GeV'))
        self.assertIsNone(結果)

    def test_ガウス則は別表現でも解く(self):
        choices = ('0', '4 pi', 'R^2', '1/R')
        結果 = 科学専門能力解決('A radial vector field has magnitude 1/r^2. Evaluate the volume integral of its divergence over a spherical volume enclosing the origin.', choices)
        self.assertIsNotNone(結果)
        self.assertEqual(結果.index, 1)

    def test_世界知識問題は能力コードで答えない(self):
        結果 = 科学専門能力解決('Which city is the capital of France?', ('Paris', 'Lyon', 'Marseille', 'Nice'))
        self.assertIsNone(結果)

    def test_相対論的媒質光速は形式則で解く(self):
        結果 = 科学専門能力解決('A light beam travels through glass with index of refraction n. The glass moves at velocity v in the same direction. With c=1, what is the observed speed of light?', ('(1-n*v)/(n-v)', '(1+n*v)/(n+v)', '1/n', '1'))
        self.assertIsNotNone(結果)
        self.assertEqual(結果.index, 1)

    def test_非関連入力へ誤発火しない(self):
        結果 = 科学専門能力解決('A spherical conductor is shown in a drawing. Which material is blue?', ('copper', 'wood', 'glass', 'paper'))
        self.assertIsNone(結果)

class 科学専門能力明示接続試験(unittest.TestCase):
    def test_科学能力は明示接続時だけ利用できる(self):
        import minidora.HDS選択実行系 as 実行系
        from minidora.科学専門能力統合 import 科学専門能力を通常MINIDORAへ接続
        original = 実行系.HDS選択推論実行
        科学専門能力を通常MINIDORAへ接続(実行系)
        question = 'A radial vector field has magnitude 1/r^2. Evaluate the volume integral of its divergence over a sphere enclosing the origin.'
        rows = (
            HDS座標('選択肢:A', '目的.候補', '0', 値状態.確定),
            HDS座標('選択肢:B', '目的.候補', '4 pi', 値状態.確定),
            HDS座標('選択肢:C', '目的.候補', 'R^2', 値状態.確定),
            HDS座標('選択肢:D', '目的.候補', '1/R', 値状態.確定),
        )
        ir = HDSIR(
            原文=question,
            正規化文=question,
            認知世界ID='test:scientific-能力',
            座標=rows,
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核('HDS_選択肢_selection'),
            参照必須=False,
            種別='knowledge_query',
            入力言語='en',
        )
        try:
            結果 = 実行系.HDS選択推論実行(ir, (), コンパイル=None, 基礎能力核=None)
            self.assertEqual(結果.状態, 'APPROVE')
            self.assertEqual(結果.回答ラベル, 'B')
            self.assertEqual(結果.専門作用起動数, 1)
            self.assertIn('MINIDORA_EXISTING_SCIENTIFIC_能力', 結果.理由)
        finally:
            実行系.HDS選択推論実行 = original

if __name__ == '__main__':
    unittest.main()
