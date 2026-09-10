"""取得本文→証拠報告→記載値採用→既存抽出の接続試験。素材だけが人工。"""
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest

from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.能力合成_局所接続 import 局所能力群
from minidora.公開本文取得 import 本文を復号
from minidora.知識取得 import 知識取得器
from minidora.知識取得接続 import 知識取得Module
from minidora.証拠統合接続 import 証拠統合Module, 記載値採用Module
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈


def plan_and_data(texts, *, settings=None):
    refs = tuple(参照資料(chr(97+i), "人工資料", "契約入力", 本文=t) for i,t in enumerate(texts))
    data = {"素材": 能力結果(True, "無関係な抜粋999", 参照=refs),
            "比較指示": 能力結果(True, "数値記載を比較"),
            "設定": 能力結果(True, "", データ=settings or {"対象":"装置A", "属性":"電圧", "単位":"V"}),
            "採用指示": 能力結果(True, "記載値採用"),
            "抽出指示": 能力結果(True, "数字抽出"),
            "抽出設定": 能力結果(True, "", データ={"種別":"数字"})}
    stages = (
        合成工程("証拠", ("証拠統合",), "比較指示", (素材参照("入力","素材"),), "設定"),
        合成工程("採用", ("記載値採用",), "採用指示", (素材参照("工程","証拠"),)),
        合成工程("抽出", ("情報抽出",), "抽出指示", (素材参照("工程","採用"),), "抽出設定"),
    )
    return 合成計画(stages, ("抽出",)), data


class 証拠合成接続試験(unittest.TestCase):
    def setUp(self):
        self.runner = 能力合成器((証拠統合Module().登録(), 記載値採用Module().登録(), *局所能力群()))

    def run_texts(self, *texts, settings=None):
        p,d = plan_and_data(texts, settings=settings)
        r = self.runner.実行(p,d)
        self.assertTrue(r.監査整合())
        return r

    def test_換算同値は後段へ渡る(self):
        r = self.run_texts("装置Aの電圧は120 Vです。", "装置Aの電圧は0.12 kVです。")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文,"120")
        self.assertEqual([t.能力 for t in r.履歴], ["証拠統合","記載値採用","情報抽出"])

    def test_矛盾資料に置換すると後段を呼ばない(self):
        r = self.run_texts("装置Aの電圧は120 Vです。", "装置Aの電圧は240 Vです。")
        self.assertFalse(r.成立)
        self.assertEqual(r.出力,())
        self.assertEqual([t.能力 for t in r.履歴], ["証拠統合","記載値採用"])
        self.assertIn("記載競合", dict(r.中間結果)["証拠"].データ["理由"])

    def test_未解釈の条件は後段で数字だけ取り出さない(self):
        r = self.run_texts("装置Aの電圧は120 Vです。ただしこれは推定です。")
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数, 2)
        self.assertTrue(dict(r.中間結果)["証拠"].データ["残差"])

    def test_参照ではなく前段の生成文を根拠にしない(self):
        p,d = plan_and_data(["装置Aの電圧は120 Vです。"])
        d["素材"] = replace(d["素材"], 本文="装置Aの電圧は999 Vです。")
        r = self.runner.実行(p,d)
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_資料の順序が変わっても採用できる(self):
        p,d = plan_and_data(["装置Aの電圧は120 Vです。", "装置Aの電圧は0.12 kVです。"])
        d["素材"] = replace(d["素材"], 参照=tuple(reversed(d["素材"].参照)))
        r = self.runner.実行(p,d)
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_採用関門を省略しても報告は診断として読める(self):
        p,d = plan_and_data(["装置Aの電圧は120 Vです。", "装置Aの電圧は240 Vです。"])
        r = self.runner.実行(合成計画((p.工程[0],),("証拠",)),d)
        self.assertTrue(r.成立)
        self.assertIn("採用保留", r.出力[0][1].本文)
        self.assertFalse(r.出力[0][1].データ["採用可"])

    def test_設定の未知フィールドを無視しない(self):
        for extra in ({"最新":True}, {"自動多数決":True}):
            p,d = plan_and_data(["装置Aの電圧は120 Vです。"])
            d["設定"].データ.update(extra)
            r = self.runner.実行(p,d)
            self.assertFalse(r.成立)
            self.assertEqual(r.実行数,0)

    def test_参照資料なしの回答を証拠にしない(self):
        p,d = plan_and_data([])
        r = self.runner.実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数,1)

    def test_採用Moduleに通常の文章を渡しても不成立(self):
        m = 記載値採用Module()
        self.assertFalse(m.実行(能力文脈("採用", "s", "120 V")).成立)
        self.assertFalse(m.実行(None).成立)

    def test_明示した時点で選択し古い時点も記録に残す(self):
        a="2025-01-01時点、装置Aの電圧は120 Vです。"
        b="2026-01-01時点、装置Aの電圧は240 Vです。"
        r=self.run_texts(a,b, settings={"対象":"装置A","属性":"電圧","単位":"V","時点":"2025-01-01"})
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,"120")
        self.assertEqual(len(dict(r.中間結果)["証拠"].データ["群"]),2)

    def test_不成立の上流資料を先に拒否(self):
        p,d=plan_and_data(["装置Aの電圧は120 Vです。"])
        d["素材"]=replace(d["素材"],成立=False)
        r=self.runner.実行(p,d)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数,0)

    def test_停止要求時は証拠処理を呼ばない(self):
        p,d=plan_and_data(["装置Aの電圧は120 Vです。"])
        r=self.runner.実行(p,d,停止要求=lambda:True)
        self.assertEqual(r.状態,"中止")
        self.assertEqual(r.実行数,0)


