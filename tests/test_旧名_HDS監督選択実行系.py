from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from minidora.HDS選択実行系 import HDS選択実行結果
from minidora.HDS中間表現 import HDSIR, HDS実行核, HDS座標
from minidora.hds介入制御 import HDS指令, HDS指令種別, 標準HDS介入制御
from minidora.HDS監督選択実行系 import HDS監督選択実行
from minidora.参照 import 参照記録
from minidora.能力状態差循環 import 標準能力模型核


def 質問中間表現() -> HDSIR:
    return HDSIR(
        原文="Q",
        正規化文="Q",
        認知世界ID="q",
        座標=(
            HDS座標('選択肢:A', '選択肢', "alpha"),
            HDS座標('選択肢:B', '選択肢', "beta"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        手順=None,
        入力言語="en",
    )


def 選択結果(状態="SUSPEND", ラベル=None, 理由群=(), 証拠数=0):
    k3 = SimpleNamespace(根拠事実数=証拠数) if 証拠数 else None
    return HDS選択実行結果(
        状態=状態,
        回答ラベル=ラベル,
        回答内容={"A": "alpha", "B": "beta"}.get(ラベル),
        理由=tuple(理由群),
        K3結果=k3,
        候補コンパイル数=2,
        資料コンパイル数=0,
        資料コンパイル失敗数=0,
        K追加事実数=0,
        K証拠事実数=証拠数,
        K証拠阻害事実数=0,
    )


class _停止制御:
    def 判定(self, _観測):
        return HDS指令(HDS指令種別.停止要求, 理由=("TEST_STOP",))


class _計算構文化器:
    def 計算コンパイル(self, _本文):
        return SimpleNamespace(
            参照必須=False,
            計算IR=SimpleNamespace(名称="generic", 版="v1", 命令列=(object(),)),
            初期状態={"x": 1},
        )


class _構文化保有者:
    def __init__(self):
        self.HDSコンパイラ = _計算構文化器()

    def コンパイル(self, _本文):
        return 質問中間表現()


class _計算実行器:
    def 計算実行(self, _中間表現, _状態):
        return SimpleNamespace(出力=2)


class HDS監督選択実行系試験(unittest.TestCase):
    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_初期APPROVEは完全透過で再評価しない(self, 模擬通常):
        初期 = 選択結果("APPROVE", "A", ("NORMAL_MINIDORA",), 証拠数=2)
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=lambda x: 質問中間表現(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(), 初期選択=初期,
        )
        self.assertIs(出力.選択, 初期)
        self.assertEqual(出力.HDS介入数, 0)
        模擬通常.assert_not_called()

    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_HDSなしはSUSPENDも完全透過(self, 模擬通常):
        初期 = 選択結果("SUSPEND", None, ('AMBIGUOUS_証拠',))
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=lambda x: 質問中間表現(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=None, 初期選択=初期,
        )
        self.assertIs(出力.選択, 初期)
        self.assertEqual(出力.HDS介入数, 0)
        模擬通常.assert_not_called()

    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_閉包済み計算IRがある時だけ汎用計算を起動して通常MINIDORAへ戻す(self, 模擬通常):
        初期 = 選択結果("SUSPEND", None, ('NO_KNOWLEDGE_証拠',))
        模擬通常.return_value = 選択結果("APPROVE", "B", ('証拠_PRESENT',), 証拠数=3)
        保有者 = _構文化保有者()
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=保有者.コンパイル, 基礎能力核=None,
            模型核=標準能力模型核(), 計算実行器_=_計算実行器(),
            HDS制御=標準HDS介入制御(), 初期選択=初期,
        )
        self.assertEqual(出力.選択.状態, "APPROVE")
        self.assertEqual(出力.選択.回答ラベル, "B")
        self.assertEqual(出力.HDS作用, ("EXISTING_COMPUTE_EXECUTOR",))
        self.assertEqual(出力.HDS介入数, 1)
        self.assertEqual(模擬通常.call_count, 1)
        self.assertIsNone(模擬通常.call_args.kwargs["基礎能力核"])
        self.assertTrue(模擬通常.call_args.kwargs["正式模型評価"])
        self.assertEqual(出力.参照[-1].値, 2)
        self.assertEqual(出力.参照[-1].供給器, "MINIDORA計算実行器")
        self.assertIn("HDS_SUPERVISORY_INTERVENTION", 出力.選択.理由)

    @patch("minidora.HDS監督選択実行系.HDS追加参照検索")
    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_観測不足時だけ参照を広げて通常MINIDORAを再実行(self, 模擬通常, 模擬追加):
        初期 = 選択結果("SUSPEND", None, ('NO_KNOWLEDGE_証拠',))
        追加 = 参照記録("extra", "extra", '証拠', "fixture://extra", "fixture")
        模擬追加.return_value = (追加,)
        模擬通常.return_value = 選択結果("APPROVE", "A", ('証拠_PRESENT',), 証拠数=1)
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=lambda x: 質問中間表現(), 基礎能力核=None,
            模型核=標準能力模型核(), 参照供給器=object(),
            HDS制御=標準HDS介入制御(), 初期選択=初期,
        )
        self.assertEqual(出力.選択.回答ラベル, "A")
        self.assertEqual(出力.HDS作用, ('参照',))
        self.assertEqual(出力.参照, (追加,))
        模擬追加.assert_called_once()
        模擬通常.assert_called_once()

    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_STOPだけなら初期SUSPENDを改変しない(self, 模擬通常):
        初期 = 選択結果("SUSPEND", None, ('AMBIGUOUS_証拠',))
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=lambda x: 質問中間表現(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=_停止制御(), 初期選択=初期,
        )
        self.assertIs(出力.選択, 初期)
        self.assertEqual(出力.HDS介入数, 0)
        self.assertEqual(出力.停止理由, ("TEST_STOP",))
        模擬通常.assert_not_called()

    @patch("minidora.HDS監督選択実行系.HDS選択推論実行")
    def test_初期選択省略時も通常MINIDORAを一度だけ先に実行(self, 模擬通常):
        通常 = 選択結果("APPROVE", "A", ("NORMAL_MINIDORA",), 証拠数=1)
        模擬通常.return_value = 通常
        出力 = HDS監督選択実行(
            質問中間表現(), (), コンパイル=lambda x: 質問中間表現(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(),
        )
        self.assertIs(出力.選択, 通常)
        self.assertEqual(出力.HDS介入数, 0)
        self.assertEqual(模擬通常.call_count, 1)


if __name__ == "__main__":
    unittest.main()
