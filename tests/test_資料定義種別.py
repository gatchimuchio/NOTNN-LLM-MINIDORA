"""一般連体形と名詞主要部を、回答の種類・全文・区間へ結ぶ有限対照。"""
from copy import deepcopy
import unittest

from minidora.HDS運用.資料回答 import _種別を読む, 記載関係を読む, 資料回答版
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import _文章, 資料文章を照合, 資料文章を検査
from minidora.製品版.型 import 能力結果


def 定義要求(対象):
    return {"版": "HDS一般会話要求-v2", "対象": [], "主題": [対象], "操作": ["説明"],
            "形式": "文章", "範囲": "自動", "最大文字数": 24000, "問い": 対象 + "の定義",
            "比較対象": [], "観点": [], "詳細": "標準", "提示本文": "",
            "関係焦点": ["定義"], "肯否": "未指定"}


class 資料定義種別試験(unittest.TestCase):
    def test_一送り仮名の動詞と形容詞を名詞主要部へ結ぶ(self):
        for 文, 修飾, 種別 in (("紙を折る器具", "紙を折る", "器具"),
                               ("金属を削る機械", "金属を削る", "機械"),
                               ("人の姿を描く作品", "人の姿を描く", "作品"),
                               ("香りの強い飲料", "香りの強い", "飲料")):
            with self.subTest(文=文):
                読み = _種別を読む(文)
                self.assertEqual((読み["修飾"], 読み["種別"]), (修飾, 種別))
                証拠 = 読み["連体型証拠"]
                self.assertEqual(文[slice(*証拠["主要部範囲"])], 種別)
                self.assertEqual("".join(項["表層"] for 項 in 証拠["字句"]), 文)

    def test_単独性質と連用形を概念種別へ変えない(self):
        for 文 in ("青い", "安全", "紙を折り器具", "人の姿を描き作品"):
            with self.subTest(文=文):
                self.assertIsNone(_種別を読む(文))

    def test_未知修飾は新しい字句連体読解へ昇格しない(self):
        self.assertIsNone(_種別を読む("フナリを折る器具"))

    def test_別段落の同じ明示対象の具体定義を所属だけへ縮めない(self):
        本文 = "検査機は機械の一つである。\n\n検査機は紙を折る器具である。"
        構造 = 資料意味を選ぶ({"人工資料": 能力結果(True, 本文)}, 定義要求("検査機"))
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertIn("機械の一つ", 成果.本文)
        self.assertIn("紙を折る器具", 成果.本文)
        self.assertNotIn("種別・所属関係です", 成果.本文)
        self.assertTrue(資料文章を検査(成果))
        記載 = 記載関係を読む(構造)
        行 = next(行 for 行 in 記載 if "紙を折る" in 行["対応"]["原文"])
        self.assertIsNotNone(行["関係"]["定義"])
        self.assertEqual(本文[行["対応"]["開始"]:行["対応"]["終了"]], 行["対応"]["原文"])

    def test_意味保存版と修飾証拠の改変を再生成で拒否する(self):
        本文 = "記録具は金属を削る機械である。"
        構造 = 資料意味を選ぶ({"人工資料": 能力結果(True, 本文)}, 定義要求("記録具"))
        成果 = 資料文章を照合(構造, _文章(構造))
        self.assertEqual(資料回答版, "HDS資料回答内容-v21")
        for 旧版 in ("HDS資料回答内容-v19", "HDS資料回答内容-v20"):
            旧 = deepcopy(成果)
            旧.データ["意味成果"]["版"] = 旧版
            self.assertFalse(資料文章を検査(旧))
        for 旧版 in ("HDS資料回答内容-v7", "HDS資料回答内容-v8", "HDS資料回答内容-v9", "HDS資料回答内容-v10", "HDS資料回答内容-v11", "HDS資料回答内容-v12", "HDS資料回答内容-v13", "HDS資料回答内容-v14", "HDS資料回答内容-v15", "HDS資料回答内容-v16"):
            旧 = deepcopy(成果)
            旧.データ["意味成果"]["版"] = 旧版
            self.assertFalse(資料文章を検査(旧))
        改変 = deepcopy(成果)
        行 = next(行 for 行 in 改変.データ["意味成果"]["記載関係"] if 行["関係"]["定義"])
        行["関係"]["定義"]["連体型証拠"]["主要部範囲"][0] += 1
        self.assertFalse(資料文章を検査(改変))


if __name__ == "__main__":
    unittest.main()
