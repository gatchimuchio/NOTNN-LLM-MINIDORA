"""実Compilerと人工工程原票の局所照合。実採用・外部知識評価ではない。"""
from copy import deepcopy
from unittest import TestCase, main
from unittest.mock import patch

from minidora.HDS実行主体 import HDS実行状態
from minidora.HDS運用.能力 import 運用能力目録
from minidora.HDS運用.構文化接続 import 運用構文化器
from minidora.HDS運用.解釈 import 構造を保存
from minidora.HDS運用.一般依頼 import 一般依頼を読む, 一般計画を作る
from minidora.HDS運用.工程 import 工程供給, 入力依存を収集, _会話束HDS対応を検査
from minidora.HDS運用.会話目的束 import 会話目的を読む
from minidora.HDS運用.意味資料 import 資料意味を選ぶ
from minidora.HDS運用.内容構成 import _文章, 資料文章を照合
from minidora.HDS運用.会話回答束 import 会話束内容仕様を構成, 会話束回答を照合
from minidora.HDS運用.値 import 正準, 指紋, 結果を保存, 結果を復元, 計画を保存
from minidora.能力結果復元 import 能力結果を復元
from minidora.文章作成 import 文章を作る, 文章仕様を復元


所有 = "人工最終所有"
原文 = "このメモを一文で説明し、一文で要約してください。\n\n係員は荷札を確認する。"


def 状態を作る():
    入力 = {"セッションID": 所有, "原文": 原文, "資料": {}, "外部許可": False,
           "前回有効": False, "前回結果": None}
    構文化器 = 運用構文化器()
    ir = 構文化器.コンパイル(原文)
    解釈 = 一般依頼を読む(入力, 意味IR=ir)
    解釈["HDS"] = {"全文": 構造を保存(構文化器.原IR)}
    計画, 素材, 種別 = 一般計画を作る(解釈, 入力)
    目録 = 運用能力目録(所有)
    包 = 正準({"方式": "能力計画", "計画": 計画を保存(計画),
              "資料": {名: 結果を保存(値) for 名, 値 in 素材.items()},
              "回答種別": 種別, "外部許可": False, "目録": 目録.ハッシュ,
              "被覆": [], "役割": {}, "禁止": [], "原文": 原文, "解釈": 解釈})
    値 = {"運用入力": 正準(入力), "運用解釈": 正準(解釈), "運用計画:0": 包}
    目的群 = 会話目的を読む(解釈["要求"], 所有セッション=所有)
    子群 = []
    for 目的, 子計画 in zip(目的群, 素材["一般:子計画"].データ["子計画"]):
        対応 = 子計画["素材対応"]
        材料 = 素材[対応["一般:資料:0"]]
        意味 = 資料意味を選ぶ({"提示本文": 材料}, 目的["要求"])
        子 = 資料文章を照合(意味, _文章(意味))
        if not 子.成立:
            raise AssertionError(子.保留理由)
        子群.append({"目的ID": 目的["目的ID"], "成果": 子})
        値["運用計画:0/成果/" + 子計画["出力"]] = 結果を保存(子)
    仕様 = 会話束内容仕様を構成(子群, 解釈["要求"], 所有セッション=所有)
    文章 = 文章を作る({名: 能力結果を復元(値) for 名, 値 in 仕様["素材"].items()},
                   文章仕様を復元(仕様["仕様"]))
    束 = 会話束回答を照合(子群, 解釈["要求"], 文章, 所有セッション=所有)
    値["運用計画:0/成果/一般:束照合"] = 結果を保存(束)
    値["運用応答"] = 結果を保存(束)
    原票を封緘(値, 目録)
    return 値, 目録


def 原票を封緘(値, 目録):
    包 = 値["運用計画:0"]
    出力 = ["運用計画:0/成果/" + 名 for 名 in 包["計画"]["出力工程"]]
    回答 = 結果を復元(値["運用応答"])
    値["運用採用対応"] = {"原文": 値["運用入力"]["原文"], "計画鍵": "運用計画:0",
                       "計画印": 指紋(包), "目録": 目録.ハッシュ, "出力": 出力,
                       "出力印": [指紋(値[名]) for 名 in 出力], "回答印": 指紋(値["運用応答"]),
                       "資料依存": 入力依存を収集(包, 値["運用入力"], 回答.参照)}


