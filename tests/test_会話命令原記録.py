"""人工採用原票の所有・原文検査。製品のHDS採用成立を証明する試験ではない。"""
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase

from minidora.HDS運用 import HDS運用セッション
from minidora.HDS運用.解釈 import 依頼を解釈
from minidora.HDS運用.一般依頼 import 一般計画を作る
from minidora.HDS運用.会話文脈 import 会話入力文脈を読む, 命令提示材料を読む
from minidora.HDS運用.値 import 結果を復元, 指紋
from tests.test_会話束最終検証 import 状態を作る, 所有


class 会話命令実庫検査(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.原票, _ = 状態を作る()

    def setUp(self):
        self.値 = deepcopy(self.原票)
        self.会話 = HDS運用セッション(所有)
        self.会話._原記録 = self.会話._原記録.同期候補(
            self.値["運用入力"], None, 結果を復元(self.値["運用応答"]), {})
        self.会話.目録.原記録庫 = self.会話._原記録.庫
        self.会話._前回目的 = deepcopy(self.値["運用解釈"])
        self.会話._前回結果 = deepcopy(self.値["運用応答"])
        self.会話._焦点有効 = True

    def 命令入力(self):
        前 = self.会話._前採用会話を証明()
        歴史 = self.会話._前命令候補を証明(前)
        入力 = {"原文": "再計算してください。", "セッションID": 所有, "資料": {},
              "外部許可": False, "前回目的": self.会話._前回目的,
              "前回結果": self.会話._前回結果, "前回有効": self.会話._有効(),
              "前回依存": {}, "前採用会話": 前, "前命令候補": 歴史,
              "命令提示原文": self.会話._命令提示原文を証明(歴史)}
        return 入力, 依頼を解釈(入力)

    def test_現行成果と歴史命令を別用途で同じ実庫から発行(self):
        前 = self.会話._前採用会話を証明()
        歴史 = self.会話._前命令候補を証明(前)
        self.assertEqual(前["契約包"], 歴史["契約包"])
        self.assertEqual(len(前["文脈証明"][0]), 5)
        self.assertEqual(len(歴史["命令証明"][0]), 8)
        self.assertEqual(歴史["命令証明"][0]["原要求印"], 前["契約包"]["原文印"])

    def test_同所有名でも実庫が空なら保存包を採用証明にしない(self):
        別 = HDS運用セッション(所有)
        別._前回目的 = self.会話._前回目的
        別._前回結果 = self.会話._前回結果
        別._焦点有効 = True
        with self.assertRaises(ValueError):
            別._前採用会話を証明()

    def test_別所有の実庫を接続しても自己証明にしない(self):
        self.会話.ID = "別の人工所有"
        with self.assertRaises(ValueError):
            self.会話._前命令候補を証明()

    def test_失効元は普通参照へ戻さず原要求の歴史を保つ(self):
        前 = self.会話._前採用会話を証明()
        旧ID = 前["文脈証明"][0]["原記録ID"]
        候補 = self.会話._原記録.同期候補(self.値["運用入力"], None,
            結果を復元(self.値["運用応答"]), {}, 失効成果ID=(旧ID,))
        self.assertTrue(self.会話._原記録.庫.原記録(旧ID)["現行"])
        self.会話._原記録 = 候補
        self.会話._焦点有効 = False
        self.assertFalse(候補.庫.原記録(旧ID)["現行"])
        self.assertIsNone(self.会話._前採用会話を証明())
        歴史 = self.会話._前命令候補を証明()
        self.assertEqual(歴史["契約包"], 前["契約包"])

    def test_再実行は現在依頼のまま原要求の提示区分を新材料にする(self):
        入力, 解釈 = self.命令入力()
        self.assertEqual(解釈["原文"], 入力["原文"])
        _, 素材, _ = 一般計画を作る(解釈, 入力)
        for 子 in 素材["一般:子計画"].データ["子計画"]:
            self.assertEqual(子["解釈"]["要求"]["問い"], 入力["原文"])
            self.assertNotIn("前束目的ID", 子["解釈"])
            材料 = 素材[子["素材対応"]["一般:資料:0"]]
            self.assertEqual(材料.本文, "係員は荷札を確認する。")
            self.assertNotEqual(材料.本文, 結果を復元(self.値["運用応答"]).本文)

    def test_原文区分を改変しても最終実庫所有照合で拒否(self):
        入力, 解釈 = self.命令入力()
        状態 = SimpleNamespace(成果=tuple({"運用入力": 入力, "運用解釈": 解釈}.items()))
        self.会話._会話入力所有を検査(状態)
        最初 = next(iter(入力["命令提示原文"].values()))
        最初["原文範囲"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "実採用庫"):
            self.会話._会話入力所有を検査(状態)

    def test_命令原文の自己印改変を拒否(self):
        入力, 解釈 = self.命令入力()
        元ID = 解釈["前命令包"]["目的参照"][0]
        入力["命令提示原文"][元ID]["原要求"] += "無根拠な追記"
        with self.assertRaises(ValueError):
            命令提示材料を読む(解釈["要求"], 元ID, 入力)

    def test_未失効の候補へ存在しない成果を失効指定しない(self):
        前 = 指紋(self.会話._原記録.保存())
        with self.assertRaises((ValueError, KeyError)):
            self.会話._原記録.同期候補(self.値["運用入力"], None,
                結果を復元(self.値["運用応答"]), {}, 失効成果ID=("不存在成果",))
        self.assertEqual(指紋(self.会話._原記録.保存()), 前)

    def test_実用途無しの歴史候補を現在依頼へ付けない(self):
        入力, 解釈 = self.命令入力()
        初包 = self.値["運用解釈"]["要求"]
        文脈 = 会話入力文脈を読む(初包, 入力)
        self.assertIsNone(文脈["前命令包"])
        self.assertIsNotNone(解釈["前命令包"])
