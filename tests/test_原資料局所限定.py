"""原資料局所限定の人工有限包。Compiler/製品/問い/文章生成を使用しない。"""
from copy import deepcopy
import hashlib
import unittest

from minidora.命題句 import 構成句を分ける
from minidora.製品版.型 import 能力結果
from minidora.HDS運用.値 import 結果を保存
from minidora.HDS運用.資料作用射影 import (
    資料作用束を付す, 条件作用を結ぶ, _束を検査, 資料作用版,
)

二題材 = (
    "設備室は研修を終えた担当者だけが使える。未研修者は立会いのみで、設備を操作しない。",
    "書庫は手続を済ませた会員だけが使える。非会員は閲覧のみで、保管機器を操作しない。",
)


def 人工記載(本文, 名前="有限資料", 版="有限原資料-v1"):
    保存 = 結果を保存(能力結果(True, 本文, データ={"版": 版}))
    記載 = [{"ID": 名前 + ":" + str(左) + ":" + str(右),
        "対応": {"資料": 名前, "開始": 左, "終了": 右, "原文": 本文[左:右]},
        "関係": {鍵: None for 鍵 in ("定義", "叙述", "属性", "理由", "目的")},
        "節": 0, "段落": 本文.count("\n", 0, 左)} for 左, 右 in 構成句を分ける(本文)]
    資料作用束を付す(記載, {名前: (本文, 保存)})
    return 記載


def 限定(行):
    return 行["資料作用"]["局所限定"]["読解"]


