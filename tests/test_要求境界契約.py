from __future__ import annotations
from dataclasses import dataclass
import unittest
from minidora.要求境界契約 import 被覆台帳印, 要求境界契約印, 要求境界契約版

@dataclass(frozen=True)
class 被覆:
    種別: str
    識別子: str
    参照先: tuple[str, ...]

class 要求境界契約試験(unittest.TestCase):
    def test_版と決定性(self):
        self.assertEqual(要求境界契約版, 'MINIDORA-要求境界契約-v0.1')
        rows=(被覆('目的','g1',('a',)), 被覆('出力','g1',('g1',)))
        coverage=被覆台帳印(rows)
        a=要求境界契約印(原文='現在の依頼',計画印='plan',要求被覆印=coverage,目的印='goal',素材印='資料')
        b=要求境界契約印(原文='現在の依頼',計画印='plan',要求被覆印=coverage,目的印='goal',素材印='資料')
        self.assertEqual(a,b); self.assertEqual(len(a),64)

    def test_現在依頼_計画_被覆_目的_素材の差を同一視しない(self):
        rows=(被覆('目的','g1',('a',)), 被覆('出力','g1',('g1',)))
        coverage=被覆台帳印(rows)
        base=dict(原文='現在の依頼',計画印='plan',要求被覆印=coverage,目的印='goal',素材印='資料')
        seal=要求境界契約印(**base)
        variants=(
            {**base,'原文':'前の依頼'},
            {**base,'計画印':'other-plan'},
            {**base,'要求被覆印':被覆台帳印((rows[0],))},
            {**base,'目的印':'other-goal'},
            {**base,'素材印':'other-資料'},
        )
        self.assertTrue(all(要求境界契約印(**x)!=seal for x in variants))

    def test_空被覆と空計画印を拒否(self):
        with self.assertRaisesRegex(ValueError,'要求被覆'):
            被覆台帳印(())
        with self.assertRaisesRegex(ValueError,'計画印'):
            要求境界契約印(原文='x',計画印='',要求被覆印='cov')

if __name__=='__main__': unittest.main()