class _検索:
    def 検索(self, query, limit=5):
        return tuple(参照資料(str(i),"人工HTML","試験検索",f"https://example.test/{i}",
                             本文="誤ったスニペット999") for i in (1,2))


class _HTML供給:
    def __init__(self, second):
        self.second=second
    def 取得(self, url):
        text="装置Aの電圧は120 Vです。" if url.endswith("1") else self.second
        return 本文を復号(url,(url,),{"content-type":"text/html; charset=utf-8"},f"<p>{text}</p>".encode())


class 取得証拠接続試験(unittest.TestCase):
    def pipeline(self, second):
        retrieval=知識取得Module(知識取得器(_検索(),_HTML供給(second)),外部読取許可=True)
        runner=能力合成器((retrieval.登録(),証拠統合Module().登録(),記載値採用Module().登録(),*局所能力群()))
        p,d=plan_and_data([])
        d["取得指示"]=能力結果(True,"資料を取得")
        d["取得設定"]=能力結果(True,"",データ={"検索語":"装置A 電圧","必要語":["電圧"],"最低資料数":2})
        first=合成工程("取得",("知識取得",),"取得指示",設定参照="取得設定")
        proof=replace(p.工程[0],入力=(素材参照("工程","取得"),))
        return runner.実行(合成計画((first,proof,*p.工程[1:]),p.出力工程),d,外部読取許可=True)

    def test_実取得機構から単位統合と既存数値抽出(self):
        r=self.pipeline("装置Aの電圧は0.12 kVです。")
        self.assertTrue(r.成立,r.理由)
        self.assertEqual(r.出力[0][1].本文,"120")
        self.assertEqual(r.実行数,4)
        self.assertNotIn("999",r.出力[0][1].本文)
        self.assertEqual(len(r.出力[0][1].参照),2)

    def test_取得成功でも証拠競合なら最後の抽出を停止(self):
        r=self.pipeline("装置Aの電圧は240 Vです。")
        self.assertTrue(dict(r.中間結果)["取得"].成立)
        self.assertTrue(dict(r.中間結果)["証拠"].成立)
        self.assertFalse(r.成立)
        self.assertEqual(r.実行数,3)
        self.assertNotIn("情報抽出",[t.能力 for t in r.履歴])

    def test_抜粋だけ見て後半の留保を落とさない(self):
        r=self.pipeline("装置Aの電圧は0.12 kVです。</p><p>ただし上記は仮定である。")
        self.assertFalse(r.成立)
        self.assertTrue(dict(r.中間結果)["証拠"].データ["残差"])


class 証拠デモ試験(unittest.TestCase):
    def test_独立CLIの一致競合と入力摂動(self):
        import json
        root=Path(__file__).resolve().parents[1]
        for args in ([],["--競合"],["--値","731"]):
            with self.subTest(args=args):
                result=subprocess.run([sys.executable,str(root/"tools/証拠統合デモ.py"),*args],
                    capture_output=True,encoding="utf-8",timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                output=json.loads(result.stdout)
                self.assertTrue(output["監査整合"])
                self.assertEqual(output["状態"],"保留" if "--競合" in args else "合格")


if __name__ == "__main__":
    unittest.main()
