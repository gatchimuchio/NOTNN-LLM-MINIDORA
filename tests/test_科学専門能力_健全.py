from __future__ import annotations
import math
import unittest
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, 値状態
from minidora.科学専門能力 import 科学専門能力解決

class 科学専門能力健全性試験(unittest.TestCase):
    def test_数値を変えた対生成閾値を解く(self):
        eps = 0.004
        target = 510998.95 ** 2 / eps / 1000000000.0
        choices = (f'{target:.3g} GeV', f'{target * 3:.3g} GeV', '2 GeV', '9 GeV')
        result = 科学専門能力解決(f'For head-on gamma-gamma creation of an electron-positron pair, background photon energy is {eps} eV. What high-energy photon threshold is required?', choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 0)

    def test_正解候補欠落なら推測しない(self):
        result = 科学専門能力解決('For head-on gamma-gamma creation of an electron-positron pair, background photon energy is 0.004 eV. What high-energy photon threshold is required?', ('1 GeV', '2 GeV', '3 GeV', '4 GeV'))
        self.assertIsNone(result)

    def test_ガウス則は別表現でも解く(self):
        choices = ('0', '4 pi', 'R^2', '1/R')
        result = 科学専門能力解決('A radial vector field has magnitude 1/r^2. Evaluate the volume integral of its divergence over a spherical volume enclosing the origin.', choices)
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 1)

    def test_世界知識問題は能力コードで答えない(self):
        result = 科学専門能力解決('Which city is the capital of France?', ('Paris', 'Lyon', 'Marseille', 'Nice'))
        self.assertIsNone(result)

    def test_相対論的媒質光速は形式則で解く(self):
        result = 科学専門能力解決('A light beam travels through glass with index of refraction n. The glass moves at velocity v in the same direction. With c=1, what is the observed speed of light?', ('(1-n*v)/(n-v)', '(1+n*v)/(n+v)', '1/n', '1'))
        self.assertIsNotNone(result)
        self.assertEqual(result.index, 1)

    def test_非関連入力へ誤発火しない(self):
        result = 科学専門能力解決('A spherical conductor is shown in a drawing. Which material is blue?', ('copper', 'wood', 'glass', 'paper'))
        self.assertIsNone(result)

class 科学専門能力接続試験(unittest.TestCase):
    def test_科学能力が通常選択問題を閉包できる(self):
        import minidora.hds_choice_runtime as runtime
        question = 'A radial vector field has magnitude 1/r^2. Evaluate the volume integral of its divergence over a sphere enclosing the origin.'
        rows = (
            HDS座標('choice:A', '目的.候補', '0', 値状態.確定),
            HDS座標('choice:B', '目的.候補', '4 pi', 値状態.確定),
            HDS座標('choice:C', '目的.候補', 'R^2', 値状態.確定),
            HDS座標('choice:D', '目的.候補', '1/R', 値状態.確定),
        )
        ir = HDSIR(
            原文=question,
            正規化文=question,
            認知世界ID='test:scientific-capability',
            座標=rows,
            関係=(),
            残差=(),
            意味作用履歴=(),
            実行核=HDS実行核('HDS_choice_selection'),
            参照必須=False,
            種別='knowledge_query',
            入力言語='en',
        )
        result = runtime.HDS選択推論実行(ir, (), コンパイル=None, 基礎能力核=None)
        self.assertEqual(result.状態, 'APPROVE')
        self.assertEqual(result.回答ラベル, 'B')
        self.assertEqual(result.専門作用起動数, 1)
        self.assertIn('MINIDORA_EXISTING_SCIENTIFIC_CAPABILITY', result.理由)

if __name__ == '__main__':
    unittest.main()
