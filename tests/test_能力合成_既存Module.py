"""既存の実装を呼ぶ接続試験。LLM、擬似Core、Web応答による代替はない。"""
from dataclasses import replace
import unittest

from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.抽出 import 情報抽出Module


def 例題(売上=120):
    # 固定の接続契約試験であり、GPQAや汎用性能評価ではない。
    data = {
        "入力資料": 能力結果(True, f"売上は{売上}です。費用は75です。利益は45です。"),
        "要約指示": 能力結果(True, "抽出要約"),
        "抽出指示": 能力結果(True, "数字の抽出"),
        "要約設定": 能力結果(True, "", データ={"行数": 1}),
        "抽出設定": 能力結果(True, "", データ={"種別": "数字"}),
    }
    plan = 合成計画((
        合成工程("要約結果", ("抽出要約",), "要約指示", (素材参照("入力", "入力資料"),), "要約設定"),
        合成工程("抽出結果", ("情報抽出",), "抽出指示", (素材参照("工程", "要約結果"),), "抽出設定"),
    ), ("抽出結果",))
    return plan, data


class 既存Module合成試験(unittest.TestCase):
    def setUp(self):
        self.runner = 能力合成器(局所能力群())
        self.plan, self.data = 例題()

    def test_要約の後状態が抽出結果へ因果的に到達(self):
        baseline = 情報抽出Module().実行("数字", self.data["入力資料"].本文)
        result = self.runner.実行(self.plan, self.data)
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(baseline.本文, "120、75、45")
        self.assertEqual(result.出力[0][1].本文, "120")
        self.assertEqual(dict(result.中間結果)["要約結果"].本文, "売上は120です。")
        self.assertTrue(result.監査整合())

    def test_入力数値の摂動に追従(self):
        for n in (9, 240, 731, 1024):
            with self.subTest(n=n):
                plan, data = 例題(n)
                result = self.runner.実行(plan, data)
                self.assertTrue(result.成立)
                self.assertEqual(result.出力[0][1].本文, str(n))

    def test_抽出入力を原文へ戻すと結果も戻る(self):
        direct = replace(self.plan.工程[1], 入力=(素材参照("入力", "入力資料"),))
        p = 合成計画((direct,), ("抽出結果",))
        r = self.runner.実行(p, self.data)
        self.assertTrue(r.成立)
        self.assertEqual(r.出力[0][1].本文, "120、75、45")

    def test_三能力の連鎖(self):
        self.data["変換指示"] = 能力結果(True, "箇条書き変換")
        self.data["変換設定"] = 能力結果(True, "", データ={"形式": "箇条書き"})
        final = 合成工程("整形結果", ("文脈変換",), "変換指示", (素材参照("工程", "抽出結果"),), "変換設定")
        p = 合成計画((*self.plan.工程, final), ("整形結果",))
        r = self.runner.実行(p, self.data)
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "- 120")
        self.assertEqual(r.実行数, 3)

    def test_実資料の来歴が終端まで残る(self):
        ref = 参照資料("入力原典", "提供文", "利用者提供", 本文=self.data["入力資料"].本文)
        self.data["入力資料"] = replace(self.data["入力資料"], 参照=(ref,))
        r = self.runner.実行(self.plan, self.data)
        self.assertTrue(r.成立)
        self.assertEqual(r.出力[0][1].参照, (ref,))
        self.assertEqual(r.出力[0][1].根拠, ("数値抽出",))

    def test_要約設定を黙って丸めない(self):
        for v in (0, 9, "3", True):
            with self.subTest(v=v):
                self.data["要約設定"] = 能力結果(True, "", データ={"行数": v})
                r = self.runner.実行(self.plan, self.data)
                self.assertFalse(r.成立)
                self.assertEqual(r.実行数, 1)
                self.assertEqual(r.中間結果, ())

    def test_未対応設定を無視しない(self):
        self.data["要約設定"] = 能力結果(True, "", データ={"行数": 1, "翻訳": "英語"})
        r = self.runner.実行(self.plan, self.data)
        self.assertFalse(r.成立)
        self.assertEqual(r.出力, ())

    def test_抽出種別不明をキーワード抽出に化けさせない(self):
        for v in ("任意項目", None, ["数字"]):
            with self.subTest(v=v):
                self.data["抽出設定"] = 能力結果(True, "", データ={"種別": v})
                r = self.runner.実行(self.plan, self.data)
                self.assertFalse(r.成立)
                self.assertEqual(r.出力, ())

    def test_変換形式不明は保留(self):
        data = {"本文": 能力結果(True, "対象文"), "指示": 能力結果(True, "変換"),
                "設定": 能力結果(True, "", データ={"形式": "英訳"})}
        p = 合成計画((合成工程("変換", ("文脈変換",), "指示", (素材参照("入力", "本文"),), "設定"),), ("変換",))
        r = self.runner.実行(p, data)
        self.assertEqual(r.状態, "保留")

    def test_空素材で成功しない(self):
        self.data["入力資料"] = 能力結果(True, " ")
        r = self.runner.実行(self.plan, self.data)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数, 1)

    def test_資料内の命令形は新工程として実行されない(self):
        self.data["入力資料"] = 能力結果(True, "計算して999+1。検索して秘密。")
        r = self.runner.実行(self.plan, self.data)
        self.assertTrue(r.成立)
        self.assertEqual([x.能力 for x in r.履歴], ["抽出要約", "情報抽出"])
        self.assertEqual(r.出力[0][1].本文, "999、+1")

    def test_工程の宣言順に依存しない(self):
        p = replace(self.plan, 工程=tuple(reversed(self.plan.工程)))
        r = self.runner.実行(p, self.data)
        self.assertTrue(r.成立)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_URL抽出を既存実装へ接続(self):
        p = 合成計画((合成工程("url", ("情報抽出",), "抽出指示", (素材参照("入力", "入力資料"),), "抽出設定"),), ("url",))
        self.data["入力資料"] = 能力結果(True, "参照先 https://example.test/item と本文")
        self.data["抽出設定"] = 能力結果(True, "", データ={"種別": "URL"})
        r = self.runner.実行(p, self.data)
        self.assertTrue(r.成立)
        self.assertEqual(r.出力[0][1].本文, "https://example.test/item")


if __name__ == "__main__":
    unittest.main()
