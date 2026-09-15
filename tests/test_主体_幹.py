import unittest

from minidora import (
    ミニドラ,
    主体主幹,
    主体状態,
    主体更新提案,
    要求,
    手順,
    命令,
    作用,
    実行状態,
)


class 主体主幹試験(unittest.TestCase):
    def setUp(self):
        初期 = 主体状態(
            現在目的=("K3基盤を維持する",),
            判断基準=("根拠なく反転しない",),
            立場=(("基盤", "K3"),),
        )
        self.本体 = ミニドラ(主体主幹_=主体主幹(初期))

    def _結果手順(self, value="ok"):
        return 手順("結果形成", (命令("値設定", 作用.設定, 引数=(value,), 更新先="結果"),))

    def test_全処理が同じ主体状態を参照する(self):
        手順_ = 手順("主体参照", (命令("主体取得", 作用.取得, 対象="主体状態", 更新先="結果"),))
        result = self.本体.実行(要求("主体", 手順_))
        self.assertEqual(result.値["立場"], (("基盤", "K3"),))
        self.assertEqual(result.主体状態.版, 0)

    def test_理由なし反転は保留し旧状態を維持(self):
        提案 = 主体更新提案(変更={"立場": {"基盤": "Llama3"}})
        result = self.本体.実行(要求("基盤変更", self._結果手順(), 主体更新提案=提案))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertEqual(result.主体状態.立場, (("基盤", "K3"),))
        self.assertEqual(result.主体状態.版, 0)

    def test_理由付き訂正は履歴を残して更新(self):
        提案 = 主体更新提案(
            変更={"仮説": ("Llama3型主体主幹を内包する",)},
            理由=("Llama3再構文化で自己一貫性機構候補を抽出",),
            根拠=("L3_SELF_CONSISTENCY_HDS_V2_20260821",),
        )
        result = self.本体.実行(要求("仮説更新", self._結果手順(), 主体更新提案=提案))
        self.assertEqual(result.値, "ok")
        self.assertEqual(result.採否.状態, 実行状態.合格)
        self.assertEqual(result.主体状態.版, 1)
        self.assertEqual(result.主体監査履歴[-1].旧版, 0)
        self.assertEqual(result.主体監査履歴[-1].新版, 1)
        self.assertTrue(result.主体監査履歴[-1].理由)

    def test_Layer0内部からの無言変更も主体主幹を迂回できない(self):
        提案 = {"変更": {"判断基準": ("都度変更",)}, "理由": (), "根拠": ()}
        手順_ = 手順("迂回試行", (
            命令("結果設定", 作用.設定, 引数=("通して",), 更新先="結果"),
            命令("主体更新注入", 作用.設定, 引数=(提案,), 更新先="主体更新提案"),
        ))
        result = self.本体.実行(要求("迂回", 手順_))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertEqual(result.主体状態.判断基準, ("根拠なく反転しない",))

    def test_主体IDは処理経路から変更不能(self):
        提案 = 主体更新提案(変更={"主体ID": "OTHER"}, 理由=("変更したい",))
        result = self.本体.実行(要求("主体交換", self._結果手順(), 主体更新提案=提案))
        self.assertEqual(result.採否.状態, 実行状態.失敗)
        self.assertEqual(result.主体状態.主体ID, "MINIDORA")

    def test_主体状態はturnを跨いで持続(self):
        update = 主体更新提案(
            変更={"選好": {"応答言語": "日本語"}},
            理由=("日本語基底契約",),
            根拠=("AGENTS.md",),
        )
        self.本体.実行(要求("設定", self._結果手順(), 主体更新提案=update))
        手順_ = 手順("主体参照", (命令("主体取得", 作用.取得, 対象="主体状態", 更新先="結果"),))
        result = self.本体.実行(要求("次turn", 手順_))
        self.assertEqual(result.値["選好"], (("応答言語", "日本語"),))
        self.assertEqual(result.主体状態.版, 1)


if __name__ == "__main__":
    unittest.main()
