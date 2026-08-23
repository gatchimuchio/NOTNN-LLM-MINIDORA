from __future__ import annotations

import unittest

from minidora.semantic_tokens import 意味語
from minidora.言語基底_英語 import 英語基本形, 英語関係概念, 英語関係族


class 英語言語基底試験(unittest.TestCase):
    def test_科学文で頻出する過去分詞を基本形へ戻す(self) -> None:
        self.assertEqual(英語基本形("produced"), "produce")
        self.assertEqual(英語基本形("generated"), "generate")
        self.assertEqual(英語基本形("inhibited"), "inhibit")
        self.assertEqual(英語基本形("used"), "use")
        self.assertEqual(英語基本形("led"), "lead")

    def test_名詞形容詞の派生語も関係基本形へ接続する(self) -> None:
        self.assertEqual(英語基本形("inhibition"), "inhibit")
        self.assertEqual(英語基本形("inhibitory"), "inhibit")
        self.assertEqual(英語基本形("activation"), "activate")
        self.assertEqual(英語基本形("production"), "produce")
        self.assertEqual(英語基本形("generation"), "generate")
        self.assertEqual(英語基本形("dependence"), "depend")
        self.assertEqual(英語基本形("correlation"), "correlate")

    def test_同義関係語を同じ日本語概念へ寄せる(self) -> None:
        self.assertEqual(英語関係概念("inhibited"), "阻害")
        self.assertEqual(英語関係概念("inhibition"), "阻害")
        self.assertEqual(英語関係概念("suppresses"), "阻害")
        self.assertEqual(英語関係概念("blocked"), "阻害")
        self.assertEqual(英語関係概念("produced"), "生成")
        self.assertEqual(英語関係概念("production"), "生成")
        self.assertEqual(英語関係概念("generated"), "生成")
        self.assertEqual(英語関係概念("generation"), "生成")

    def test_意味語は表面基本形と関係概念を同時に保持する(self) -> None:
        produced = 意味語("The enzyme produced a metabolite")
        generated = 意味語("The enzyme generated a metabolite")
        inhibition = 意味語("catalytic inhibition")
        self.assertIn("produce", produced)
        self.assertIn("generate", generated)
        self.assertIn("inhibit", inhibition)
        self.assertIn("rel:生成", produced)
        self.assertIn("rel:生成", generated)
        self.assertIn("rel:阻害", inhibition)

    def test_関係族は世界知識ではなく一般関係だけを持つ(self) -> None:
        families = 英語関係族()
        self.assertIn("因果", families)
        self.assertIn("阻害", families)
        self.assertIn("包含", families)
        self.assertNotIn("protein", {word for words in families.values() for word in words})
        self.assertNotIn("quantum", {word for words in families.values() for word in words})


if __name__ == "__main__":
    unittest.main()
