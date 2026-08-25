from __future__ import annotations

import unittest

from minidora.模型 import 成立候補, 言語状態, 標準模型核
from minidora.言語構造 import 言語関係抽出
from minidora.言語基底_英語 import 英語関係族


class 模型関係域試験(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = 標準模型核()

    def _winner(self, context: str, a: str, b: str, *, history=()):
        result = self.kernel.評価言語状態(
            言語状態(context, "自然言語:en"),
            (
                成立候補("A", 言語状態(a, "自然言語:en")),
                成立候補("B", 言語状態(b, "自然言語:en")),
            ),
            履歴=tuple(言語状態(item, "自然言語:en") for item in history),
        )
        return result

    def test_有向関係は逆向きを同一視しない(self) -> None:
        result = self._winner("A causes B", "A causes B", "B causes A")
        self.assertEqual(result.最有力候補ID, "A")
        self.assertGreater(result.候補辞書()["A"], result.候補辞書()["B"])

    def test_肯定と否定を別構造として保持する(self) -> None:
        positive = self.kernel.言語対応.内部化(言語状態("A causes B", "自然言語:en"))
        negative = self.kernel.言語対応.内部化(言語状態("A does not cause B", "自然言語:en"))
        self.assertNotEqual(positive.構造署名, negative.構造署名)
        self.assertTrue(positive.関係構造[0].肯定)
        self.assertFalse(negative.関係構造[0].肯定)
        self.assertEqual(self._winner("A causes B", "A causes B", "A does not cause B").最有力候補ID, "A")

    def test_履歴順序を集合和へ潰さない(self) -> None:
        forward = self._winner("current", "alpha", "beta", history=("alpha", "beta"))
        reverse = self._winner("current", "alpha", "beta", history=("beta", "alpha"))
        self.assertEqual(forward.最有力候補ID, "B")
        self.assertEqual(reverse.最有力候補ID, "A")

    def test_条件付き関係を無条件関係と同一視しない(self) -> None:
        conditioned = 言語関係抽出("if catalyst, A causes B", "自然言語:en")
        plain = 言語関係抽出("A causes B", "自然言語:en")
        self.assertTrue(conditioned[0].条件)
        self.assertFalse(plain[0].条件)
        result = self._winner(
            "if catalyst, A causes B",
            "if catalyst, A causes B",
            "if inhibitor, A causes B",
        )
        self.assertEqual(result.最有力候補ID, "A")

    def test_一般関係族は個別世界知識なしで構造化できる(self) -> None:
        representatives = {
            "因果": "causes", "増加": "increases", "減少": "decreases", "阻害": "inhibits",
            "活性化": "activates", "生成": "produces", "要求": "requires", "包含": "contains",
            "使用": "uses", "防止": "prevents", "相関": "correlates with", "結合": "binds to",
            "相互作用": "interacts with", "構成": "consists of", "所属": "belongs to",
            "位置": "is located in", "由来": "derives from",
        }
        self.assertEqual(set(representatives), set(英語関係族()))
        for kind, phrase in representatives.items():
            with self.subTest(kind=kind):
                relations = 言語関係抽出(f"A {phrase} B", "自然言語:en")
                self.assertTrue(any(item.種別 == kind for item in relations))

    def test_模型核はHDSを必要とせず関係域を形成する(self) -> None:
        self.assertGreaterEqual(len(self.kernel.関係群), 6)
        module_names = {type(item).__module__ for item in self.kernel.関係群}
        self.assertTrue(all("hds" not in name.casefold() for name in module_names))


if __name__ == "__main__":
    unittest.main()
