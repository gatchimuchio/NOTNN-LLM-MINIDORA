"""既存の要約・抽出・証拠・関係判定を使った目的分解と実行の接続試験。"""
from dataclasses import asdict, replace
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

from minidora.多段解決 import 多段問題, 解決目的, 解法, 問題素材, 多段解決器
from minidora.多段解決接続 import 多段解決Module, 解決補助能力群
from minidora.能力合成 import 能力合成器, 合成工程, 合成計画, 素材参照, _結果辞書
from minidora.能力合成_局所接続 import 局所能力群
from minidora.証拠統合接続 import 証拠統合Module
from minidora.関係制約 import 関係式, 関係記録整合
from minidora.関係制約接続 import 数値関係化Module, 関係制約Module, 関係判定採用Module
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈

ROOT = Path(__file__).resolve().parents[1]
例題 = runpy.run_path(str(ROOT / "tools/多段解決デモ.py"))["問題を用意"]


def 文書実行器():
    return 多段解決器((*局所能力群(), *解決補助能力群()), 純粋作用確認=True)


def 関係問題を用意(上限="100", 条件=None):
    def source(name, text):
        return 能力結果(True, "", 参照=(参照資料(name, "人工資料" + name, "局所試験", 本文=text),))
    data = {"A": source("a", "装置Aの電圧は120 V以上です。"),
            "B": source("b", (f'条件「{条件}」では、' if 条件 else "") + f"装置Bの電圧は{上限} V以下です。"),
            "指示": 能力結果(True, "指定した処理"),
            "非空": 能力結果(True, "", データ={"種別": "非空"}),
            "A設定": 能力結果(True, "", データ={"対象": "装置A", "属性": "電圧", "単位": "V"}),
            "B設定": 能力結果(True, "", データ={"対象": "装置B", "属性": "電圧", "単位": "V"}),
            "関係設定": 能力結果(True, "", データ={"問い": [asdict(関係式("比較", "装置A", "超", "装置B"))]}),
            "採用設定": 能力結果(True, "", データ={"問いID": "比較", "期待": "導出"})}
    goals = tuple(解決目的(name, "成果検査", "指示", "非空") for name in ("Aの証拠", "Bの証拠", "関係化"))
    goals += (解決目的("比較確定", "関係判定採用", "指示", "採用設定"),)
    methods = (
        解法("A読解", "Aの証拠", (), "証拠統合", "指示", (問題素材("入力", "A"),), "A設定"),
        解法("B読解", "Bの証拠", (), "証拠統合", "指示", (問題素材("入力", "B"),), "B設定"),
        解法("同一尺度へ", "関係化", ("Aの証拠", "Bの証拠"), "数値関係化", "指示",
             (問題素材("目的", "Aの証拠"), 問題素材("目的", "Bの証拠")), "関係設定"),
        解法("比較を解く", "比較確定", ("関係化",), "関係制約", "指示", (問題素材("目的", "関係化"),)),
    )
    engine = 多段解決器((*解決補助能力群(), 証拠統合Module().登録(), 数値関係化Module().登録(),
                        関係制約Module().登録(), 関係判定採用Module().登録()), 純粋作用確認=True)
    return engine, 多段問題(("比較確定",), goals, methods), data


