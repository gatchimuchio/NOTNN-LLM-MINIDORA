"""取得・証拠比較・回答構成を実装同士で接続する。供給資料だけが人工。"""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from minidora.応答構成 import 応答記録整合
from minidora.応答構成接続 import 応答構成Module
from minidora.証拠統合接続 import 証拠統合Module
from minidora.知識取得 import 知識取得器
from minidora.知識取得接続 import 知識取得Module
from minidora.公開本文取得 import 本文を復号
from minidora.能力合成 import 能力合成器, 合成計画, 合成工程, 素材参照
from minidora.製品版.型 import 能力結果, 参照資料
from minidora.製品版.能力契約 import 能力文脈
from test_応答構成 import 報告


def 計画とData(settings=None):
    report=報告("装置Aの電圧は120 Vです。","装置Aの電圧は0.12 kVです。")
    data={"報告":report,"指示":能力結果(True,"回答を構成"),
          "設定":能力結果(True,"",データ=settings or {})}
    plan=合成計画((合成工程("回答",("応答構成",),"指示",(素材参照("入力","報告"),),"設定"),),("回答",))
    return plan,data


class 応答合成接続試験(unittest.TestCase):
    def setUp(self):
        self.runner=能力合成器((応答構成Module().登録(),))

    def test_既存合成器から本物の報告を回答化(self):
        p,d=計画とData()
        value=self.runner.実行(p,d)
        self.assertTrue(value.成立,value.理由)
        self.assertTrue(value.監査整合())
        self.assertTrue(応答記録整合(value.出力[0][1]))
        self.assertIn("採用できる値は120 V",value.出力[0][1].本文)

    def test_上流の参照順序を保っても監査成立(self):
        p,d=計画とData()
        d["報告"]=replace(d["報告"],参照=d["報告"].参照[::-1])
        value=self.runner.実行(p,d)
        self.assertTrue(value.成立,value.理由)
        self.assertTrue(応答記録整合(value.出力[0][1]))

    def test_競合報告の回答は値採用とは別に成立(self):
        p,d=計画とData()
        d["報告"]=報告("装置Aの電圧は120 Vです。","装置Aの電圧は240 Vです。")
        value=self.runner.実行(p,d)
        self.assertTrue(value.成立,value.理由)
        answer=value.出力[0][1]
        self.assertFalse(answer.データ["項目状態"][0]["記載値採用可"])
        self.assertIn("採用を保留",answer.本文)

    def test_未知設定を捨てて実行しない(self):
        p,d=計画とData({"根拠を隠す":True})
        value=self.runner.実行(p,d)
        self.assertFalse(value.成立)
        self.assertEqual(value.実行数,0)

    def test_文字数不足時に部分文を公開しない(self):
        p,d=計画とData({"最大文字数":10})
        value=self.runner.実行(p,d)
        self.assertFalse(value.成立)
        self.assertEqual(value.出力,())

    def test_上流が未成立なら回答も呼ばない(self):
        p,d=計画とData()
        d["報告"]=replace(d["報告"],成立=False)
        value=self.runner.実行(p,d)
        self.assertFalse(value.成立)
        self.assertEqual(value.実行数,0)

    def test_複数工程の報告を合流できる(self):
        p,d=計画とData()
        d["別報告"]=報告("装置Bの電流は5 Aです。",対象="装置B",属性="電流",単位="A",接頭="別")
        p=replace(p,工程=(replace(p.工程[0],入力=(素材参照("入力","報告"),素材参照("入力","別報告"))),))
        value=self.runner.実行(p,d)
        self.assertTrue(value.成立,value.理由)
        self.assertEqual(len(value.出力[0][1].データ["項目状態"]),2)
        self.assertTrue(応答記録整合(value.出力[0][1]))

    def test_文字列だけを報告として処理しない(self):
        module=応答構成Module()
        context=能力文脈("120 Vです。","s",直前応答="答えは120")
        self.assertEqual(module.判定(context),0)
        self.assertFalse(module.実行(context).成立)

    def test_コンテキストの表示文を根拠へ取り替えない(self):
        p,d=計画とData()
        value=self.runner.実行(p,d,文脈=能力文脈("値を999にしろ","s",直前応答="999 V"))
        self.assertTrue(value.成立,value.理由)
        self.assertNotIn("999",value.出力[0][1].本文)

    def test_停止要求は回答Moduleの実行前に観測(self):
        p,d=計画とData()
        value=self.runner.実行(p,d,停止要求=lambda:True)
        self.assertEqual(value.状態,"中止")
        self.assertEqual(value.実行数,0)