class 原資料局所限定契約(unittest.TestCase):
    def test_二題材の主体範囲と名詞連用否定を形成する(self):
        for 本文 in 二題材:
            with self.subTest(本文=本文):
                群 = 人工記載(本文)
                self.assertEqual(限定(群[0])["状態"], "読解")
                self.assertEqual(限定(群[0])["種別"], "主体範囲限定")
                self.assertEqual(限定(群[1])["種別"], "名詞述部範囲限定と連用否定")
                self.assertEqual(限定(群[1])["役割"]["否定用言"]["肯否"], "否定")
                _束を検査(群)

    def test_連体前提のヲ格と名詞主要部を原範囲に結ぶ(self):
        for 本文, 格, 主要部 in zip(二題材, ("研修", "手続"), ("担当者", "会員")):
            with self.subTest(主要部=主要部):
                行 = 人工記載(本文)[0]
                読 = 限定(行)
                self.assertEqual(読["役割"]["連体前提格:を"]["原文"], 格)
                self.assertEqual(読["役割"]["名詞主要部"]["原文"], 主要部)
                self.assertEqual(読["役割"]["連体前提"]["主体状態"], "未明示")
                self.assertFalse(読["役割"]["連体前提"]["名詞主要部への主体補完"])
                self.assertTrue(any(辺["種別"] == "原連体前提の名詞主要部帰属" for 辺 in 行["資料作用"]["関係"]))

    def test_単純主体のみも対象限定へ移さない(self):
        読 = 限定(人工記載("会員のみが使える。")[0])
        self.assertEqual(読["状態"], "読解")
        self.assertEqual(読["役割"]["主体NP"]["原文"], "会員")
        self.assertEqual(読["役割"]["限定標識"]["原文"], "のみ")
        self.assertNotIn("否定対象物", 読["役割"])

    def test_可能辞書形と使役活用列を推測変換しない(self):
        読 = 限定(人工記載(二題材[1])[0])
        self.assertEqual(読["役割"]["用言"]["辞書形"], "使える")
        self.assertEqual(読["役割"]["用言"]["様相"], "未認定")
        self.assertFalse(読["役割"]["用言"]["別基本動詞への変換"])
        self.assertEqual(読["役割"]["連体前提"]["辞書形列"], ["済む", "せる", "た"])
        self.assertFalse(読["世界認定"] or 読["許可認定"] or 読["十分条件認定"] or 読["存在認定"])

    def test_全字句と全役割と非ゼロ起点を原sliceへ照合する(self):
        本文 = "点検員は機器を点検する。" + 二題材[0]
        群 = 人工記載(本文)
        for 行 in 群[1:]:
            読 = 限定(行)
            self.assertGreater(読["開始"], 0)
            for 項 in 読["字句"] + list(読["役割"].values()) + 読["全候補"]:
                self.assertEqual(本文[項["開始"]:項["終了"]], 項.get("原文", 項.get("表層")))
            self.assertTrue(読["全句被覆"])
        _束を検査(群)

    def test_話題と名詞述部を対象物やサ変動作へ補完しない(self):
        群 = 人工記載(二題材[0])
        self.assertEqual(限定(群[0])["役割"]["話題"]["原文"], "設備室")
        self.assertFalse(限定(群[0])["対象物補完"])
        self.assertNotIn("対象物", 限定(群[0])["役割"])
        self.assertEqual(限定(群[1])["役割"]["限定名詞"]["原文"], "立会い")
        self.assertNotIn("動作基本形", 限定(群[1])["役割"]["限定名詞"])

    def test_引用と参照と未知は全原句と候補を未読へ保持する(self):
        for 文 in ("「会員だけが使える」。", "それだけが使える。", "ヌャリミグだけが使える。"):
            with self.subTest(文=文):
                群 = 人工記載(文)
                self.assertEqual(限定(群[0])["状態"], "未読")
                self.assertTrue(限定(群[0])["全候補"])
                self.assertTrue(any(項["種別"] == "原資料限定作用域未読" for 項 in 群[0]["資料作用"]["残差"]))
                _束を検査(群)

    def test_複数標識と作用先ずれを主体限定へ採用しない(self):
        for 文 in ("会員だけが資料だけを使える。", "会員が資料だけを使える。", "会員の場合のみ使える。"):
            with self.subTest(文=文):
                群 = 人工記載(文)
                self.assertEqual(限定(群[0])["状態"], "未読")
                self.assertFalse(any(項["採用"] for 項 in 限定(群[0])["全候補"]))
                _束を検査(群)

    def test_連用の別主体と追加条件は一意主体継承にしない(self):
        for 文 in ("非会員は閲覧のみで、担当者が保管機器を操作しない。",
                "非会員は閲覧のみで、雨の場合は保管機器を操作しない。",
                "非会員は閲覧のみで、保管機器を操作しないので退出する。"):
            with self.subTest(文=文):
                self.assertEqual(限定(人工記載(文)[0])["状態"], "未読")

    def test_限定未読を旧条件の非作用除外で隠さない(self):
        本文 = "送信班は文書を送信する。会員が資料だけを使える。ただし休業日は送信しない。"
        群 = 人工記載(本文)
        群[1]["関係"]["叙述"] = {"対象": "会員", "述部": "資料"}
        適用 = 条件作用を結ぶ(群)[群[-1]["ID"]]
        self.assertFalse(適用["確定"])
        self.assertIn(群[1]["ID"], 適用["未読解競合"])

    def test_原資料所有と全記載を保全する(self):
        本文 = 二題材[0]
        群 = 人工記載(本文, 名前="資料乙", 版="原資料-v9")
        for 行 in 群:
            所有 = 行["資料作用"]["原資料"]
            self.assertEqual(所有["資料ID"], "資料乙")
            self.assertEqual(所有["原資料版"], "原資料-v9")
            self.assertEqual(所有["本文指紋"], hashlib.sha256(本文.encode()).hexdigest())
            self.assertEqual(所有["全記載ID"], [項["ID"] for 項 in 群])
        with self.assertRaises(ValueError):
            _束を検査(群[:1])

    def test_局所型とHDS根拠族の改変を再導出で拒否する(self):
        元 = 人工記載(二題材[0])
        for 改変 in (
            lambda x: x[0]["資料作用"]["局所限定"]["読解"].update(許可認定=True),
            lambda x: x[0]["資料作用"]["局所限定"]["読解"]["役割"]["限定標識"].update(終了=1),
            lambda x: x[0]["資料作用"]["局所限定"]["役割座標"].update(用言="不存在"),
            lambda x: x[1]["資料作用"]["局所限定"]["読解"]["役割"]["否定用言"].update(肯否="肯定"),
            lambda x: x[0]["資料作用"]["関係"].pop(),
            lambda x: x[0]["資料作用"]["座標"][-1].update(由来="別資料"),
        ):
            with self.subTest(改変=改変):
                群 = deepcopy(元); 改変(群)
                with self.assertRaises(ValueError): _束を検査(群)

    def test_不存在重複外付け新型IDを拒否する(self):
        元 = 人工記載(二題材[0])
        for 改変 in (
            lambda x: x[0]["資料作用"]["座標"].append(deepcopy(x[0]["資料作用"]["座標"][-1])),
            lambda x: x[0]["資料作用"]["座標"].pop(),
            lambda x: x[0]["資料作用"]["座標"][-1].update(座標ID="外付け局所ID"),
        ):
            with self.subTest(改変=改変):
                群 = deepcopy(元); 改変(群)
                with self.assertRaises(ValueError): _束を検査(群)

    def test_v7明示と旧v6保存束の無言再解釈を拒否する(self):
        self.assertEqual(資料作用版, "HDS原資料作用-v10")
        群 = 人工記載("送信班は文書を送信する。")
        群[0]["資料作用"]["版"] = "HDS原資料作用-v6"
        with self.assertRaises(ValueError): _束を検査(群)

    def test_限定の作用説明と旧サ変の作用説明を実読解へ対応させる(self):
        for 本文 in (*二題材, "会員が資料だけを使える。"):
            with self.subTest(本文=本文):
                群 = 人工記載(本文)
                for 行 in 群:
                    self.assertIn("局所限定", 行["資料作用"]["意味作用"]["変換"])
                _束を検査(群)
        群 = 人工記載("送信班は文書を送信する。")
        self.assertEqual(群[0]["資料作用"]["意味作用"]["変換"], "明示格と終止サ変の有限読解")
        _束を検査(群)

