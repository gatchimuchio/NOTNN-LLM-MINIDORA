"""当回一般構文の人工有限。初見実測・世界事実・回答採否ではない。"""
from unittest import TestCase, main
from dataclasses import replace
from copy import deepcopy
import hashlib
import json
from minidora.HDS中間表現 import HDSIR, HDS座標, HDS残差, HDS実行核
from minidora.HDS会話文節 import HDS会話文節を形成
from minidora.HDS会話契約 import 会話契約を形成, 会話契約を検査, 会話射影由来
from minidora.HDS運用.会話目的束 import 会話目的を読む


def _基礎(文):
    return HDSIR(文, 文, "人工一般構文", (HDS座標("元座標", "世界.人工", {"保持": "原物"}),), (),
                 (HDS残差("元残差", "別領域未観測", "原材料", "元残差を保持"),), (), HDS実行核())


def _形成(文):
    元 = _基礎(文)
    ir = HDS会話文節を形成(元)
    if ir is None: raise AssertionError("新一般構文が未形成です")
    if ir.座標[0] != 元.座標[0] or ir.残差[0] != 元.残差[0]: raise AssertionError("元IRの変更")
    包 = 会話契約を形成(ir, 所有セッション="人工一般所有")
    会話契約を検査(包, 所有セッション="人工一般所有", 意味IR=ir)
    return ir, 包


def _読む(文):
    ir, 包 = _形成(文)
    return ir, 包, 会話目的を読む(包, 所有セッション="人工一般所有", 意味IR=ir)


