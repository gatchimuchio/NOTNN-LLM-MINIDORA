"""原資料の局所修飾と採用根拠への条件適用。製品・外部取得は実行しない。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from test_原資料条件作用 import 読む, 構造を作る
from minidora.HDS運用.資料作用射影 import 条件作用を結ぶ
from minidora.HDS運用.資料回答 import _条件を結ぶ
from minidora.HDS運用.内容構成 import _文章, 資料文章を照合, 資料文章を検査


class 原資料局所条件試験(unittest.TestCase):
    def test_連体条件を名詞主要部と外側主格述部の原範囲へ保持する(self):
        for 原文 in (
            "装置が作動するときに生成される信号（測定用）の値は基準値に等しい。",
            "操作者が検査する場合に記録された数値は基準値に等しい。",
            "装置が作動するときに生成される信号は電気的な記録である。",
        ):
            with self.subTest(原文=原文):
                本文 = 原文 + "点検員は機器を点検する。"
                記載 = 読む(本文)
                局所 = 記載[0]["資料作用"]["局所範囲"]
                self.assertEqual(局所["種別"], "名詞内部の条件修飾")
                self.assertFalse(記載[0]["資料作用"]["条件候補"])
                self.assertIsNone(記載[0]["資料作用"]["条件"])
                self.assertIsNotNone(局所["内部作用"])
                self.assertIsNotNone(局所["外側非動作証明"])
                self.assertIsNone(局所["外側未読解"])
                self.assertTrue(局所["字句"])
                for 部分 in 局所["範囲"] + 局所["字句"]:
                    self.assertEqual(本文[部分["開始"]:部分["終了"]], 部分.get("原文", 部分.get("表層")))
                self.assertEqual(_条件を結ぶ(記載, {記載[-1]["ID"]}), {})

    def test_主節の明示帰結を連体条件へ移さない(self):
        記載 = 読む("作業員は信号を生成する。装置が作動するときに信号を生成しない。")
        self.assertIsNone(記載[-1]["資料作用"]["局所範囲"])
        self.assertTrue(記載[-1]["資料作用"]["条件候補"])
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertTrue(適用["確定"])
        self.assertEqual(適用["候補"], [記載[0]["ID"]])

    def test_未知連体と内部注記条件を局所修飾として捨てない(self):
        for 原文 in (
            "装置が作動するときにフナリされる信号は基準値に等しい。",
            "装置が作動するときに生成される信号（ただし停電時は生成しない）の値は基準値に等しい。",
        ):
            with self.subTest(原文=原文):
                記載 = 読む(原文 + "点検員は機器を点検する。")
                self.assertIsNone(記載[0]["資料作用"]["局所範囲"])
                self.assertTrue(記載[0]["資料作用"]["条件候補"])
                with self.assertRaisesRegex(ValueError, "未確定"):
                    _条件を結ぶ(記載, {記載[-1]["ID"]})

    def test_内部帰属と未読外側作用を分け競合と採用拒否へ保持する(self):
        for 原文 in (
            "担当者が確認するときに発生する信号は装置を冷やして熱い。",
            "機器が停止するときに表示される通知は回路を冷やして熱い。",
            "装置が作動するときに生成される信号は機器を停止する。",
            "装置が作動するときに生成される信号は機器を停止する予定である。",
            "装置が作動するときに生成される信号はフナリ。",
        ):
            with self.subTest(原文=原文):
                記載 = 読む("送信班は文書を送信する。" + 原文 + "ただし休業日は送信しない。")
                局所 = 記載[1]["資料作用"]["局所範囲"]
                self.assertEqual(局所["種別"], "名詞内部の条件修飾")
                self.assertIsNotNone(局所["内部作用"])
                self.assertIsNone(局所["外側非動作証明"])
                self.assertIsNotNone(局所["外側未読解"])
                self.assertEqual(局所["外側述部型"], "未読解外側作用")
                self.assertIsNone(記載[1]["命題"])
                self.assertTrue(any(項["種別"] == "原資料外側作用未読解" for 項 in 記載[1]["資料作用"]["残差"]))
                適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
                self.assertFalse(適用["確定"])
                self.assertIn(記載[1]["ID"], 適用["未読解競合"])
                with self.assertRaisesRegex(ValueError, "未読外側作用"):
                    _条件を結ぶ(記載, {記載[1]["ID"]})
                with self.assertRaisesRegex(ValueError, "未確定"):
                    _条件を結ぶ(記載, {記載[0]["ID"]})

    def test_内部名詞の属性を経由しても未読外側作用を確定へ採用しない(self):
        本文 = "装置が作動するときに生成される信号の値は装置を冷やして熱い。"
        構造 = 構造を作る(本文)
        記載 = 読む(本文)
        self.assertIsNotNone(記載[0]["資料作用"]["局所範囲"]["内部作用"])
        self.assertIsNotNone(記載[0]["関係"]["属性"])
        self.assertIsNone(記載[0]["命題"])
        with self.assertRaisesRegex(ValueError, "未読外側作用"):
            _文章(構造)

    def test_明示報告内の引用条件を外側作用に移さず裸引用は保留する(self):
        記載 = 読む("作業員は信号を生成する。記録員は「停電の場合は生成しない」と記載している。")
        局所 = 記載[-1]["資料作用"]["局所範囲"]
        self.assertEqual(局所["種別"], "明示報告内の引用条件")
        self.assertFalse(記載[-1]["資料作用"]["条件候補"])
        self.assertEqual(_条件を結ぶ(記載, {記載[0]["ID"]}), {})
        裸引用 = 読む("作業員は信号を生成する。「停電の場合は生成しない」")
        self.assertIsNone(裸引用[-1]["資料作用"]["局所範囲"])
        with self.assertRaisesRegex(ValueError, "引用帰属.*未確定"):
            _条件を結ぶ(裸引用, {裸引用[0]["ID"]})

    def test_未知の外側帰属を引用条件の免除にしない(self):
        記載 = 読む("作業員は信号を生成する。記録員は「停電の場合は生成しない」と実行する。")
        self.assertIsNone(記載[-1]["資料作用"]["局所範囲"])
        with self.assertRaisesRegex(ValueError, "未確定"):
            _条件を結ぶ(記載, {記載[0]["ID"]})

    def test_全記載の未確定作用を保持し明示除外された採用主述だけを通す(self):
        本文 = "点検員は機器を点検する。送信班は文書を送信する。別班は記録を送信する。ただし休業日は送信しない。"
        記載 = 読む(本文)
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertFalse(適用["確定"])
        self.assertEqual(適用["候補"], [記載[1]["ID"], 記載[2]["ID"]])
        照合 = []
        self.assertEqual(_条件を結ぶ(記載, {記載[0]["ID"]}, 照合記録=照合), {})
        self.assertEqual(照合[0]["除外証拠"][0]["理由"], "動作基本形が完全不一致")
        with self.assertRaisesRegex(ValueError, "未確定"):
            _条件を結ぶ(記載, {記載[1]["ID"]})
        構造 = 構造を作る(本文, 操作="説明", 主題=("点検員",))
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertTrue(資料文章を検査(成果))
        保存適用 = list(成果.データ["意味成果"]["資料作用成果"]["適用"].values())[0]
        self.assertFalse(保存適用["確定"])
        self.assertEqual(len(保存適用["候補"]), 2)
        self.assertTrue(保存適用["残差"])
        self.assertTrue(any(項["種別"] == "全記載条件の採用閉包照合" for 項 in 成果.データ["意味成果"]["演算"]))

    def test_未知帰結と広域参照を採用集合だけで除外しない(self):
        for 条件 in ("ただし休業日は文書をまとめて送信しない。", "ただし上記の休業日は送信しない。"):
            with self.subTest(条件=条件):
                記載 = 読む("点検員は機器を点検する。送信班は文書を送信する。別班は記録を送信する。" + 条件)
                with self.assertRaisesRegex(ValueError, "未確定"):
                    _条件を結ぶ(記載, {記載[0]["ID"]})

    def test_原範囲の局所証拠と帰属座標の改変を拒否する(self):
        元 = 読む("装置が作動するときに生成される信号の値は基準値に等しい。")
        改変 = deepcopy(元)
        改変[0]["資料作用"]["局所範囲"]["範囲"][3]["原文"] = "別値"
        with self.assertRaisesRegex(ValueError, "原文読解"):
            条件作用を結ぶ(改変)
        改変 = deepcopy(元)
        改変[0]["資料作用"]["局所範囲"]["座標ID"] = "不存在座標"
        with self.assertRaisesRegex(ValueError, "帰属座標"):
            条件作用を結ぶ(改変)

    def test_字句供給不能を名詞内部の証拠にしない(self):
        from minidora.会話字句 import 会話字句不成立
        with patch("minidora.会話字句.会話字句を観測", side_effect=会話字句不成立("局所対照の供給不能")):
            記載 = 読む("装置が作動するときに生成される信号の値は基準値に等しい。点検員は機器を点検する。")
            self.assertIsNone(記載[0]["資料作用"]["局所範囲"])
            with self.assertRaisesRegex(ValueError, "未確定"):
                _条件を結ぶ(記載, {記載[-1]["ID"]})


if __name__ == "__main__":
    unittest.main()
