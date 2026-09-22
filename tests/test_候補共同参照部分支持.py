from __future__ import annotations

import unittest

from minidora.模型 import 候補共同参照作用, 内部言語状態, 文脈付き言語状態
from minidora.言語構造 import 言語関係構造, 意味列
from minidora.意味字句 import 意味語


def _関係(始点: str, 種別: str, 終点: str, *, 肯定: bool = True) -> 言語関係構造:
    return 言語関係構造(
        種別,
        意味語(始点),
        意味語(終点),
        肯定,
        (),
        意味語(種別),
    )


def _状態(本文: str, 関係群=()) -> 内部言語状態:
    return 内部言語状態(
        本文,
        "自然言語:en",
        意味語(本文),
        本文,
        意味列(本文),
        tuple(関係群),
        True,
        True,
    )


class 候補共同参照部分支持試験(unittest.TestCase):
    def test_一意な部分支持差だけを弱い参照差として保持する(self) -> None:
        現在 = _状態("Which candidate fits?")
        参照 = _状態("Alpha inhibits X.", (_関係("Alpha", "阻害", "X"),))
        文脈 = 文脈付き言語状態(現在, 参照状態=(参照,))
        候補A = _状態(
            "Alpha",
            (_関係("Alpha", "阻害", "X"), _関係("Alpha", "活性化", "Y")),
        )
        候補B = _状態(
            "Beta",
            (_関係("Beta", "阻害", "X"), _関係("Beta", "活性化", "Z")),
        )
        結果 = 候補共同参照作用().評価群(文脈, (("A", 候補A), ("B", 候補B)))
        self.assertEqual(set(結果), {"A"})
        self.assertEqual(結果["A"].差, 1)
        self.assertIn("部分支持差:1/2", 結果["A"].根拠[0])

    def test_部分支持が同率なら候補差へ昇格しない(self) -> None:
        現在 = _状態("Which candidate fits?")
        参照A = _状態("Alpha inhibits X.", (_関係("Alpha", "阻害", "X"),))
        参照B = _状態("Beta inhibits X.", (_関係("Beta", "阻害", "X"),))
        文脈 = 文脈付き言語状態(現在, 参照状態=(参照A, 参照B))
        候補A = _状態("Alpha", (_関係("Alpha", "阻害", "X"), _関係("Alpha", "活性化", "Y")))
        候補B = _状態("Beta", (_関係("Beta", "阻害", "X"), _関係("Beta", "活性化", "Z")))
        self.assertEqual(候補共同参照作用().評価群(文脈, (("A", 候補A), ("B", 候補B))), {})

    def test_明示反証を含む候補は部分支持差へ昇格しない(self) -> None:
        現在 = _状態("Which candidate fits?")
        参照1 = _状態("Alpha inhibits X.", (_関係("Alpha", "阻害", "X", 肯定=False),))
        参照2 = _状態("Alpha activates Y.", (_関係("Alpha", "活性化", "Y"),))
        文脈 = 文脈付き言語状態(現在, 参照状態=(参照1, 参照2))
        候補A = _状態("Alpha", (_関係("Alpha", "阻害", "X"), _関係("Alpha", "活性化", "Y")))
        候補B = _状態("Beta", (_関係("Beta", "阻害", "X"), _関係("Beta", "活性化", "Z")))
        self.assertEqual(候補共同参照作用().評価群(文脈, (("A", 候補A), ("B", 候補B))), {})


if __name__ == "__main__":
    unittest.main()
