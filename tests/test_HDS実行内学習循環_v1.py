from __future__ import annotations

import unittest

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS駆動コア import HDS駆動コア
from minidora.HDS実行主体 import HDS終端
from minidora.HDS選択継承循環 import (
    回答成果名,
    参照記憶成果名,
    学習経験成果名,
    学習導出成果名,
    学習観測世代成果名,
)
from minidora.HDS選択実行内学習 import HDS選択学習導出
from minidora.参照 import 参照記録


class 学習参照供給器:
    名称 = "実行内学習試験参照"
    並列安全 = False

    def __init__(self):
        self.問合せ: list[str] = []

    def 検索(self, 問合せ, 上限=8):
        query = " ".join(str(問合せ).split())
        self.問合せ.append(query)
        low = query.casefold()
        if "molecule a" in low and "enzyme x" in low and "inhibit" in low:
            return (
                参照記録(
                    識別子="learned-a",
                    対象="Molecule A",
                    内容="Molecule A inhibits Enzyme X.",
                    由来="試験",
                    供給器=self.名称,
                    信頼=1.0,
                ),
            )
        return ()


class HDS実行内学習循環V1試験(unittest.TestCase):
    def setUp(self):
        self.構文化器 = 公開HDSコンパイラ()
        self.コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=32)
        self.問い = "Which molecule inhibits Enzyme X?"
        self.選択肢 = ("Molecule A", "Molecule B")

    def test_一経験だけで次観測を導出する(self):
        結果 = self.コア.選択実行(self.問い, self.選択肢, 初期参照=())
        self.assertEqual(結果.終端, HDS終端.保留)
        成果 = 結果.状態.成果辞書()
        経験 = 成果[学習経験成果名]
        導出 = 成果[学習導出成果名]
        self.assertEqual(len(経験), 1)
        self.assertIsInstance(導出, HDS選択学習導出)
        self.assertTrue(導出.観測要求)
        self.assertTrue(all("実行内学習" in x.provenance for x in 導出.観測要求))

    def test_同一回答内で記憶推論適応して再評価する(self):
        provider = 学習参照供給器()
        結果 = self.コア.選択実行(
            self.問い,
            self.選択肢,
            初期参照=(),
            参照供給器=provider,
        )
        self.assertEqual(結果.終端, HDS終端.採用, 結果.理由)
        成果 = 結果.状態.成果辞書()
        self.assertEqual(成果[回答成果名], "A")
        self.assertGreaterEqual(len(成果[学習経験成果名]), 2)
        self.assertGreaterEqual(int(成果[学習観測世代成果名]), 1)
        self.assertTrue(any("molecule a" in q.casefold() and "enzyme x" in q.casefold() for q in provider.問合せ))
        self.assertEqual(
            [x.作用ID for x in 結果.履歴[:3]],
            ["HDS継承/模型再評価", "HDS継承/追加参照", "HDS継承/模型再評価"],
        )
        memory = 成果[参照記憶成果名]
        learned = next(x for x in memory if x.識別子 == "learned-a")
        self.assertTrue(any(k == "hds_observation_id" and str(v).startswith("学習:") for k, v in learned.条件))

    def test_外部参照なしでは従来どおり推測せず保留する(self):
        結果 = self.コア.選択実行(self.問い, self.選択肢, 初期参照=())
        self.assertEqual(結果.終端, HDS終端.保留)
        self.assertNotIn(回答成果名, 結果.状態.成果辞書())


if __name__ == "__main__":
    unittest.main()
