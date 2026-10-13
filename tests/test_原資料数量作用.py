"""原資料の数量格と条件結合の局所契約。外部取得・製品・正式受入は含まない。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from test_原資料条件作用 import 読む, 構造を作る
from minidora.HDS運用.資料作用射影 import 条件作用を結ぶ
from minidora.HDS運用.資料回答 import _条件を結ぶ
from minidora.HDS運用.内容構成 import _文章, 資料文章を照合, 資料文章を検査, 資料文章を再表現


class 原資料数量作用試験(unittest.TestCase):
    def test_数量を動作へ混ぜず同じ対象物と動作に例外を結ぶ(self):
        for 対象, 数量, 動作 in (("荷物", "3箱", "受領"), ("機器", "１２台", "点検"), ("資料", "二枚", "複写")):
            with self.subTest(数量=数量):
                本文 = "作業員は" + 対象 + "を" + 数量 + 動作 + "する。ただし休業日は" + 対象 + "を" + 動作 + "しない。"
                記載 = 読む(本文)
                作用 = 記載[0]["資料作用"]["作用"]
                self.assertEqual(作用["動作基本形"], 動作 + "する")
                self.assertEqual(作用["役割"]["数量"]["原文"], 数量)
                self.assertEqual(作用["役割"]["対象物"]["値"], 対象)
                for 座標 in 記載[0]["資料作用"]["座標"]:
                    if "原文" in 座標["内容"]:
                        左, 右 = 座標["原文範囲"]
                        self.assertEqual(本文[左:右], 座標["内容"]["原文"])
                適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
                self.assertTrue(適用["確定"])
                self.assertEqual(適用["候補"], [記載[0]["ID"]])

    def test_数量を省略した帰結から複数の同動作を一つに絞らない(self):
        記載 = 読む("作業員は機器を3台点検する。作業員は機器を4台点検する。ただし休業日は機器を点検しない。")
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertFalse(適用["確定"])
        self.assertEqual(適用["候補"], [行["ID"] for 行 in 記載[:2]])
        with self.assertRaisesRegex(ValueError, "未確定"):
            _条件を結ぶ(記載, {記載[0]["ID"]})

    def test_明示数量の帰結は一致する数量だけを参照する(self):
        記載 = 読む("作業員は機器を3台点検する。作業員は機器を4台点検する。ただし休業日は機器を3台点検しない。")
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertTrue(適用["確定"])
        self.assertEqual(適用["候補"], [記載[0]["ID"]])

    def test_再作用と単純作用を数量があっても同一視しない(self):
        記載 = 読む("作業員は資料を3枚送信する。作業員は資料を3枚再送信する。ただし休業日は資料を送信しない。")
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertTrue(適用["確定"])
        self.assertEqual(適用["候補"], [記載[0]["ID"]])
        self.assertEqual(記載[1]["資料作用"]["作用"]["動作基本形"], "再送信する")

    def test_未読解の数量修飾と未知計量語を消さない(self):
        for 作用 in ("作業員は資料を3枚まとめて送信する。", "作業員は資料を3𠮷送信する。"):
            with self.subTest(作用=作用):
                記載 = 読む(作用 + "ただし休業日は送信しない。")
                self.assertIsNone(記載[0]["資料作用"]["作用"])
                self.assertFalse(条件作用を結ぶ(記載)[記載[-1]["ID"]]["確定"])

    def test_数量格の改変を原文再読解で拒否する(self):
        記載 = 読む("作業員は機器を3台点検する。ただし休業日は点検しない。")
        記載[0]["資料作用"]["作用"]["役割"]["数量"]["値"] = "4台"
        with self.assertRaisesRegex(ValueError, "原文読解"):
            条件作用を結ぶ(記載)

    def test_数値と例外を実内容に保持し旧内容版は再表現前に拒否する(self):
        本文 = "作業員は荷物を3箱受領する。ただし雨天時は荷物を受領しない。"
        構造 = 構造を作る(本文)
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertIn("3箱", 成果.本文)
        self.assertIn("受領する。", 成果.本文)
        self.assertNotIn("するである", 成果.本文)
        self.assertIn("雨天時", 成果.本文)
        self.assertIn("受領しない", 成果.本文)
        self.assertTrue(資料文章を検査(成果))
        self.assertEqual(成果.データ["意味成果"]["版"], "HDS資料回答内容-v21")
        self.assertEqual(成果.データ["意味成果"]["資料作用成果"]["版"], "HDS原資料作用-v10")
        旧 = deepcopy(成果)
        旧.データ["意味成果"]["版"] = "HDS資料回答内容-v6"
        保全 = deepcopy(旧)
        with patch("minidora.HDS運用.内容構成._文章", side_effect=AssertionError("旧版を再構成しない")) as 再構成:
            self.assertFalse(資料文章を検査(旧))
            with self.assertRaises(ValueError):
                資料文章を再表現(旧, "箇条書き")
            self.assertEqual(再構成.call_count, 0)
        self.assertEqual(旧, 保全)

    def test_数量作用の否定過去を採用式と原活用で表現する(self):
        for 活用 in ("する", "した", "しない", "しなかった"):
            with self.subTest(活用=活用):
                本文 = "作業員は資料を3枚複写" + 活用 + "。"
                構造 = 構造を作る(本文)
                成果 = 資料文章を照合(構造, _文章(構造))
                self.assertIn(本文, 成果.本文)
                self.assertNotIn("である", 成果.本文)
                self.assertTrue(資料文章を検査(成果))
                表現 = [項 for 項 in 成果.データ["意味成果"]["演算"] if 項.get("種別") == "原主述終止表現"]
                self.assertEqual(len(表現), 1)
                self.assertEqual(表現[0]["態"], "能動数量作用")
                self.assertIn("数量", [項["役割"] for 項 in 表現[0]["役割範囲"]])

    def test_数量作用と別の採用式を原文表現で接続しない(self):
        from minidora.HDS運用.資料回答 import _主述を表現
        記載 = 読む("作業員は資料を3枚複写する。")
        記載[0]["命題"]["述語"] = "資料を4枚複写する"
        with self.assertRaisesRegex(ValueError, "採用命題"):
            _主述を表現(記載[0])

    def test_数量作用の脚注を命題や活用へ混ぜず原注記を保つ(self):
        本文 = "作業員は資料を3枚複写する[7]。"
        構造 = 構造を作る(本文)
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertIn(本文, 成果.本文)
        self.assertTrue(資料文章を検査(成果))
        記載 = 成果.データ["意味成果"]["記載関係"][0]
        self.assertEqual(記載["命題"]["述語"], "資料を3枚複写する")
        self.assertEqual(記載["脚注"][0]["原文"], "[7]")

    def test_既存未読解述語でも末尾脚注だけを元のまま保持する(self):
        from minidora.HDS運用.資料回答 import _主述を表現
        from minidora.命題解釈 import 命題を表現
        from minidora.命題構造 import 原子
        記載 = 読む("試験器はフナリ[7]。")
        本文, 表現 = _主述を表現(記載[0])
        self.assertEqual(本文, 命題を表現(原子("フナリ", "試験器")) + "[7]。")
        self.assertIsNone(表現)
        self.assertEqual(記載[0]["脚注"][0]["原文"], "[7]")

    def test_旧作用束は読み替えず版不一致を拒否する(self):
        記載 = 読む("作業員は機器を点検する。ただし休業日は点検しない。")
        記載[0]["資料作用"]["版"] = "HDS原資料作用-v3"
        保全 = deepcopy(記載)
        with self.assertRaisesRegex(ValueError, "版"):
            条件作用を結ぶ(記載)
        self.assertEqual(記載, 保全)


if __name__ == "__main__":
    unittest.main()