class 一般構文同発話有限(TestCase):
    def test_S1_比較対象と観点の原格を分ける(self):
        文 = "「符号甲」と「符号乙」は、情報の保存方法がどう違う？"
        ir, _, 行 = _読む(文)
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["比較対象"], ["符号甲", "符号乙"])
        self.assertEqual(行[0]["要求"]["観点"], ["情報の保存方法"])
        self.assertEqual(行[0]["要求"]["操作"], ["対照"])
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))
        for x in ir.座標:
            if x.由来 == 会話射影由来 and x.原文範囲 is not None:
                self.assertEqual(x.内容["原文"], 文[slice(*x.原文範囲)])

    def test_S2_同発話二観点と連体主要部を比較へ結ぶ(self):
        文 = "「手順甲」と「手順乙」はどこが違う？開始する時点と作業の重なり方を比べて。"
        ir, _, 行 = _読む(文)
        self.assertEqual(len(行), 1)
        self.assertEqual(行[0]["要求"]["比較対象"], ["手順甲", "手順乙"])
        self.assertEqual(行[0]["要求"]["観点"], ["開始する時点", "作業の重なり方"])
        条件 = [x for x in ir.座標 if x.種別 == "条件.会話適用" and x.内容["値"]["役割"] == "同発話対応"]
        self.assertEqual(条件[0].内容["値"]["値"]["方式"], "比較観点補足")
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))

    def test_S4_読点可能述部は問いとして保持する(self):
        文 = "「装置甲」は、なぜ熱を逃がせるの？"
        ir, _, 行 = _読む(文)
        self.assertEqual(行[0]["要求"]["主題"], ["装置甲"])
        self.assertEqual(行[0]["要求"]["操作"], ["理由"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["熱を逃がせる"])
        self.assertFalse(any(x.種別.startswith("世界.") and x.由来 == 会話射影由来 for x in ir.座標))


class 一般必須役割有限(TestCase):
    def test_比較観点での原格(self):
        文 = "「方式甲」と「方式乙」は、運搬の速さでどう違いますか？"
        ir, _, 行 = _読む(文)
        self.assertEqual(行[0]["要求"]["比較対象"], ["方式甲", "方式乙"])
        self.assertEqual(行[0]["要求"]["観点"], ["運搬の速さ"])
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))

    def test_比較の連体二観点での同発話(self):
        文 = "「運送甲」と「運送乙」はどう違う？運ぶ荷物の重さと運ぶ距離の長さで比べて。"
        ir, _, 行 = _読む(文)
        self.assertEqual(行[0]["要求"]["比較対象"], ["運送甲", "運送乙"])
        self.assertEqual(行[0]["要求"]["観点"], ["運ぶ荷物の重さ", "運ぶ距離の長さ"])
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))

    def test_定義関係内部目的の三必須役割(self):
        文 = "運搬器とは何ですか？測定器との関係と、運搬器が材料を運ぶ目的も含めて説明して。"
        ir, _, 行 = _読む(文)
        self.assertEqual(len(行), 3)
        self.assertEqual(行[0]["要求"]["関係焦点"], ["定義"])
        関係 = 行[1]["要求"]["関係要求"][0]
        self.assertEqual([x["値"] for x in 関係["両端"]], ["運搬器", "測定器"])
        目的 = 行[2]["要求"]["動作目的要求"][0]
        self.assertEqual(目的["主体"]["値"], "運搬器")
        self.assertEqual(目的["対象物"]["値"], "材料")
        self.assertEqual(目的["原述部"]["原文"], "運ぶ")
        self.assertEqual(目的["主要部"]["値"], "目的")
        self.assertEqual(行[2]["要求"]["関係焦点"], ["運搬器が材料を運ぶ目的"])
        self.assertTrue(all(x["要求"]["操作"] == ["説明"] for x in 行))
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))
        self.assertFalse(any(x.種別.startswith("世界.") and x.由来 == 会話射影由来 for x in ir.座標))

    def test_内部目的の省略主体を補完しない(self):
        文 = "運搬器とは何か、材料を運ぶ目的も含めて説明して。"
        _, _, 行 = _読む(文)
        目的 = 行[1]["要求"]["動作目的要求"][0]
        self.assertIsNone(目的["主体"])
        self.assertEqual(目的["対象物"]["値"], "材料")
        self.assertEqual(行[1]["要求"]["操作"], ["説明"])

    def test_包含された比較を定義から分離する(self):
        文 = "運搬器とは何ですか？測定器との構造の違いも含めて説明して。"
        ir, _, 行 = _読む(文)
        self.assertEqual(len(行), 2)
        self.assertEqual(行[0]["要求"]["主題"], ["運搬器"])
        self.assertEqual(行[0]["要求"]["関係焦点"], ["定義"])
        self.assertEqual(行[1]["要求"]["操作"], ["対照"])
        self.assertEqual(行[1]["要求"]["比較対象"], ["運搬器", "測定器"])
        self.assertEqual(行[1]["要求"]["観点"], ["構造"])
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))

    def test_独立二端関係を連結一主題にしない(self):
        文 = "運搬器と測定器の関係を説明して。"
        _, _, 行 = _読む(文)
        self.assertEqual(行[0]["要求"]["主題"], ["運搬器", "測定器"])
        self.assertEqual(行[0]["要求"]["版"], "HDS一般会話要求-v3")
        関係 = 行[0]["要求"]["関係要求"][0]
        self.assertEqual([x["値"] for x in 関係["両端"]], ["運搬器", "測定器"])
        self.assertEqual(関係["焦点"]["値"], "関係")
        self.assertEqual(関係["原発話"], 文)

    def test_理由参照の関係限定は元WHYと関係子だけ(self):
        文 = "運搬器はなぜ動くの？その理由を、測定器との関係で説明して。材料を要約して。"
        ir, _, 行 = _読む(文)
        self.assertEqual(len(行), 3)
        元, 関係子, 別 = [x["要求"] for x in 行]
        self.assertEqual(元["操作"], ["理由"])
        self.assertEqual(元["関係焦点"], ["動く"])
        self.assertEqual(元["観点"], ["測定器"])
        self.assertEqual(元["関係要求"], 関係子["関係要求"])
        self.assertEqual(別["操作"], ["要約"])
        self.assertEqual(別["観点"], [])
        self.assertNotIn("関係要求", 別)
        self.assertFalse(any(x.種別 == "会話未消費" for x in ir.残差))

    def test_同発話関係もをWHYの必須範囲へ渡す(self):
        文 = "運搬器はなぜ動くの？測定器との関係も教えて。"
        _, _, 行 = _読む(文)
        self.assertEqual(len(行), 2)
        self.assertEqual(行[0]["要求"]["関係要求"], 行[1]["要求"]["関係要求"])
        self.assertEqual(行[0]["要求"]["観点"], ["測定器"])

    def test_競合する当回目的へ補足を推測適用しない(self):
        for 文 in ("「甲」と「乙」はどう違う？「丙」と「丁」はどう違う？運ぶ距離で比べて。",
                  "運搬器はなぜ動くの？測定器はなぜ動くの？その理由を、材料との関係で説明して。",
                  "運搬器と測定器とは何ですか？加工器との関係も含めて説明して。"):
            with self.subTest(文=文):
                ir, 包 = _形成(文)
                if 文.startswith("運搬器と測定器とは"):
                    self.assertEqual([x.内容["値"] for x in ir.座標 if x.種別 == "対象.会話主題"
                                      and x.原文範囲 is not None and x.原文範囲[1] < 文.index("？")],
                                     ["運搬器", "測定器"])
                self.assertTrue(any(x.種別 == "会話未消費" for x in ir.残差))
                self.assertFalse(any(x.種別 == "条件.会話適用" and x.内容["値"]["役割"] == "同発話対応" for x in ir.座標))
                with self.assertRaises(ValueError): 会話目的を読む(包, 所有セッション="人工一般所有", 意味IR=ir)

    def test_未知動作と条件否定数量を未消費に保持(self):
        for 文 in ("運搬器とは何か、材料をフナリする目的も含めて説明して。",
                  "運搬器は、点検が終わると、なぜ材料を運べないの？",
                  "運搬器とは何か、測定器との関係も含めて二文で説明して。"):
            with self.subTest(文=文):
                ir, 包 = _形成(文)
                self.assertTrue(any(x.種別 == "会話未消費" for x in ir.残差))
                with self.assertRaises(ValueError): 会話目的を読む(包, 所有セッション="人工一般所有", 意味IR=ir)

    def test_関係三端は二端へ切断しない(self):
        ir, 包 = _形成("運搬器と測定器と加工器はどのような関係にある？")
        self.assertTrue(any(x.種別 == "会話未消費" for x in ir.残差))
        self.assertFalse(any(x.種別 == "条件.会話適用" and x.内容["値"]["役割"] == "関係要求" for x in ir.座標))
        with self.assertRaises(ValueError): 会話目的を読む(包, 所有セッション="人工一般所有", 意味IR=ir)

    def test_新原役割の原範囲と主体改変を拒否する(self):
        from minidora.HDS運用.一般依頼 import 一般要求を検査
        文 = "運搬器とは何か、運搬器が材料を運ぶ目的も含めて説明して。"
        _, 包, 行 = _読む(文)
        要求 = 行[1]["要求"]
        for 欄, 値 in (("主体", None), ("原述部", {"原文": "運ぶ", "原文範囲": None}),
                      ("対象物", {"値": "材料", "原文範囲": [True, 1]})):
            with self.subTest(欄=欄):
                改 = deepcopy(要求); 改["動作目的要求"][0][欄] = 値
                with self.assertRaises(ValueError): 一般要求を検査(改)
        from minidora.HDS会話契約 import _原動作目的の原役割を検査
        未知 = "材料をフナリする目的"
        内 = {"原語句": {"原文": 未知, "原文範囲": [0, len(未知)]}, "主体": None,
              "対象物": {"値": "材料", "原文範囲": [0, 2]},
              "原述部": {"原文": "フナリする", "原文範囲": [3, len(未知) - 2]},
              "主要部": {"値": "目的", "原文範囲": [len(未知) - 2, len(未知)]}}
        with self.assertRaises(ValueError): _原動作目的の原役割を検査(内, 未知)
        証 = json.loads(包["証明正準JSON"])
        条件 = next(x for x in 証["座標"] if x["種別"] == "条件.会話適用" and x["内容"]["値"]["役割"] == "動作目的要求")
        条件["内容"]["値"]["値"]["主体"] = None
        改 = deepcopy(包); 改["証明正準JSON"] = json.dumps(証, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        改["意味束印"] = hashlib.sha256(改["証明正準JSON"].encode()).hexdigest()
        with self.assertRaises(ValueError): 会話契約を検査(改, 所有セッション="人工一般所有")

    def test_旧要求欄と新必須欄を無言変換しない(self):
        from minidora.HDS運用.一般依頼 import 一般要求を検査
        _, _, 行 = _読む("運搬器と測定器の関係を説明して。")
        要求 = 行[0]["要求"]
        for 操作 in ("旧版", "欠落", "空型", "端点改変"):
            with self.subTest(操作=操作):
                改 = deepcopy(要求)
                if 操作 == "旧版": 改["版"] = "HDS一般会話要求-v2"
                elif 操作 == "欠落": del 改["動作目的要求"]
                elif 操作 == "空型": 改["関係要求"] = []
                else: 改["関係要求"][0]["両端"][1] = deepcopy(改["関係要求"][0]["両端"][0])
                with self.assertRaises(ValueError): 一般要求を検査(改)
        self.assertEqual(一般要求を検査(要求), 要求)

    def test_原発話全文と検索限定を計画で保持(self):
        from minidora.HDS運用.一般依頼 import 一般計画を作る
        文 = "運搬器はなぜ動くの？測定器との関係も説明して。"
        _, _, 行 = _読む(文)
        要求 = 行[0]["要求"]
        入力 = {"原文": 文, "資料": {}, "外部許可": True}
        _, 素材, _ = 一般計画を作る({"方式": "一般資料", "要求": 要求}, 入力)
        設定 = 素材["一般:取得設定:0"].データ
        self.assertEqual(設定["必要語"], ["運搬器"])
        self.assertIn("測定器", 設定["検索語"])
        self.assertEqual(設定["最大検索回数"], 2)
        self.assertEqual(設定["最大取得数"], 6)
        self.assertEqual(素材["一般:要求"].データ, 要求)
        with self.assertRaises(ValueError): 一般計画を作る({"方式": "一般資料", "要求": 要求}, {**入力, "原文": 文 + "別原文"})
        with self.assertRaises(ValueError): 一般計画を作る({"方式": "一般資料", "要求": 要求}, {**入力, "外部許可": False})


if __name__ == "__main__": main()