class 会話束最終検証試験(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.原票, cls.目録 = 状態を作る()

    def setUp(self):
        self.値 = deepcopy(self.原票)
        self.供給 = 工程供給(self.目録)

    def 検査(self):
        return self.供給.最終検証(HDS実行状態(成果=tuple(self.値.items())), None)

    def test_実構文化器原文と子出力と提示根拠の対応は成立(self):
        self.assertTrue(self.検査())
        self.assertEqual(len(self.値["運用応答"]["内容"]["データ"]["目的成果"]), 2)

    def test_各子の実根拠は既存検査へ戻し拒否を伝播する(self):
        with patch.object(self.供給, "_会話根拠を検証", wraps=self.供給._会話根拠を検証) as 読取:
            self.assertTrue(self.検査())
        self.assertEqual(読取.call_count, 2)
        for 呼出 in 読取.call_args_list:
            self.assertIn("一般:束縛", 呼出.args[1]["資料"])
            self.assertEqual(呼出.args[3], "運用計画:0")
        with patch.object(self.供給, "_会話根拠を検証", return_value=False):
            self.assertFalse(self.検査())

    def test_自己整合する包でも実構文化器全文との不一致は拒否(self):
        解釈 = self.値["運用計画:0"]["解釈"]
        解釈["HDS"]["全文"]["認知世界ID"] = "偽装世界"
        self.値["運用解釈"] = deepcopy(解釈)
        原票を封緘(self.値, self.目録)
        self.assertFalse(self.検査())

    def test_計画素材の再封緘改変は拒否(self):
        束 = self.値["運用計画:0"]["資料"]
        名 = next(名 for 名 in 束 if 名.endswith("一般:資料:0"))
        束[名]["内容"]["本文"] = "別の提示材料"
        原票を封緘(self.値, self.目録)
        self.assertFalse(self.検査())

    def test_子計画の再封緘改変は拒否(self):
        self.値["運用計画:0"]["計画"]["工程"][0]["指示参照"] = "一般:束指示"
        原票を封緘(self.値, self.目録)
        self.assertFalse(self.検査())

    def test_保存子が正しくても実子出力欠落や別値は拒否(self):
        子群 = self.値["運用計画:0"]["資料"]["一般:子計画"]["内容"]["データ"]["子計画"]
        名 = "運用計画:0/成果/" + 子群[0]["出力"]
        for 別 in (None, self.値["運用計画:0/成果/" + 子群[1]["出力"]]):
            with self.subTest(欠落=別 is None):
                self.値 = deepcopy(self.原票)
                if 別 is None:
                    del self.値[名]
                else:
                    self.値[名] = deepcopy(別)
                self.assertFalse(self.検査())

    def test_別所有や別原文を再封緘しても拒否(self):
        for 欄, 内容 in (("セッションID", "別所有"), ("原文", "この結果を確認して")):
            with self.subTest(欄=欄):
                self.値 = deepcopy(self.原票)
                self.値["運用入力"][欄] = 内容
                原票を封緘(self.値, self.目録)
                self.assertFalse(self.検査())

    def test_実解釈と別の保存全文への差替えを拒否(self):
        self.値["運用計画:0"]["解釈"]["HDS"]["全文"]["正規化文"] = "別の解釈"
        原票を封緘(self.値, self.目録)
        self.assertFalse(self.検査())

    def test_HDS復元時の既定型変換余剰と手順は受理しない(self):
        元 = self.原票["運用解釈"]
        for 手続き in (lambda 全文: 全文.pop("参照必須"),
                     lambda 全文: 全文.update(参照必須=0),
                     lambda 全文: 全文.update(未知欄="値"),
                     lambda 全文: 全文.update(手順={"未接続": "原手順"})):
            with self.subTest(手続き=手続き):
                解釈 = deepcopy(元)
                手続き(解釈["HDS"]["全文"])
                with self.assertRaises(ValueError):
                    _会話束HDS対応を検査(解釈, 解釈["要求"], 所有)


if __name__ == "__main__":
    main()