class 既存能力多段接続試験(unittest.TestCase):
    def test_要約成功でも親の検査で後戻りする(self):
        p, data = 例題()
        r = 文書実行器().実行(p, data)
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120、75、45")
        self.assertEqual([x["解法"] for x in r.採用経路], ["原文を保持", "素材から抽出"])
        self.assertTrue(any(x["作用"] == "局所成立" and x["解法"] == "要約を使う" for x in r.履歴))
        self.assertIn("元資料の数値列が保持されていない", str(r.履歴))

    def test_代替を外すと目的を緩めず保留(self):
        p, data = 例題(代替あり=False)
        r = 文書実行器().実行(p, data)
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())

    def test_資料摂動に同じ解法群が追従(self):
        for n in (0, 731, 10007):
            with self.subTest(n=n):
                p, data = 例題(n)
                r = 文書実行器().実行(p, data)
                self.assertTrue(r.成立, r.理由)
                self.assertEqual(r.出力[0][1].本文, f"{n}、75、45")

    def test_原文優先なら不要な要約を呼ばない(self):
        p, data = 例題()
        p = replace(p, 解法群=tuple(replace(m, 優先度=-1) if m.識別子 == "原文を保持" else m for m in p.解法群))
        r = 文書実行器().実行(p, data)
        self.assertTrue(r.成立)
        self.assertEqual(r.呼出数, 4)
        self.assertNotIn("抽出要約", [x.get("能力") for x in r.履歴])

    def test_要約に情報落ちがない時は第一経路を採用(self):
        p, data = 例題()
        data["原資料"] = 能力結果(True, "売上は120です。")
        r = 文書実行器().実行(p, data)
        self.assertTrue(r.成立)
        self.assertEqual(r.採用経路[0]["解法"], "要約を使う")
        self.assertNotIn("素材引継ぎ", [x.get("能力") for x in r.履歴])

    def test_予算不足時に最初の不完全な成果を返さない(self):
        p, data = 例題()
        r = 文書実行器().実行(p, data, 最大呼出数=4)
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())
        self.assertIn("上限", r.理由)

    def test_参照来歴を後戻りで失わない(self):
        p, data = 例題()
        r = 文書実行器().実行(p, data)
        self.assertEqual(r.出力[0][1].参照, data["原資料"].参照)
        self.assertTrue(r.整合確認())

    def test_関係判定を下位処理と目的検証に使う(self):
        engine, p, data = 関係問題を用意()
        r = engine.実行(p, data)
        self.assertTrue(r.成立, r.理由)
        answer = r.出力[0][1]
        self.assertTrue(関係記録整合(answer))
        self.assertEqual(answer.データ["回答"][0]["判定"], "導出")
        self.assertEqual([x["目的"] for x in r.採用経路], ["Aの証拠", "Bの証拠", "関係化", "比較確定"])

    def test_関係が不足しても勝手に前提を追加しない(self):
        engine, p, data = 関係問題を用意("200")
        r = engine.実行(p, data)
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())
        self.assertIn("問いの確定判定が採用条件を満たさない", str(r.履歴))

    def test_異なる条件の証拠を混ぜて達成しない(self):
        engine, p, data = 関係問題を用意(条件="試験")
        r = engine.実行(p, data)
        self.assertEqual(r.状態, "保留")
        self.assertNotIn("関係制約", [x.get("能力") for x in r.履歴])

    def test_未解釈の留保を経路探索で消さない(self):
        engine, p, data = 関係問題を用意()
        ref = data["A"].参照[0]
        data["A"] = replace(data["A"], 参照=(replace(ref, 本文=ref.本文 + "ただし仮定である。"),))
        r = engine.実行(p, data)
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())

    def test_既存合成器から多段解決Moduleを呼べる(self):
        p, data = 例題()
        module = 多段解決Module((*局所能力群(), *解決補助能力群()), 純粋作用確認=True)
        payload = 能力結果(True, "", データ={"問題": asdict(p), "初期Data": {k: _結果辞書(v) for k, v in data.items()}})
        outer = 合成計画((合成工程("実行", ("多段解決",), "指示", (素材参照("入力", "問題"),)),), ("実行",))
        result = 能力合成器((module.登録(),)).実行(outer, {"問題": payload, "指示": 能力結果(True, "目的解決")})
        self.assertTrue(result.成立, result.理由)
        self.assertEqual(result.出力[0][1].本文, "120、75、45")
        self.assertTrue(result.監査整合())

    def test_普通の会話文を実行可能問題に見せない(self):
        module = 多段解決Module(解決補助能力群(), 純粋作用確認=True)
        c = 能力文脈("全部完成させて", "s")
        self.assertEqual(module.判定(c), 0)
        self.assertFalse(module.実行(c).成立)

    def test_独立CLIの後戻り代替除去と数値摂動(self):
        for args in ([], ["--代替なし"], ["--値", "731"]):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(ROOT / "tools/多段解決デモ.py"), *args],
                                        capture_output=True, encoding="utf-8", timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data["状態"], "保留" if "--代替なし" in args else "合格")
                self.assertTrue(data["監査整合"])


if __name__ == "__main__":
    unittest.main()
