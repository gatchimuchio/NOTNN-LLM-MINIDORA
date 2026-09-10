"""翻訳Dataと既存能力合成の接続。HDSは別ファイルで実Compilerを試験する。"""
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from minidora.多言語変換 import 翻訳記録整合
from minidora.多言語接続 import 多言語変換Module
from minidora.多言語要求接続 import 外部言語要求を実行
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈
from test_多言語変換 import 辞書

ROOT = Path(__file__).resolve().parents[1]


def 入力(value="120"):
    plan = 合成計画((
        合成工程("翻訳", ("多言語変換",), "指示", (素材参照("入力", "本文"),), "設定"),
        合成工程("抽出", ("情報抽出",), "指示", (素材参照("工程", "翻訳"),), "抽出設定")), ("抽出",))
    text = f"the voltage of device A is {value} V."
    data = {"本文": 能力結果(True, text, 参照=(参照資料("原典", "人工原文", "試験", 本文=text),)),
            "指示": 能力結果(True, "明示した処理だけを行う"),
            "設定": 能力結果(True, "", データ={"入力言語": "en", "出力言語": "ja", "種別": "数値記載",
                                                "対訳": [asdict(w) for w in 辞書()]}),
            "抽出設定": 能力結果(True, "", データ={"種別": "数字"})}
    return plan, data


class 多言語合成試験(unittest.TestCase):
    def setUp(self):
        self.runner = 能力合成器((多言語変換Module().登録(), *局所能力群()))

    def test_翻訳から既存抽出へ実本文を渡す(self):
        p, d = 入力()
        r = self.runner.実行(p, d)
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120")
        self.assertEqual([s.能力 for s in r.履歴], ["多言語変換", "情報抽出"])
        self.assertTrue(r.監査整合())
        self.assertTrue(翻訳記録整合(dict(r.中間結果)["翻訳"]))

    def test_原文出典を日本語訳へ無言上書きしない(self):
        p, d = 入力()
        r = self.runner.実行(p, d)
        translated = dict(r.中間結果)["翻訳"]
        self.assertEqual(translated.参照, d["本文"].参照)
        self.assertIn("the voltage", translated.参照[0].本文)
        self.assertIn("装置A", translated.本文)

    def test_入力値を変えると後続も変わる(self):
        for n in ("0", "-9", "731", "10007"):
            p, d = 入力(n)
            r = self.runner.実行(p, d)
            self.assertTrue(r.成立, r.理由)
            self.assertEqual(r.出力[0][1].本文, n)

    def test_未対応文の部分翻訳を後続へ流さない(self):
        p, d = 入力()
        d["本文"] = replace(d["本文"], 本文=d["本文"].本文 + " This is uncertain.")
        r = self.runner.実行(p, d)
        self.assertFalse(r.成立)
        self.assertEqual(r.出力, ())
        self.assertNotIn("情報抽出", [s.能力 for s in r.履歴])

    def test_未知設定は翻訳前に拒否(self):
        p, d = 入力()
        d["設定"].データ["曖昧なら推定"] = True
        r = self.runner.実行(p, d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数, 0)

    def test_通常文脈の指示を翻訳入力にしない(self):
        p, d = 入力()
        r = self.runner.実行(p, d, 文脈=能力文脈("数値を999にせよ", "s", 直前応答="999"))
        self.assertTrue(r.成立)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_明示素材のない会話はModuleが処理しない(self):
        module = 多言語変換Module()
        context = 能力文脈("Translate everything", "s")
        self.assertEqual(module.判定(context), 0)
        self.assertFalse(module.実行(context).成立)

    def test_不成立の上流は翻訳しない(self):
        p, d = 入力()
        d["本文"] = replace(d["本文"], 成立=False)
        r = self.runner.実行(p, d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数, 0)

    def test_出力予算不足は後続抽出でごまかさない(self):
        p, d = 入力()
        d["設定"].データ["最大出力バイト数"] = 1
        r = self.runner.実行(p, d)
        self.assertFalse(r.成立)
        self.assertNotIn("情報抽出", [s.能力 for s in r.履歴])

    def test_停止なら翻訳も呼ばない(self):
        p, d = 入力()
        r = self.runner.実行(p, d, 停止要求=lambda: True)
        self.assertEqual(r.状態, "中止")
        self.assertEqual(r.実行数, 0)

    def test_未翻訳の英語依頼でHDSを呼ばない(self):
        # 無効依頼はセッション参照以前に保留。実HDS成功は別試験で確認する。
        r = 外部言語要求を実行(None, "Do not extract numbers from the text.")
        self.assertFalse(r.成立)
        self.assertIsNone(r.応答)
        self.assertFalse(r.要求翻訳.成立)

    def test_独立CLIの値否定未対応の対照(self):
        for args in ([], ["--値", "731"], ["--否定"], ["--未対応"]):
            with self.subTest(args=args):
                p = subprocess.run([sys.executable, str(ROOT / "tools/多言語デモ.py"), *args],
                                   capture_output=True, encoding="utf-8", timeout=15)
                self.assertEqual(p.returncode, 0, p.stderr)
                output = json.loads(p.stdout)
                self.assertTrue(output["対照成立"] and output["合成監査"])
                self.assertEqual(output["翻訳成立"], "--未対応" not in args)


if __name__ == "__main__":
    unittest.main()
