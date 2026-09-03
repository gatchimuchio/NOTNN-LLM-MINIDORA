from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from minidora.ハッカソン import (
    JSONL監査保存先,
    固定ニュース供給器,
    ニュース項目,
    ハッカソンチャット,
    監査台帳,
)


class _基礎ミニドラ:
    def 応答(self, 問合せ: str) -> str:
        return f"基礎応答:{問合せ}"


class ハッカソンチャット試験(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime.now(timezone.utc)
        self.items = (
            ニュース項目("n1", "半導体企業が新製品を発表", "企業は新しい半導体製品を発表した。詳細仕様は今後公開される。", "Example A", "https://example.com/a", now),
            ニュース項目("n2", "鉄道会社が新路線計画を公表", "鉄道会社は新路線の計画を公表した。開業時期は検討中としている。", "Example B", "https://example.com/b", now),
            ニュース項目("n3", "研究チームが観測結果を公開", "研究チームは観測結果を公開した。追加検証を続けるとしている。", "Example C", "https://example.com/c", now),
            ニュース項目("n4", "自治体が防災訓練を実施", "自治体は防災訓練を実施した。", "Example D", "https://example.com/d", now),
        )
        self.chat = ハッカソンチャット(
            ニュース供給器_=固定ニュース供給器(self.items),
            基礎ミニドラ=_基礎ミニドラ(),
        )

    def test_ニュースから要約へ文脈接続できる(self) -> None:
        first = self.chat.応答("今日のニュースは？", セッションID="demo")
        self.assertEqual(first.経路, "ニュース")
        self.assertIn("半導体企業が新製品を発表", first.本文)
        self.assertTrue(self.chat.監査台帳.検証(first.追跡ID))

        second = self.chat.応答("要約して", セッションID="demo")
        self.assertEqual(second.経路, "要約")
        self.assertIn("半導体企業が新製品を発表", second.本文)
        self.assertIn("鉄道会社が新路線計画を公表", second.本文)
        self.assertNotIn("自治体が防災訓練を実施", second.本文)
        self.assertTrue(self.chat.監査台帳.検証(second.追跡ID))

        record = self.chat.監査台帳.取得(second.追跡ID)
        self.assertIsNotNone(record)
        stages = tuple(event.段階 for event in record.イベント)
        self.assertIn("経路選択", stages)
        self.assertIn("文脈参照", stages)
        self.assertIn("能力実行", stages)
        self.assertEqual(record.イベント[0].出力["直前追跡ID"], first.追跡ID)
        self.assertEqual(record.イベント[0].出力["直前監査ハッシュ"], first.監査ハッシュ)

    def test_一般質問は基礎ミニドラへ委譲する(self) -> None:
        result = self.chat.応答("2+3は？", セッションID="general")
        self.assertEqual(result.経路, "基礎ミニドラ")
        self.assertEqual(result.本文, "基礎応答:2+3は？")
        self.assertTrue(self.chat.監査台帳.検証(result.追跡ID))
        record = self.chat.監査台帳.取得(result.追跡ID)
        core_event = next(event for event in record.イベント if event.モジュール == "MINIDORA Core")
        self.assertEqual(core_event.出力["実行記録"]["追跡範囲"], "モジュール境界")

    def test_明示文章を要約できる(self) -> None:
        result = self.chat.応答(
            "要約: 第一文です。第二文には共通する情報があります。第三文にも共通する情報があります。第四文です。",
            セッションID="summary",
        )
        self.assertEqual(result.経路, "要約")
        self.assertTrue(result.本文)
        self.assertTrue(self.chat.監査台帳.検証(result.追跡ID))

    def test_基本会話が成立する(self) -> None:
        result = self.chat.応答("こんにちは", セッションID="basic")
        self.assertEqual(result.経路, "基本会話")
        self.assertIn("ミニドラ", result.本文)

    def test_別経路へ移った後は古いニュースを要約しない(self) -> None:
        self.chat.応答("今日のニュースは？", セッションID="stale")
        hello = self.chat.応答("こんにちは", セッションID="stale")
        result = self.chat.応答("要約して", セッションID="stale")
        self.assertNotIn("半導体企業が新製品を発表", result.本文)
        self.assertIn("ミニドラ", hello.本文)

    def test_JSONL監査保存先へ追記できる(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            ledger = 監査台帳(JSONL監査保存先(path))
            chat = ハッカソンチャット(
                ニュース供給器_=固定ニュース供給器(self.items),
                基礎ミニドラ=_基礎ミニドラ(),
                監査台帳_=ledger,
            )
            result = chat.応答("こんにちは", セッションID="persist")
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            stored = json.loads(lines[0])
            self.assertEqual(stored["追跡ID"], result.追跡ID)
            self.assertEqual(stored["ルートハッシュ"], result.監査ハッシュ)
            self.assertTrue(ledger.検証(result.追跡ID))


if __name__ == "__main__":
    unittest.main()
