from __future__ import annotations

import json
import subprocess
import sys
import unittest
from copy import deepcopy

from minidora import ミニドラ
from minidora.hds_adapter import HDS文脈
from minidora.言語構造 import 言語関係抽出
from minidora.言語確率法則 import MINIDORA厳密言語模型
from minidora.計算中間表現 import 計算中間表現, 計算値, 計算作用, 計算命令
from minidora.計算実行境界 import 計算実行境界


class 最小汎用Core改善Round2試験(unittest.TestCase):
    def test_厳密LMはgenerator形成と増分形成で全量形成に一致(self) -> None:
        first = ("猫は本を見る。", "犬は水を飲む。")
        second = ("鳥は空を飛ぶ。", "猫は水を飲む。")
        streamed = MINIDORA厳密言語模型.形成((x for x in first), 次数=3)
        incremental = streamed.追加形成((x for x in second))
        rebuilt = MINIDORA厳密言語模型.形成((*first, *second), 次数=3)
        self.assertEqual(incremental.辞書化(), rebuilt.辞書化())
        self.assertEqual(incremental.系列確率("猫は空を飛ぶ。"), rebuilt.系列確率("猫は空を飛ぶ。"))

    def test_壊れた厳密LM状態は復元入口で拒否(self) -> None:
        payload = MINIDORA厳密言語模型.形成(("abc",), 次数=3).辞書化()
        broken = deepcopy(payload)
        broken["遷移計数"][""]["a"] = 0
        with self.assertRaises(ValueError):
            MINIDORA厳密言語模型.復元(broken)

        broken = deepcopy(payload)
        broken["遷移計数"][""]["OUTSIDE"] = 1
        with self.assertRaises(ValueError):
            MINIDORA厳密言語模型.復元(broken)

    def test_比較は要求演算子以外を先行評価しない(self) -> None:
        command = 計算命令(
            "cmp", "辞書同値", 計算作用.比較,
            (計算値.即値({"a": 1}), 計算値.即値("同値"), 計算値.即値({"a": 1})),
            出力住所="結果",
        )
        result = 計算実行境界().実行(計算中間表現("比較", (command,), "結果"))
        self.assertIs(result.出力, True)

    def test_算術作用は入力可変値を破壊しない(self) -> None:
        left = [1]
        right = [2]
        initial = {"left": left, "right": right}
        command = 計算命令(
            "add", "list加算", 計算作用.加算,
            (計算値.状態値("left"), 計算値.状態値("right")),
            出力住所="結果",
        )
        result = 計算実行境界().実行(計算中間表現("加算", (command,), "結果"), initial)
        self.assertEqual(result.出力, [1, 2])
        self.assertEqual(left, [1])
        self.assertEqual(right, [2])
        self.assertEqual(initial, {"left": [1], "right": [2]})

    def test_日本語否定活用と文境界scopeを保持(self) -> None:
        relations = 言語関係抽出("AはBを阻害しない。CはDを活性化する。", "自然言語:ja")
        self.assertTrue(any(x.種別 == "阻害" and not x.肯定 for x in relations))
        self.assertTrue(any(x.種別 == "活性化" and x.肯定 for x in relations))

        for text in ("AはBを阻害しません", "AはBを阻害せず", "AはBを阻害せぬ"):
            rows = 言語関係抽出(text, "自然言語:ja")
            self.assertTrue(any(x.種別 == "阻害" and not x.肯定 for x in rows), text)

    def test_英語明示対比で否定scopeを局所化(self) -> None:
        relations = 言語関係抽出("A does not inhibit B, but C activates D", "自然言語:en")
        self.assertTrue(any(x.種別 == "阻害" and not x.肯定 for x in relations))
        self.assertTrue(any(x.種別 == "活性化" and x.肯定 for x in relations))

    def test_default_runtimeは主体Trinityを起動しない(self) -> None:
        body = ミニドラ()
        self.assertIsNone(body.主体主幹)
        self.assertIsNone(body.Trinity文脈)
        self.assertEqual(body.HDS履歴, ())
        self.assertEqual(body.主体状態.主体ID, "MINIDORA")

    def test_default_HDSコンパイルは無状態(self) -> None:
        class Compiler:
            def __init__(self) -> None:
                self.kwargs = None
            def コンパイル(self, 入力, *, 前回結果=None, HDS履歴=(), 文脈=None):
                self.kwargs = {"前回結果": 前回結果, "HDS履歴": HDS履歴, "文脈": 文脈}
                return "fixture-ir"

        compiler = Compiler()
        body = ミニドラ(HDSコンパイラ_=compiler)
        self.assertEqual(body.コンパイル("入力"), "fixture-ir")
        self.assertIsNone(compiler.kwargs["前回結果"])
        self.assertEqual(compiler.kwargs["HDS履歴"], ())
        self.assertIsInstance(compiler.kwargs["文脈"], HDS文脈)

    def test_plain_importではlegacy_submoduleを起動しない(self) -> None:
        script = r'''
import json, sys
import minidora
blocked = [
    "minidora.runtime_v03",
    "minidora.trinity_context",
    "minidora.k3_functional",
    "minidora.http_reference",
    "minidora.europe_pmc_reference",
    "minidora.crossref_reference",
]
print(json.dumps([name for name in blocked if name in sys.modules]))
'''
        proc = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(proc.stdout), [])


if __name__ == "__main__":
    unittest.main()
