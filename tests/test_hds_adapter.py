import unittest

from minidora import (
    HDSIR,
    HDS実行核,
    HDS座標,
    HDS残差,
    ミニドラ,
    要求,
    手順,
    命令,
    作用,
    参照記録,
    固定参照供給器,
    参照矛盾数,
    実行状態,
)


def _加算IR(入力, 左, 右):
    proc = 手順(
        "fixture:HDS-IR加算",
        (命令("加算", 作用.加算, 引数=("$a", "$b"), 更新先="結果", 根拠=("fixture:HDS-IR",)),),
        由来="fixture compiler",
    )
    return HDSIR(
        原文=入力,
        正規化文=入力,
        認知世界ID="fixture:world",
        座標=(
            HDS座標("a", "対象.現在状態", 左),
            HDS座標("b", "対象.現在状態", 右),
            HDS座標("action", "手段.作用", "加算"),
            HDS座標("result", "目的.到達状態", "加算結果"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("加算", ("a", "b"), "結果"),
        初期状態={"a": 左, "b": 右},
        参照必須=False,
        種別="fixture",
        閉包状態="CLOSED_FOR_OPERATION",
        表現状態="MEANING_PRESERVED",
        手順=proc,
    )


class FixtureCompiler:
    def コンパイル(self, 入力, *, 前回結果=None, HDS履歴=()):
        if "続き" in 入力:
            return _加算IR(入力, 前回結果, 4)
        return _加算IR(入力, 2, 3)


class 未閉包Compiler:
    def コンパイル(self, 入力, *, 前回結果=None, HDS履歴=()):
        return HDSIR(
            原文=入力,
            正規化文=入力,
            認知世界ID="fixture:open",
            座標=(HDS座標("target", "対象.実体", 入力),),
            関係=(),
            残差=(
                HDS残差(
                    "res:0",
                    "semantic_loss",
                    入力,
                    "意味が実行可能な形まで閉包していない",
                ),
            ),
            意味作用履歴=(),
            実行核=HDS実行核(),
            初期状態={},
            参照必須=False,
            種別="未閉包",
            手順=None,
        )


class HDSAdapter試験(unittest.TestCase):
    def test_外部HDSコンパイラのIRをそのまま実行する(self):
        body = ミニドラ(HDSコンパイラ_=FixtureCompiler())
        result = body.実行(要求("表層表現はfixtureでは解釈しない"))
        self.assertEqual(result.値, 5)
        self.assertEqual(result.採否.状態, 実行状態.合格)
        self.assertIsNotNone(result.HDS_IR)
        self.assertEqual(result.言語計画, "fixture")

    def test_HDS時間文脈をCompilerへ帰還する(self):
        body = ミニドラ(HDSコンパイラ_=FixtureCompiler())
        self.assertEqual(body.応答("最初"), "5です。")
        self.assertEqual(body.応答("続き"), "9です。")
        self.assertEqual(len(body.HDS履歴), 2)

    def test_未閉包HDS_IRは推測せず保留する(self):
        body = ミニドラ(HDSコンパイラ_=未閉包Compiler())
        result = body.実行(要求("意味未確定"))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIn("HDS_IR未閉包", result.採否.理由)
        self.assertEqual(len(body.HDS履歴), 1)

    def test_意味同一性が確定したDataだけを競合判定する(self):
        records = (
            参照記録(
                "a", "東京", "人口資料A", "fixture://a", "固定",
                意味キー="人口", 値=1400, 時点="2026", 範囲="東京都", 意味確定=True,
            ),
            参照記録(
                "b", "東京", "人口資料B", "fixture://b", "固定",
                意味キー="人口", 値=1300, 時点="2026", 範囲="東京都", 意味確定=True,
            ),
        )
        self.assertEqual(参照矛盾数(records), 1)

    def test_意味未確定Dataを勝手に矛盾認定しない(self):
        records = (
            参照記録("a", "東京", "人口資料A", "fixture://a", "固定", 意味キー="人口", 値=1400),
            参照記録("b", "東京", "人口資料B", "fixture://b", "固定", 意味キー="人口", 値=1300),
        )
        self.assertEqual(参照矛盾数(records), 0)

    def test_Runtimeも意味確定競合を保留する(self):
        provider = 固定参照供給器((
            参照記録(
                "a", "東京", "人口資料A", "fixture://a", "固定",
                意味キー="人口", 値=1400, 時点="2026", 範囲="東京都", 意味確定=True,
            ),
            参照記録(
                "b", "東京", "人口資料B", "fixture://b", "固定",
                意味キー="人口", 値=1300, 時点="2026", 範囲="東京都", 意味確定=True,
            ),
        ))
        result = ミニドラ(provider).実行(要求("東京 人口"))
        self.assertIsNone(result.値)
        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIn("未解消矛盾", result.採否.理由)


if __name__ == "__main__":
    unittest.main()
