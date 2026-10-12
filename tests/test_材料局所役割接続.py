"""命題未型の別題材材料を、局所原役割と未読に分ける有限接続。"""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from test_主張採用検討接続 import 人工, 読む, 終端, 内容能力
from minidora.HDS運用.関係言語 import 材料局所役割を読む
from minidora.HDS運用.関係読解 import 関係資料を検査
from minidora.HDS運用.関係内容 import 関係回答を検査
from minidora.HDS運用.値 import 結果を保存, 結果を復元
from minidora.製品版.型 import 能力結果


class 材料局所役割有限接続(TestCase):
    def 四成果を確認(self, P, 材料, 数量, 動作, 前提, 未実施):
        _, 入力, 解釈 = 人工(P, 材料, "保証要求")
        供給, 値, 回答 = 終端(解釈, 入力)
        構造 = 回答.データ["構造"]
        self.assertEqual(構造["版"], "HDS主張採用読解-v2")
        self.assertEqual(回答.データ["版"], "HDS主張採用回答-v2")
        self.assertIsNone(構造["P読解"]["式"])
        self.assertEqual(構造["P読解"]["原主張"]["本文"], P)
        self.assertEqual(len(構造["P読解"]["未型範囲"]), 4)
        self.assertFalse(構造["行為検討"]["要求行為実行"])
        self.assertEqual(構造["行為検討"]["保証"], "未認定")
        行 = 構造["資料群"]["提示本文"]
        self.assertIsNone(行["判定"])
        self.assertEqual(行["採用記載"], [])
        self.assertEqual(行["読解"], [])
        局所 = [項 for 原 in 行["材料局所読解"] for 項 in 原["読解"]]
        self.assertEqual([項["種別"] for 項 in 局所], ["名詞述部連用", "明示格用言記載", "話題用言記載"])
        for 項 in 局所:
            self.assertEqual(項["原文"], 材料[slice(*項["範囲"])])
            self.assertIsNone(項["明示主体"])
            self.assertIsNone(項["式"])
            self.assertFalse(項["推論採用"])
            self.assertFalse(項["主体補完"])
            self.assertFalse(項["時点補完"])
            for 字 in 項["字句"]:
                self.assertEqual(字["表層"], 材料[字["開始"]:字["終了"]])
        self.assertEqual(局所[0]["役割"]["名詞述部"]["原文"], 数量)
        self.assertFalse(局所[0]["役割"]["数量原形"]["数値変換"])
        話題 = 局所[2]["役割"]["話題NP"]
        self.assertEqual(話題["連体前提"]["原文"], 前提)
        self.assertEqual(話題["連体前提"]["主体状態"], "未明示")
        self.assertFalse(話題["連体前提"]["名詞主要部への主体補完"])
        self.assertEqual(局所[2]["役割"]["未完了標識"]["原文"], "まだ")
        self.assertEqual(局所[2]["役割"]["用言"]["肯否"], "否定")
        for 文 in (数量, 動作, 前提, 未実施, "実施状況・結果・適用対象と条件", "必要条件や反証と認定していません"):
            self.assertIn(文, 回答.本文)
        self.assertTrue(関係資料を検査(構造))
        self.assertTrue(関係回答を検査(回答))
        self.assertEqual(結果を保存(結果を復元(結果を保存(回答))), 結果を保存(回答))
        self.assertTrue(供給.最終検証(SimpleNamespace(成果=tuple(値.items())), None))
        for 名 in ("関係読解", "関係内容構成", "関係文章生成", "関係回答照合"):
            self.assertIn("運用計画:0/成果/" + 名, 値)
        return 構造, 回答, 供給, 値

    def test_F01_容器材料で三原役割と四実成果を保存(self):
        self.四成果を確認("この容器なら冷却しても必ず半年保存できる",
            "箱の容量は三リットルで、内面を清掃している。冷蔵庫に入れた保存試験はまだ実施していない。",
            "三リットル", "清掃している", "冷蔵庫に入れた", "まだ実施していない")

    def test_F02_電気材料で別値別単位別前提を保存(self):
        self.四成果を確認("この端末なら振動しても必ず二年間作動する",
            "端末の電圧は五ボルトで、接点を洗浄している。試験室に置いた動作検査はまだ実施していない。",
            "五ボルト", "洗浄している", "試験室に置いた", "まだ実施していない")

    def test_F03_形容詞名詞化と数詞原形も型内で保持(self):
        文 = "紙の長さは四センチで、端部を加工している"
        読 = 材料局所役割を読む(文, 起点=7)
        self.assertEqual(len(読["読解"]), 2)
        項 = 読["読解"][0]
        self.assertEqual(項["役割"]["話題NP"]["原名詞句"]["原文"], "紙の長さ")
        self.assertEqual(項["役割"]["数量原形"]["数詞"]["原文"], "四")
        for 項 in 読["読解"]:
            self.assertEqual(項["原文"], 文[項["範囲"][0] - 7:項["範囲"][1] - 7])
            self.assertIsNone(項["明示主体"])

    def test_F04_明示主格だけを保存し対象から主体を補完しない(self):
        前 = 材料局所役割を読む("接点を洗浄している")["読解"][0]
        後 = 材料局所役割を読む("作業者が接点を洗浄している")["読解"][0]
        self.assertIsNone(前["明示主体"])
        self.assertEqual(後["明示主体"]["名詞句"]["原名詞句"]["原文"], "作業者")
        self.assertEqual(後["役割"]["明示格"]["を"]["名詞句"]["原名詞句"]["原文"], "接点")
        self.assertFalse(後["推論採用"])

    def test_F05_全未読と例外隔離では内容不足を保持(self):
        for 材料 in ("未詳な複雑な条件を伴うもの。",
                    "端末の電圧は五ボルトで、接点を洗浄している。ただし例外の範囲は不明。"):
            _, 入力, 解釈 = 人工(材料=材料)
            構造 = 読む(解釈, 入力)
            結果 = 内容能力(構造)
            self.assertFalse(結果.成立)
            self.assertEqual(結果.データ["構造"], 構造)
            self.assertTrue(構造["資料群"]["提示本文"]["残差"])

    def test_F06_未知引用指示限定多格及び未完了の肯定化を読まない(self):
        for 文 in ("接点をZXQ検査している", "作業者は「接点を洗浄している」と述べた",
                   "それを洗浄している", "接点を洗浄しているなら作動する", "接点だけを洗浄している",
                   "作業者が担当者が接点を洗浄している", "紙の長さは四謎単位で",
                   "試験室に置いた検査はまだ実施している", "接点を洗浄するかもしれない"):
            with self.subTest(文=文):
                読 = 材料局所役割を読む(文)
                self.assertEqual(読["読解"], [])
                self.assertTrue(読["残差"])

    def test_F07_読めた値と未読残差の原区間を分離(self):
        文 = "端末の電圧は五ボルトで、原因は複雑なものです"
        読 = 材料局所役割を読む(文)
        self.assertEqual(len(読["読解"]), 1)
        self.assertEqual(len(読["残差"]), 1)
        for 項 in 読["読解"] + 読["残差"]:
            self.assertEqual(項["原文"], 文[slice(*項["範囲"])])
        self.assertEqual(読["残差"][0]["原文"], "原因は複雑なものです")

    def test_F08_全源再導出で原範囲値単位主体否定を改変できない(self):
        材料 = "端末の電圧は五ボルトで、接点を洗浄している。試験室に置いた動作検査はまだ実施していない。"
        _, 入力, 解釈 = 人工("この端末なら必ず二年間作動する", 材料, "保証要求")
        構造 = 読む(解釈, 入力)
        self.assertTrue(関係資料を検査(構造))
        for 種 in ("範囲", "値", "主体", "否定", "必要内容寄与", "P"):
            改 = deepcopy(構造)
            原 = 改["資料群"]["提示本文"]["材料局所読解"]
            if 種 == "範囲": 原[0]["読解"][0]["範囲"][0] += 1
            elif 種 == "値": 原[0]["読解"][0]["役割"]["数量原形"]["計量名詞"]["原文"] = "アンペア"
            elif 種 == "主体": 原[0]["読解"][1]["明示主体"] = {"原文": "端末"}
            elif 種 == "否定": 原[1]["読解"][0]["役割"]["用言"]["肯否"] = "肯定"
            elif 種 == "必要内容寄与": 原[0]["読解"][0]["必要内容寄与"] = False
            else: 改["P読解"]["状態"] = "全文型成立"
            with self.subTest(種=種):
                self.assertFalse(関係資料を検査(改))

    def test_F09_旧v1を新意味へ無言再生成しない(self):
        _, 入力, 解釈 = 人工(材料="接点を洗浄している。")
        構造 = 読む(解釈, 入力)
        旧 = {**deepcopy(構造), "版": "HDS主張採用読解-v1"}
        with patch("minidora.HDS運用.関係読解.関係資料を読む", side_effect=AssertionError("旧版の再読解")):
            self.assertFalse(関係資料を検査(旧))
        旧回答 = 能力結果(True, "旧回答", データ={"版": "HDS主張採用回答-v1", "種別": "関係資料回答"})
        with patch("minidora.HDS運用.関係内容._生成", side_effect=AssertionError("旧版の再生成")):
            self.assertFalse(関係回答を検査(旧回答))


if __name__ == "__main__":
    main()
