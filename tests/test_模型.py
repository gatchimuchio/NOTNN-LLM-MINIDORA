import unittest

from minidora import (
    MINIDORA模型核,
    成立候補,
    言語状態,
    関係規則,
    ミニドラ,
)


class 模型核試験(unittest.TestCase):
    def test_文脈差が成立差へ到達する(self):
        core = MINIDORA模型核(
            (
                関係規則("日本首都", 文脈必須=frozenset({"日本"}), 候補必須=frozenset({"東京"}), 差=5),
                関係規則("仏首都", 文脈必須=frozenset({"フランス"}), 候補必須=frozenset({"パリ"}), 差=5),
            )
        )
        candidates = (
            成立候補("東京", 言語状態("東京", "自然言語:ja")),
            成立候補("パリ", 言語状態("パリ", "自然言語:ja")),
        )
        japan = core.評価言語状態(言語状態("日本 首都", "自然言語:ja"), candidates)
        france = core.評価言語状態(言語状態("フランス 首都", "自然言語:ja"), candidates)
        self.assertEqual(japan.最有力候補ID, "東京")
        self.assertEqual(france.最有力候補ID, "パリ")

    def test_同じ関係を複数文脈へ再利用する(self):
        core = MINIDORA模型核(
            (関係規則("日本関連", 文脈必須=frozenset({"日本"}), 候補必須=frozenset({"東京"}), 差=3),)
        )
        candidates = (
            成立候補("A", 言語状態("東京", "自然言語:ja")),
            成立候補("B", 言語状態("パリ", "自然言語:ja")),
        )
        first = core.評価言語状態(言語状態("日本 地理", "自然言語:ja"), candidates)
        second = core.評価言語状態(言語状態("日本 都市", "自然言語:ja"), candidates)
        self.assertEqual(first.最有力候補ID, "A")
        self.assertEqual(second.最有力候補ID, "A")

    def test_根拠差がなければ勝手に確定しない(self):
        core = MINIDORA模型核(())
        result = core.評価言語状態(
            言語状態("未知", "自然言語:ja"),
            (
                成立候補("A", 言語状態("候補A", "自然言語:ja")),
                成立候補("B", 言語状態("候補B", "自然言語:ja")),
            ),
        )
        self.assertIsNone(result.最有力候補ID)
        self.assertEqual(result.候補辞書(), {"A": 0, "B": 0})

    def test_プログラム言語も明示体系として扱える(self):
        core = MINIDORA模型核(
            (関係規則("return", 文脈必須=frozenset({"return"}), 候補必須=frozenset({"value"}), 差=2),)
        )
        result = core.評価言語状態(
            言語状態("return", "プログラム言語:Python"),
            (
                成立候補("value", 言語状態("value", "プログラム言語:Python")),
                成立候補("other", 言語状態("other", "プログラム言語:Python")),
            ),
        )
        self.assertEqual(result.最有力候補ID, "value")

    def test_runtimeが模型核入口を持つ(self):
        core = MINIDORA模型核(
            (関係規則("選択", 文脈必須=frozenset({"日本"}), 候補必須=frozenset({"東京"}), 差=4),)
        )
        body = ミニドラ(模型核_=core)
        result = body.言語評価("日本", ("東京", "パリ"))
        self.assertEqual(result.最有力候補ID, "候補1")
        self.assertEqual(result.候補辞書()["候補1"], 4)


if __name__ == "__main__":
    unittest.main()
