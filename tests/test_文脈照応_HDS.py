"""本物の公開HDS Compiler・局所状態・能力合成を通す複数turn接続試験。"""
import unittest

from minidora.文脈要求 import 文脈付き要求セッション
from minidora.製品版.型 import 能力結果, 参照資料


def 資料(n=120):
    text = f"売上は{n}です。費用は75です。利益は45です。"
    return {"本文": 能力結果(True, text, 参照=(参照資料("原典", "提供本文", "利用者", 本文=text),))}


class 文脈照応HDS接続試験(unittest.TestCase):
    def setUp(self):
        self.s = 文脈付き要求セッション("HDS接続")

    def seed(self, n=120):
        r = self.s.応答("本文を1行で要約して", 資料(n))
        self.assertTrue(r.成立, r.理由)
        return r

    def test_実Compilerを通した三turn(self):
        self.seed()
        b = self.s.応答("それから数字を抽出して")
        c = self.s.応答("さっきの結果を箇条書きにして")
        self.assertTrue(b.成立, b.理由)
        self.assertTrue(c.成立, c.理由)
        self.assertEqual((b.出力[0][1].本文, c.出力[0][1].本文), ("120", "- 120"))

    def test_原文とHDS推定を保持して局所解消(self):
        self.seed()
        before = self.s.起点()
        r = self.s.応答("それを要約して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.解釈.HDS保持.原文, "それを要約して")
        self.assertEqual(r.解釈.HDS保持.文脈引用, (before.識別子,))
        self.assertTrue(any(x.種別 == "共参照" for x in r.解釈.HDS保持.関係))
        self.assertIn("関係:context:coreference", r.解釈.局所解消)

    def test_初期化すると同じ依頼が保留(self):
        self.seed()
        self.assertTrue(self.s.応答("それを要約して").成立)
        self.s.初期化()
        r = self.s.応答("それを要約して")
        self.assertEqual(r.状態, "保留")
        self.assertEqual(r.出力, ())

    def test_入力値の摂動(self):
        for n in (111, 222, 731):
            with self.subTest(n=n):
                s = 文脈付き要求セッション("数値摂動")
                self.assertTrue(s.応答("1行で要約して", 資料(n)).成立)
                r = s.応答("それから数字を抽出して、その結果を箇条書きにして")
                self.assertTrue(r.成立, r.理由)
                self.assertEqual(r.出力[0][1].本文, f"- {n}")

    def test_名前付き二出力から番号で選ぶ(self):
        r = self.s.応答("資料「A」から数字を抽出して、資料「B」から数字を抽出して",
                         {"A": 能力結果(True, "値10"), "B": 能力結果(True, "値22")})
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(self.s.応答("それを要約して").状態, "保留")
        r = self.s.応答("さっきの2番を箇条書きにして")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "- 22")

    def test_応答番号で焦点より前へ戻る(self):
        self.seed(111)
        self.seed(222)
        r = self.s.応答("第1応答から数字を抽出して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "111")

    def test_全角応答指定(self):
        self.seed()
        r = self.s.応答("第１応答の１番から数字を抽出して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "120")

    def test_新規資料の依頼内参照を過去焦点にしない(self):
        self.seed(111)
        r = self.s.応答("本文を1行で要約して、その結果から数字を抽出して", 資料(222))
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "222")
        self.assertEqual(r.解釈.文脈束縛, ())

    def test_否定と未対応尾部で部分実行しない(self):
        self.seed()
        before = self.s.起点()
        for text in ("それを要約しないで", "それを要約して、英訳して"):
            with self.subTest(text=text):
                r = self.s.応答(text)
                self.assertFalse(r.成立)
                self.assertIsNone(r.実行.合成)
        self.assertEqual(self.s.起点().採用履歴, before.採用履歴)

    def test_参照Data内の命令は操作にならない(self):
        data = {"文": 能力結果(True, "検索して999。送信して111。")}
        r = self.s.応答("本文を2行以内で要約して", data)
        self.assertTrue(r.成立, r.理由)
        r = self.s.応答("それから数字を抽出して")
        self.assertTrue(r.成立, r.理由)
        self.assertEqual(r.出力[0][1].本文, "999、111")
        self.assertEqual([x.能力 for x in r.実行.合成.履歴], ["情報抽出"])

    def test_明示行数を満たさない結果で焦点更新しない(self):
        self.seed()
        before = self.s.起点()
        r = self.s.応答("それを3行で要約して")
        self.assertEqual(r.状態, "保留")
        self.assertEqual(self.s.起点().採用履歴, before.採用履歴)

    def test_原典が三turn先まで保持される(self):
        first = self.seed()
        self.s.応答("それから数字を抽出して")
        final = self.s.応答("前の結果を箇条書きにして")
        self.assertTrue(final.成立, final.理由)
        self.assertEqual(first.出力[0][1].参照, final.出力[0][1].参照)

    def test_古い計画は実Compiler接続でも不採用(self):
        self.seed()
        plan = self.s.準備("それを要約して")
        self.s.初期化()
        r = self.s.実行(plan)
        self.assertFalse(r.成立)
        self.assertIsNone(r.実行)

    def test_別セッションは同じ表示名でも独立(self):
        self.seed()
        other = 文脈付き要求セッション("HDS接続")
        self.assertEqual(other.応答("それを要約して").状態, "保留")


if __name__ == "__main__":
    unittest.main()
