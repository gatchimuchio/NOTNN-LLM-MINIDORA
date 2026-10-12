"""自己述定の有限対照。原資料の純粋読解のみ。製品・Compiler・文章生成なし。"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from test_原資料条件作用 import 読む
from minidora.HDS運用.資料作用射影 import 資料作用版, 条件作用を結ぶ, 資料作用成果
from minidora.HDS運用.資料回答 import _条件を結ぶ
from minidora.HDS運用.値 import 正準


class 原資料自己述定試験(unittest.TestCase):
    def 自己を読む(self, 文):
        記載 = 読む(文)
        局所 = 記載[0]["資料作用"]["局所範囲"]
        self.assertIsNotNone(局所)
        self.assertEqual(局所["自己述定証明"]["読了候補数"], 1)
        self.assertFalse(局所["自己述定証明"]["内部主体補完"])
        self.assertFalse(記載[0]["資料作用"]["条件候補"])
        self.assertIsNone(記載[0]["資料作用"]["条件"])
        条件作用を結ぶ(記載)
        return 記載, 局所

    def test_明示v5と題材を限定しない存在分類(self):
        self.assertEqual(資料作用版, "HDS原資料作用-v5")
        for 文 in (
            "装置が停止する場合は、故障して停止する場合と点検して停止する場合がある。",
            "機器が作動する場合は、操作者が検査する場合と担当者が測定する場合がある。",
            "担当者が確認する場合は、点検する場合がある。",
        ):
            with self.subTest(文=文):
                記載, 局所 = self.自己を読む(文)
                self.assertEqual(局所["種別"], "条件付き場合名詞の存在述定")
                self.assertIsNone(局所["外側非動作証明"])
                self.assertTrue(記載[0]["資料作用"]["動作核候補"])
                self.assertEqual(len(局所["場合列挙"]), 文.count("場合") - 1)
                self.assertEqual(len(局所["自己述定証明"]["全境界候補"]), 文.count("場合"))
                self.assertEqual(sum(項["採用"] for 項 in 局所["自己述定証明"]["全境界候補"]), 1)

    def test_内部省略主体を外側へ補完せず残差に保持(self):
        文 = "装置が停止する場合は、故障して停止する場合と点検して停止する場合がある。"
        記載, 局所 = self.自己を読む(文)
        self.assertEqual(局所["元主体"]["原文"], "装置")
        self.assertTrue(all(項["明示主体"] is None and 項["主体状態"] == "未明示" for 項 in 局所["内部事象"]))
        残差 = [項 for 項 in 記載[0]["資料作用"]["残差"] if 項["種別"] == "自己述定内部主体未明示"]
        self.assertEqual(len(残差), 4)
        self.assertNotIn("装置", [項["原文"] for 項 in 残差])
        self.assertIsNone(記載[0]["命題"])

    def test_連用節の時制を終止節から補完しない(self):
        _, 局所 = self.自己を読む("装置が停止する場合は、点検して検査した場合がある。")
        self.assertEqual([項["時制"] for 項 in 局所["内部事象"]], ["未明示", "過去"])
        self.assertTrue(all(項["明示主体"] is None for 項 in 局所["内部事象"]))

    def test_内部の別明示主体と原範囲を維持(self):
        文 = "機器が停止する場合は、操作者が点検する場合と担当者が検査する場合がある。"
        _, 局所 = self.自己を読む(文)
        self.assertEqual([項["明示主体"]["原文"] for 項 in 局所["内部事象"]], ["操作者", "担当者"])
        self.assertEqual(局所["元主体"]["原文"], "機器")
        for 項 in 局所["範囲"] + 局所["字句"]:
            self.assertEqual(文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))

    def test_純名詞推量は推定状態と原モダリティを保持(self):
        文 = "ただし記録は、恐らく機器の記録に違いない。"
        記載, 局所 = self.自己を読む(文)
        self.assertEqual(局所["種別"], "明示主体の推量付き名詞述定")
        self.assertEqual(局所["元主体"]["原文"], "記録")
        self.assertEqual(局所["内容状態"], "推定")
        self.assertEqual(局所["モダリティ"]["値状態"], "推定")
        self.assertEqual([項["原文"] for 項 in 局所["モダリティ"]["範囲"]], ["恐らく", "に違いない"])
        self.assertIsNotNone(局所["外側非動作証明"])
        self.assertEqual(局所["内部事象"], [])
        座標 = next(項 for 項 in 記載[0]["資料作用"]["座標"] if 項["座標ID"] == 局所["座標ID"])
        self.assertEqual(座標["値状態"], "推定")
        self.assertEqual(記載[0]["資料作用"]["関係"][-1]["値状態"], "推定")
        self.assertIsNone(記載[0]["命題"])

    def test_動詞名詞化推量は非動作へ除外せず内部動作を保持(self):
        文 = "ただし装置は、恐らく機器を点検するものに違いない。"
        記載, 局所 = self.自己を読む(文)
        self.assertFalse(局所["単純名詞述定"])
        self.assertIsNone(局所["外側非動作証明"])
        self.assertFalse(局所["自己述定証明"]["外部条件競合除外"])
        self.assertEqual(局所["内部事象"][0]["用言原文"], "点検する")
        self.assertIsNone(局所["内部事象"][0]["明示主体"])
        self.assertEqual(記載[0]["資料作用"]["動作核候補"], ["点検する"])
        self.assertIsNone(記載[0]["命題"])

    def test_内部動作の推量や存在分類で外部例外を誤一意化しない(self):
        for 内文 in (
            "ただし装置は、恐らく機器を点検するものに違いない。",
            "装置が停止する場合は、点検する場合と検査する場合がある。",
        ):
            with self.subTest(内文=内文):
                記載 = 読む("操作者は機器を点検する。" + 内文 + "ただし休業日は点検しない。")
                適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
                self.assertFalse(適用["確定"])
                self.assertIn(記載[1]["ID"], 適用["未読解競合"])
                self.assertFalse(any(項["記載ID"] == 記載[1]["ID"] for 項 in 適用["除外"]))
                with self.assertRaisesRegex(ValueError, "未確定"):
                    _条件を結ぶ(記載, {記載[0]["ID"]})

    def test_単純名詞推量の非動作証拠だけを外部条件の除外へ渡す(self):
        記載 = 読む("操作者は機器を点検する。ただし記録は、恐らく機器の記録に違いない。ただし休業日は点検しない。")
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertTrue(適用["確定"])
        self.assertEqual(適用["候補"], [記載[0]["ID"]])
        self.assertTrue(any(項["記載ID"] == 記載[1]["ID"] and 項.get("局所範囲座標ID") for 項 in 適用["除外"]))

    def test_否定未知未消費帰結と複数話題は自己型へ偽変換しない(self):
        for 文 in (
            "装置が停止する場合は、故障する場合と点検する場合がない。",
            "装置が停止する場合は、故障する場合と点検する場合がある予定です。",
            "装置が停止する場合は、故障する場合と点検する場合を文書にまとめて送信しない。",
            "装置が停止する場合は、ヌホリする場合と点検する場合がある。",
            "装置が停止する場合は、操作者は点検する場合と検査する場合がある。",
            "装置が停止する場合は、点検しない場合と検査する場合がある。",
        ):
            with self.subTest(文=文):
                記載 = 読む(文)
                self.assertIsNone(記載[0]["資料作用"]["局所範囲"])
                self.assertTrue(記載[0]["資料作用"]["条件候補"])
                self.assertFalse(条件作用を結ぶ(記載)[記載[0]["ID"]]["確定"])

    def test_推量の未知引用指示撤回時点と複雑名詞句を残す(self):
        for 文 in (
            "ただし記録は、恐らく機器の記録に違いないが、送信しない。",
            "ただし記録は、恐らくヌホリの記録に違いない。",
            "ただし上記の記録は、恐らく機器の記録に違いない。",
            "ただし記録は誤りで、恐らく機器の記録に違いない。",
            "記録員は「ただし記録は、恐らく機器の記録に違いない」と実行する。",
            "ただし休業日は、恐らく送信しないに違いない。",
            "ただし現存する多くの記録は、恐らく機器の記録に違いない。",
            "ただし記録は、恐らく機器の記録や後世では装置の状態を表すものに違いない。",
        ):
            with self.subTest(文=文):
                記載 = 読む(文)
                self.assertFalse(any(行["資料作用"]["局所範囲"] and "自己述定証明" in 行["資料作用"]["局所範囲"] for 行 in 記載))

    def test_主節の条件動作は旧厳格帰結のまま(self):
        記載 = 読む("作業員は信号を生成する。装置が作動するときに信号を生成しない。")
        self.assertIsNone(記載[-1]["資料作用"]["局所範囲"])
        self.assertTrue(記載[-1]["資料作用"]["条件候補"])
        適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
        self.assertTrue(適用["確定"])
        self.assertEqual(適用["候補"], [記載[0]["ID"]])

    def test_旧六未読外述と二非動作の責任を保つ(self):
        for 外述, 未読 in (
            ("容器を叩いて低い", True), ("回路を切る", True),
            ("端末を検査する予定です", True), ("ヌホリ", True),
            ("基準値を含めて小さい", True), ("基準値に等しく低い", True),
            ("基準値に等しい", False), ("電気的な記録です", False),
        ):
            with self.subTest(外述=外述):
                記載 = 読む("保管係は記録を保管する。操作者が測定するときに表示される数値は" + 外述 + "。ただし休業日は保管しない。")
                局所 = 記載[1]["資料作用"]["局所範囲"]
                self.assertEqual(局所["種別"], "名詞内部の条件修飾")
                self.assertEqual(局所["外側未読解"] is not None, 未読)
                self.assertEqual(局所["外側非動作証明"] is None, 未読)
                適用 = 条件作用を結ぶ(記載)[記載[-1]["ID"]]
                self.assertEqual(適用["確定"], not 未読)
                self.assertEqual(記載[1]["ID"] in 適用["未読解競合"], 未読)

    def test_先行区間込みの原字句と全記載所有を保持(self):
        文 = "作業員は信号を生成する。装置が停止する場合は、点検する場合と検査する場合がある。"
        記載 = 読む(文)
        局所 = 記載[1]["資料作用"]["局所範囲"]
        self.assertGreater(局所["開始"], 0)
        for 項 in 局所["範囲"] + 局所["字句"] + 局所["自己述定証明"]["全境界候補"]:
            self.assertEqual(文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))
        self.assertEqual(記載[1]["資料作用"]["原資料"]["全記載ID"], [行["ID"] for 行 in 記載])

    def test_自己証拠主体字句候補モダリティの改変を拒否(self):
        文 = "ただし装置は、恐らく機器を点検するものに違いない。"
        記載, _ = self.自己を読む(文)
        for 改変 in (
            lambda 値: 値["元主体"].update(原文="別主体"),
            lambda 値: 値["字句"][0].update(表層="別値"),
            lambda 値: 値["自己述定証明"].update(内部主体補完=True),
            lambda 値: 値["自己述定証明"]["全境界候補"][0].update(採用=False),
            lambda 値: 値["モダリティ"].update(値状態="確定"),
            lambda 値: 値.update(外側非動作証明={"読み": "偽非動作"}),
        ):
            改 = deepcopy(記載)
            改変(改[0]["資料作用"]["局所範囲"])
            with self.assertRaisesRegex(ValueError, "原文読解"):
                条件作用を結ぶ(改)

    def test_自己状態関係残差全記載と旧版改変を拒否(self):
        記載, 局所 = self.自己を読む("ただし装置は、恐らく機器を点検するものに違いない。")
        for 種別 in ("状態", "関係", "座標由来", "関係由来", "残差", "残差ID", "残差影響", "余剰残差", "全記載", "旧版"):
            改 = deepcopy(記載)
            束 = 改[0]["資料作用"]
            if 種別 == "状態":
                next(項 for 項 in 束["座標"] if 項["座標ID"] == 局所["座標ID"])["値状態"] = "確定"
            elif 種別 == "関係":
                束["関係"][-1]["終点"] = ("不存在",)
            elif 種別 == "座標由来":
                next(項 for 項 in 束["座標"] if 項["座標ID"] == 局所["座標ID"])["由来"] = "偽資料"
            elif 種別 == "関係由来":
                束["関係"][-1]["由来"] = "偽資料"
            elif 種別 == "残差":
                束["残差"] = []
            elif 種別 == "残差ID":
                束["残差"][0]["残差ID"] = "不存在"
            elif 種別 == "残差影響":
                束["残差"][0]["影響座標"] = ("不存在",)
            elif 種別 == "余剰残差":
                束["残差"].append(deepcopy(束["残差"][0]))
            elif 種別 == "全記載":
                束["原資料"]["全記載ID"] = []
            else:
                束["版"] = "HDS原資料作用-v4"
            with self.assertRaises(ValueError):
                条件作用を結ぶ(改)

    def test_意味成果の厳格正準保存と字句供給失敗を保持(self):
        記載, _ = self.自己を読む("装置が停止する場合は、点検する場合と検査する場合がある。")
        保存 = json.loads(json.dumps(正準(記載), ensure_ascii=False, allow_nan=False))
        条件作用を結ぶ(保存)
        self.assertEqual(正準(資料作用成果(記載)), 正準(資料作用成果(保存)))
        改 = deepcopy(記載)
        改[0]["資料作用"]["局所範囲"]["自己述定証明"]["読了候補数"] = float("nan")
        with self.assertRaises(ValueError):
            正準(改)
        with patch("minidora.会話字句.会話字句を観測", side_effect=ValueError("辞書失敗")):
            # 宣言されている字句不成立以外の障害も成功へ変えない。
            with self.assertRaises(ValueError):
                読む("装置が停止する場合は、点検する場合と検査する場合がある。")

    def test_全束の同値根拠ID複製を索引化前に拒否(self):
        for 文 in (
            "装置が停止する場合は、点検する場合と検査する場合がある。",
            "操作者は部品を加工する。ただし機械は、おそらく部品を加工したものに違いない。ただし休業日は加工しない。",
            "作業員は信号を生成する。装置が作動するときに信号を生成しない。",
        ):
            with self.subTest(文=文):
                記載 = 読む(文)
                # 自己型以外の原作用・条件を含め、正常束は変更せず保存できる。
                資料作用成果(記載)
                for 列, 鍵 in (("座標", "座標ID"), ("関係", "関係ID"), ("残差", "残差ID")):
                    for 番号, 行 in enumerate(記載):
                        if not 行["資料作用"][列]:
                            continue
                        改 = deepcopy(記載)
                        改[番号]["資料作用"][列].append(deepcopy(改[番号]["資料作用"][列][-1]))
                        for 検査 in (条件作用を結ぶ, 資料作用成果):
                            with self.assertRaisesRegex(ValueError, 鍵 + "重複"):
                                検査(改)

    def test_記載及び別記載間の意味作用ID重複も拒否(self):
        記載 = 読む("操作者は部品を加工する。点検員は機器を点検する。")
        資料作用成果(記載)
        改 = deepcopy(記載)
        改[1]["資料作用"]["意味作用"]["作用ID"] = 改[0]["資料作用"]["意味作用"]["作用ID"]
        with self.assertRaisesRegex(ValueError, "作用ID重複"):
            資料作用成果(改)
        改 = deepcopy(記載)
        改.append(deepcopy(改[0]))
        with self.assertRaisesRegex(ValueError, "記載ID重複"):
            資料作用成果(改)


if __name__ == "__main__":
    unittest.main()