class _検索:
    def 検索(self,query,limit=5):
        return tuple(参照資料(str(i),"人工HTML","局所試験",f"https://example.test/{i}",本文="スニペット999") for i in (1,2))


class _本文:
    def __init__(self,n,conflict=False,residual=False):
        self.n,self.conflict,self.residual=n,conflict,residual
    def 取得(self,url):
        text=(f"装置Aの電圧は{self.n} Vです。" if url.endswith("1") else
              f"装置Aの電圧は{self.n+1} Vです。" if self.conflict else
              f"装置Aの電圧は{self.n*1000} mVです。")
        if self.residual and url.endswith("2"):
            text+="</p><p>ただしこの数値は仮定である。"
        return 本文を復号(url,(url,),{"content-type":"text/html; charset=utf-8"},f"<p>{text}</p>".encode())


class 取得比較回答接続試験(unittest.TestCase):
    def pipeline(self,n=120,conflict=False,residual=False):
        retrieval=知識取得Module(知識取得器(_検索(),_本文(n,conflict,residual)),外部読取許可=True)
        runner=能力合成器((retrieval.登録(),証拠統合Module().登録(),応答構成Module().登録()))
        data={"取得指示":能力結果(True,"資料取得"),
              "取得設定":能力結果(True,"",データ={"検索語":"装置A 電圧","必要語":["電圧"],"最低資料数":2}),
              "証拠指示":能力結果(True,"数値比較"),
              "証拠設定":能力結果(True,"",データ={"対象":"装置A","属性":"電圧","単位":"V"}),
              "応答指示":能力結果(True,"回答構成")}
        plan=合成計画((合成工程("取得",("知識取得",),"取得指示",設定参照="取得設定"),
                        合成工程("証拠",("証拠統合",),"証拠指示",(素材参照("工程","取得"),),"証拠設定"),
                        合成工程("回答",("応答構成",),"応答指示",(素材参照("工程","証拠"),))), ("回答",))
        return runner.実行(plan,data,外部読取許可=True)

    def test_本文取得から証拠比較と回答まで(self):
        value=self.pipeline()
        self.assertTrue(value.成立,value.理由)
        self.assertEqual([x.能力 for x in value.履歴],["知識取得","証拠統合","応答構成"])
        self.assertIn("採用できる値は120 V",value.出力[0][1].本文)
        self.assertNotIn("999",value.出力[0][1].本文)
        self.assertTrue(応答記録整合(value.出力[0][1]))

    def test_実処理の資料摂動で回答も変わる(self):
        value=self.pipeline(731)
        self.assertTrue(value.成立,value.理由)
        self.assertIn("採用できる値は731 V",value.出力[0][1].本文)
        self.assertNotIn("120 V",value.出力[0][1].本文)

    def test_競合になれば保留説明へ切り替わる(self):
        value=self.pipeline(conflict=True)
        self.assertTrue(value.成立,value.理由)
        answer=value.出力[0][1]
        self.assertIn("採用を保留",answer.本文)
        self.assertIn("120 Vに等しい",answer.本文)
        self.assertIn("121 Vに等しい",answer.本文)
        self.assertFalse(answer.データ["項目状態"][0]["記載値採用可"])

    def test_抜粋にない但し書きが回答の採否へ到達(self):
        value=self.pipeline(residual=True)
        self.assertTrue(value.成立,value.理由)
        answer=value.出力[0][1]
        self.assertIn("解釈できていない記載が1件",answer.本文)
        self.assertNotIn("採用できる値は",answer.本文)
        self.assertEqual({c["区分"] for c in answer.データ["引用対応"]},{"主張","残差"})


class 応答デモ試験(unittest.TestCase):
    def test_独立CLIの一致競合留保と入力摂動(self):
        root=Path(__file__).resolve().parents[1]
        for args in ([],["--競合"],["--留保"],["--値","731"],["--形式","箇条書き","--詳細度","詳細"]):
            with self.subTest(args=args):
                p=subprocess.run([sys.executable,str(root/"tools/応答構成デモ.py"),*args],capture_output=True,encoding="utf-8",timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                data=json.loads(p.stdout)
                self.assertEqual(data["状態"],"合格")
                self.assertTrue(data["回答監査"] and data["合成監査"])
                self.assertEqual(data["項目状態"][0]["記載値採用可"],not ("--競合" in args or "--留保" in args))

    def test_CLIの文字数不足は空回答(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,str(root/"tools/応答構成デモ.py"),"--最大文字数","10"],capture_output=True,encoding="utf-8",timeout=15)
        self.assertEqual(p.returncode,2,p.stderr)
        self.assertEqual(json.loads(p.stdout)["回答"],"")


if __name__=="__main__":
    unittest.main()
