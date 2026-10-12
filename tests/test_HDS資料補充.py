"""HDSの実不足・再計画・終端照合を人工通信で検査する。正式評価ではない。"""
from copy import deepcopy
from dataclasses import replace
import unittest

from minidora.HDS運用.セッション import HDS運用セッション
from minidora.HDS運用.工程 import 工程供給, 現行計画
from minidora.HDS運用.資料補充 import 資料補充を検査
from minidora.HDS運用.資料回答 import 資料内容不足, 資料内容不足を読む
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import 内容仕様を構成
from minidora.HDS運用.値 import 結果を復元, 指紋
from minidora.知識取得 import 知識取得器, _記録印
from minidora.取得実行制御 import 公開取得上限
from minidora.製品版.型 import 能力結果
from test_知識取得継続 import 人工検索, 人工本文
from test_基本チャット内容 import 要求


def 応答する(本文群=None, 上限=None):
    本文 = 人工本文(本文群)
    検索 = 人工検索(len(本文.本文群))
    会話 = HDS運用セッション("補充", 外部読取許可=True, 手順形成=False,
                     取得器=知識取得器(検索, 本文), 取得上限=上限 or 公開取得上限(最大検索回数=1))
    応答 = 会話.応答("試料甲とは何ですか", 外部読取許可=True)
    return 会話, 検索, 本文, 応答


class HDS資料補充試験(unittest.TestCase):
    def test_内容不足から同じHDSが次本文を読み終端まで照合する(self):
        会話, 検索, 本文, 応答 = 応答する(["試料甲の方式は断熱収納。", "試料甲の素材は樹脂。",
                                "試料甲とは熱の移動を抑える容器である。"])
        self.assertTrue(応答.成立, 応答.本文)
        self.assertIn("熱の移動を抑える容器", 応答.本文)
        self.assertNotIn("999", 応答.本文)
        self.assertEqual(len(検索.回数), 1)
        self.assertEqual(len(本文.回数), 3)
        状態 = 応答.HDS結果.状態
        値 = dict(状態.成果)
        鍵, 包 = 現行計画(状態)
        self.assertEqual(鍵, "運用計画:2")
        self.assertTrue(資料補充を検査(鍵, 包, 値, 会話.目録, 4))
        自己検証 = 工程供給(会話.目録)
        self.assertTrue(自己検証.最終検証(状態, None))
        旧不足 = 結果を復元(値["運用計画:0/試行/一般内容構成/0"]["不成立成果"])
        self.assertFalse(旧不足.成立)
        self.assertEqual(旧不足.データ["診断"]["不足役割"][0]["種別"], "定義・種別関係")
        self.assertEqual(応答.追跡["公開取得資源"]["使用"]["検索回数"], 1)
        self.assertEqual(応答.追跡["公開取得資源"]["使用"]["候補数"], 3)
        # 新packetだけを再封印した候補差替え・不足診断改変も旧実成果から拒否する。
        for 改変 in ("候補", "診断", "対象外", "証明削除", "途中切断", "継続への包み直し"):
            with self.subTest(改変=改変):
                変更 = deepcopy(値)
                if 改変 == "候補":
                    元 = 変更[鍵]["資料"][包["資料補充"]["素材名"]]["内容"]["データ"]
                    元["継続束"]["候補"][1]["URL"] = "https://example.com/changed"
                    元["記録SHA256"] = _記録印({k: v for k, v in 元.items() if k != "記録SHA256"})
                elif 改変 == "診断":
                    変更["運用計画:0/試行/一般内容構成/0"]["不成立成果"]["内容"]["データ"]["診断"]["対象"] = ["別の主題"]
                elif 改変 == "対象外":
                    変更[鍵]["原文"] = "別の問い"
                elif 改変 == "証明削除":
                    del 変更[鍵]["資料補充"]
                elif 改変 == "途中切断":
                    del 変更["運用計画:1"]["資料補充"]
                else:
                    del 変更[鍵]["資料補充"]
                    変更[鍵]["解釈"] = {"方式": "継続", "目的": 変更[鍵]["解釈"]}
                変更["運用採用対応"]["計画印"] = 指紋(変更[鍵])
                with self.assertRaises((ValueError, KeyError)):
                    資料補充を検査(鍵, 変更[鍵], 変更, 会話.目録, 4)
                偽状態 = replace(状態, 成果=tuple(変更.items()))
                self.assertFalse(自己検証.最終検証(偽状態, None))

    def test_意味不足と候補枯渇は保留して採用原本を残さない(self):
        会話, 検索, 本文, 応答 = 応答する(["試料甲の方式は断熱収納。", "試料甲の素材は樹脂。"])
        self.assertEqual(応答.状態, "SUSPEND", 応答.本文)
        self.assertFalse(会話.状態()["前回有効"])
        self.assertEqual(len(検索.回数), 1)
        self.assertEqual(len(本文.回数), 2)
        self.assertNotIn("運用応答", dict(応答.HDS結果.状態.成果))

    def test_共有資源不足では追加取得も採用もしない(self):
        会話, 検索, 本文, 応答 = 応答する(上限=公開取得上限(最大検索回数=1, 最大本文取得数=1))
        self.assertEqual(応答.状態, "SUSPEND", 応答.本文)
        self.assertFalse(会話.状態()["前回有効"])
        self.assertEqual(len(検索.回数), 1)
        self.assertEqual(len(本文.回数), 1)
        self.assertEqual(応答.追跡["公開取得資源"]["使用"]["本文取得数"], 1)

    def test_定義不足の診断を元要求と原作用成果から再導出する(self):
        構造 = 資料意味を選ぶ({"人工資料": 能力結果(True, "試料甲の方式は断熱収納。")},
                    要求(主題=("試料甲",), 関係焦点=("定義",)))
        with self.assertRaises(資料内容不足) as 捕捉:
            内容仕様を構成(構造)
        不足 = 捕捉.exception
        self.assertEqual(資料内容不足を読む(不足.診断, 構造), 不足.診断)
        self.assertEqual(不足.診断["要求"], 構造["要求"])
        self.assertTrue(不足.診断["資料作用成果"])
        偽 = deepcopy(不足.診断)
        偽["必要確認"] = []
        with self.assertRaises(ValueError):
            資料内容不足を読む(偽, 構造)


if __name__ == "__main__":
    unittest.main()
