"""原主述の終止・格・引用を保持する局所表示対照。製品入口は実行しない。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import (
    _文章, 資料文章を照合, 資料文章を検査, 資料文章を再表現, 資料文章の版を検査,
)
from minidora.HDS運用.資料回答 import 記載関係を読む, _主述を表現, _作用を読む
from minidora.HDS運用.値 import 結果を保存
from minidora.命題構造 import 原子
from minidora.命題解釈 import 命題を表現
from minidora.製品版.型 import 能力結果


def 構造を作る(本文, *, 形式="文章", 操作="説明"):
    要求 = {"版": "HDS一般会話要求-v2", "対象": [], "主題": [], "操作": [操作],
            "形式": 形式, "範囲": "自動", "最大文字数": 24000,
            "問い": "原主述の表示の開発対照", "比較対象": [], "観点": [],
            "詳細": "標準", "提示本文": 本文, "関係焦点": [], "肯否": "未指定"}
    return 資料意味を選ぶ({"表示資料": 能力結果(True, 本文)}, 要求)


def 表示する(本文, **設定):
    構造 = 構造を作る(本文, **設定)
    return 資料文章を照合(構造, _文章(構造))


class 資料主述表現試験(unittest.TestCase):
    def test_ヲ格動詞の非過去過去否定と敬体を保持(self):
        for 活用 in ("する", "します", "した", "しました", "しない", "しません", "しなかった"):
            原文 = "検品班が部材を分類" + 活用 + "。"
            with self.subTest(活用=活用):
                成果 = 表示する(原文)
                self.assertEqual(成果.本文, 原文)
                self.assertNotIn("である", 成果.本文)
                self.assertTrue(資料文章を検査(成果))

    def test_明示行為者受動の態時制否定を能動へ戻さない(self):
        for 活用 in ("される", "されます", "された", "されました", "されない", "されません", "されなかった"):
            原文 = "部材は検品班により分類" + 活用 + "。"
            with self.subTest(活用=活用):
                成果 = 表示する(原文)
                self.assertEqual(成果.本文, 原文)
                証拠 = 成果.データ["意味成果"]["演算"][-1]
                self.assertEqual(証拠["態"], "受動")
                self.assertTrue(資料文章を検査(成果))

    def test_受動の主格と行為者格を原文から保つ(self):
        原文 = "試験票が担当班によって処理された。"
        成果 = 表示する(原文)
        self.assertEqual(成果.本文, 原文)
        役割 = 成果.データ["意味成果"]["演算"][-1]["役割範囲"]
        self.assertEqual([(項["役割"], 項["原文"]) for 項 in 役割[:4]],
                         [("対象物", "試験票"), ("主格", "が"), ("対象", "担当班"), ("行為者格", "によって")])

    def test_ヲ格のない既存サ変活用も一意な元読みから表現(self):
        for 述部 in ("作動する", "作動した", "作動しない", "作動している", "作動していない", "作動できる", "作動できない"):
            原文 = "試験器が" + 述部 + "。"
            with self.subTest(述部=述部):
                成果 = 表示する(原文)
                self.assertEqual(成果.本文, 原文)
                self.assertTrue(資料文章を検査(成果))

    def test_名詞述語のコピュラを動詞扱いで削らない(self):
        成果 = 表示する("試験器は観測用の器具である。")
        self.assertIn("試験器は観測用の器具です。", 成果.本文)
        self.assertFalse(any(項["種別"] == "原主述終止表現" for 項 in 成果.データ["意味成果"]["演算"]))

    def test_語尾が動作形でも明示名詞として記された場合は動詞へ変えない(self):
        行 = {"ID": "名詞対照", "対応": {"資料": "名詞資料", "開始": 0, "終了": 13,
             "原文": "項目甲は分類するである。"}, "命題": 原子("分類する", "項目甲").辞書()}
        本文, 証拠 = _主述を表現(行)
        self.assertEqual(本文, "項目甲は分類するである。")
        self.assertIsNone(証拠)

    def test_明示名詞否定の終止を保つ(self):
        for 活用 in ("ではない", "ではありません", "じゃない", "じゃありません", "でない"):
            原文 = "担当者は監督者" + 活用 + "。"
            with self.subTest(活用=活用):
                成果 = 表示する(原文)
                self.assertEqual(成果.本文, 原文)
                self.assertEqual(成果.データ["意味成果"]["演算"][-1]["態"], "名詞述語")

    def test_修飾内の動詞と引用文字列を文末置換しない(self):
        原文 = "方式甲とは「処理するである」という名称を持つ手順である。"
        成果 = 表示する(原文)
        self.assertIn("「処理するである」", 成果.本文)
        self.assertIn("という名称を持つ手順です。", 成果.本文)
        self.assertTrue(資料文章を検査(成果))

    def test_未知述語は新しい活用や意味を付け足さない(self):
        行 = 記載関係を読む(構造を作る("試験器はフナリ。"))[0]
        本文, 証拠 = _主述を表現(行)
        self.assertEqual(本文, 命題を表現(原子("フナリ", "試験器")) + "。")
        self.assertIsNone(証拠)

    def test_引用帰属を外側動作へ変えて採用しない(self):
        行 = 記載関係を読む(構造を作る("担当者は「試験器は作動する」と述べた。"))[0]
        self.assertIsNone(行["命題"])
        with self.assertRaisesRegex(ValueError, "未読解"):
            表示する(行["対応"]["原文"])

    def test_各役割の絶対原文範囲と支持式が採用命題に一致(self):
        原文 = "試験器は観測用の器具である。\n検品班が部材を分類した。"
        成果 = 表示する(原文)
        意味 = 成果.データ["意味成果"]
        証拠 = next(項 for 項 in 意味["演算"] if 項["種別"] == "原主述終止表現")
        行 = next(項 for 項 in 意味["記載関係"] if 項["ID"] == 証拠["記載ID"])
        self.assertEqual(証拠["支持式"], 行["命題"])
        self.assertGreater(証拠["対応"]["開始"], 0)
        for 役割 in 証拠["役割範囲"]:
            self.assertEqual(原文[役割["開始"]:役割["終了"]], 役割["原文"])

    def test_採用命題の異主体や異動作は原主述表現で拒否(self):
        行 = 記載関係を読む(構造を作る("検品班は部材を分類する。"))[0]
        for 式 in (原子("部材を分類する", "別班"), 原子("部材を処理する", "検品班")):
            with self.subTest(式=式):
                変 = deepcopy(行)
                変["命題"] = 式.辞書()
                with self.assertRaisesRegex(ValueError, "作用式.*不一致"):
                    _主述を表現(変)

    def test_表現役割の範囲改変は原文全被覆で拒否(self):
        行 = 記載関係を読む(構造を作る("検品班は部材を分類する。"))[0]
        作用 = _作用を読む(行["対応"]["原文"])
        作用["表現"][-1]["開始"] += 1
        with patch("minidora.HDS運用.資料回答._作用を読む", return_value=作用):
            with self.assertRaisesRegex(ValueError, "被覆"):
                _主述を表現(行)

    def test_脚注を終止の再構成で消さない(self):
        成果 = 表示する("検品班は部材を分類する[7]。")
        self.assertEqual(成果.本文, "検品班は部材を分類する[7]。")

    def test_条件否定は本体の表示修理後も全文同伴(self):
        原文 = "検品班は部材を分類する。ただし休業日は分類しない。"
        成果 = 表示する(原文, 操作="要約")
        self.assertIn("分類する。", 成果.本文)
        self.assertIn("ただし休業日は分類しない。", 成果.本文)
        self.assertNotIn("するである", 成果.本文)
        self.assertTrue(資料文章を検査(成果))

    def test_文章箇条書き引用形式の再表現も同じ主述と原構造を保つ(self):
        成果 = 表示する("検品班は部材を分類しない。")
        for 形式 in ("文章", "箇条書き", "引用"):
            with self.subTest(形式=形式):
                再 = 資料文章を再表現(成果, 形式)
                self.assertIn("検品班は部材を分類しない。", 再.本文)
                self.assertEqual(再.データ["構造"], 成果.データ["構造"])
                self.assertEqual(再.データ["意味成果"], 成果.データ["意味成果"])
                self.assertTrue(資料文章を検査(再))

    def test_旧v3は再生成前に拒否し原保存を変えない(self):
        成果 = 表示する("検品班は部材を分類する。")
        self.assertEqual(成果.データ["意味成果"]["版"], "HDS資料回答内容-v21")
        成果.データ["意味成果"]["版"] = "HDS資料回答内容-v3"
        原保存 = deepcopy(結果を保存(成果))
        with patch("minidora.HDS運用.内容構成.資料文章を照合", side_effect=AssertionError("旧v3の再生成")):
            self.assertFalse(資料文章を検査(成果))
            with self.assertRaisesRegex(ValueError, "意味保存版.*失効.*再計算"):
                資料文章を再表現(成果, "文章")
            with self.assertRaisesRegex(ValueError, "意味保存版.*失効.*再計算"):
                資料文章の版を検査(成果)
        self.assertEqual(結果を保存(成果), 原保存)


if __name__ == "__main__":
    unittest.main()
