from __future__ import annotations

import unittest

from minidora.能力状態差循環 import MINIDORA能力状態差模型核
from minidora.模型 import 成立候補, 言語状態, 関係寄与


class _初回変化作用:
    名称 = "初回変化作用"

    def 評価群(self, 文脈, 候補群):
        return {
            "B": 関係寄与("初回変化:B", 1, ("開始:B",)),
            "C": 関係寄与("初回変化:C", 1, ("開始:C",)),
        }


class _正寄与再作用:
    名称 = "正寄与再作用"

    def 評価群(self, 文脈, 候補群):
        return {}

    def 再評価群(self, 文脈, 候補群, 循環番号):
        return {
            "B": 関係寄与(
                f"正寄与:{循環番号}",
                1,
                (f"正根拠:{循環番号}",),
            )
        }


class _負寄与再作用:
    名称 = "負寄与再作用"

    def 評価群(self, 文脈, 候補群):
        return {}

    def 再評価群(self, 文脈, 候補群, 循環番号):
        return {
            "B": 関係寄与(
                f"負寄与:{循環番号}",
                -1,
                (f"負根拠:{循環番号}",),
            )
        }


class _首位保持関係:
    名称 = "首位保持関係"

    def 評価(self, 文脈, 候補):
        if 候補.識別子 == "A":
            return 関係寄与(self.名称, 10, ("首位:A",))
        return None


class _再作用面観測:
    名称 = "再作用面観測"
    観測: list[tuple[str, ...]] = []

    def 評価群(self, 文脈, 候補群):
        return {}

    def 再評価群(self, 文脈, 候補群, 循環番号):
        self.__class__.観測.append(tuple(候補ID for 候補ID, _ in 候補群))
        return {}


class 能力模型核状態差再作用補強試験(unittest.TestCase):
    def test_得点不変でも寄与構造差が続けば再作用を継続する(self) -> None:
        模型核 = MINIDORA能力状態差模型核(
            (),
            能力作用群=(
                _初回変化作用(),
                _正寄与再作用(),
                _負寄与再作用(),
            ),
            最大再作用回数=3,
        )
        結果 = 模型核.評価言語状態(
            言語状態("問い"),
            (
                成立候補("A", 言語状態("候補A")),
                成立候補("B", 言語状態("候補B")),
                成立候補("C", 言語状態("候補C")),
            ),
        )

        # 各再作用では +1 / -1 が同時追加されるためBの得点は変わらない。
        # それでも寄与構造は毎回変化しているので、得点差だけで循環を打ち切らない。
        self.assertEqual(結果.統計.再作用回数, 3)
        self.assertGreaterEqual(結果.統計.寄与状態再利用数, 6)
        self.assertTrue(any(保存点.段階 == "RECONCILE_3" for 保存点 in 結果.検査点))

    def test_現在首位を保ちながら全変化候補を再作用面へ残す(self) -> None:
        _再作用面観測.観測 = []
        模型核 = MINIDORA能力状態差模型核(
            (_首位保持関係(),),
            能力作用群=(
                _初回変化作用(),
                _再作用面観測(),
            ),
            最大再作用回数=1,
        )
        模型核.評価言語状態(
            言語状態("問い"),
            (
                成立候補("A", 言語状態("候補A", 識別子="A")),
                成立候補("B", 言語状態("候補B", 識別子="B")),
                成立候補("C", 言語状態("候補C", 識別子="C")),
            ),
        )

        self.assertEqual(_再作用面観測.観測, [("A", "B", "C")])


if __name__ == "__main__":
    unittest.main()
