from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.hds介入制御 import HDS指令, HDS指令種別, 標準HDS介入制御
from minidora.hds監督選択runtime import HDS監督選択実行
from minidora.参照 import 参照記録
from minidora.能力状態差循環 import 標準能力模型核


def qir() -> HDSIR:
    return HDSIR(
        原文="Q",
        正規化文="Q",
        認知世界ID="q",
        座標=(
            HDS座標("choice:A", "choice", "alpha"),
            HDS座標("choice:B", "choice", "beta"),
        ),
        関係=(),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        手順=None,
        入力言語="en",
    )


def result(status="SUSPEND", label=None, reasons=(), proof=0):
    k3 = SimpleNamespace(根拠事実数=proof) if proof else None
    return HDS選択実行結果(
        状態=status,
        回答ラベル=label,
        回答内容={"A": "alpha", "B": "beta"}.get(label),
        理由=tuple(reasons),
        K3結果=k3,
        候補コンパイル数=2,
        Dataコンパイル数=0,
        Dataコンパイル失敗数=0,
        K追加事実数=0,
        K証拠事実数=proof,
        K証拠阻害事実数=0,
    )


class _StopControl:
    def 判定(self, _観測):
        return HDS指令(HDS指令種別.停止要求, 理由=("TEST_STOP",))


class _計算Compiler:
    def 計算コンパイル(self, _text):
        return SimpleNamespace(
            参照必須=False,
            計算IR=SimpleNamespace(名称="generic", 版="v1", 命令列=(object(),)),
            初期状態={"x": 1},
        )


class _CompileOwner:
    def __init__(self):
        self.HDSコンパイラ = _計算Compiler()

    def コンパイル(self, _text):
        return qir()


class _計算実行器:
    def 計算実行(self, _ir, _state):
        return SimpleNamespace(出力=2)


class SupervisoryChoiceRuntimeTest(unittest.TestCase):
    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_初期APPROVEは完全透過で再評価しない(self, mock_normal):
        initial = result("APPROVE", "A", ("NORMAL_MINIDORA",), proof=2)
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(), 初期選択=initial,
        )
        self.assertIs(out.選択, initial)
        self.assertEqual(out.HDS介入数, 0)
        mock_normal.assert_not_called()

    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_HDSなしはSUSPENDも完全透過(self, mock_normal):
        initial = result("SUSPEND", None, ("AMBIGUOUS_EVIDENCE",))
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=None, 初期選択=initial,
        )
        self.assertIs(out.選択, initial)
        self.assertEqual(out.HDS介入数, 0)
        mock_normal.assert_not_called()

    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_閉包済み計算IRがある時だけ汎用計算を起動して通常MINIDORAへ戻す(self, mock_normal):
        initial = result("SUSPEND", None, ("NO_KNOWLEDGE_EVIDENCE",))
        mock_normal.return_value = result("APPROVE", "B", ("EVIDENCE_PRESENT",), proof=3)
        owner = _CompileOwner()
        out = HDS監督選択実行(
            qir(), (), コンパイル=owner.コンパイル, 基礎能力核=None,
            模型核=標準能力模型核(), 計算実行器_=_計算実行器(),
            HDS制御=標準HDS介入制御(), 初期選択=initial,
        )
        self.assertEqual(out.選択.状態, "APPROVE")
        self.assertEqual(out.選択.回答ラベル, "B")
        self.assertEqual(out.HDS作用, ("EXISTING_COMPUTE_EXECUTOR",))
        self.assertEqual(out.HDS介入数, 1)
        self.assertEqual(mock_normal.call_count, 1)
        self.assertIsNone(mock_normal.call_args.kwargs["基礎能力核"])
        self.assertTrue(mock_normal.call_args.kwargs["正式模型評価"])
        self.assertEqual(out.参照[-1].値, 2)
        self.assertEqual(out.参照[-1].供給器, "MINIDORA計算実行器")
        self.assertIn("HDS_FEEDBACK_SAFETY_VALVE", out.選択.理由)

    @patch("minidora.hds監督選択runtime.HDS追加参照検索")
    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_観測不足時だけ参照を広げて通常MINIDORAを再実行(self, mock_normal, mock_extra):
        initial = result("SUSPEND", None, ("NO_KNOWLEDGE_EVIDENCE",))
        extra = 参照記録("extra", "extra", "evidence", "fixture://extra", "fixture")
        mock_extra.return_value = (extra,)
        mock_normal.return_value = result("APPROVE", "A", ("EVIDENCE_PRESENT",), proof=1)
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=None,
            模型核=標準能力模型核(), 参照供給器=object(),
            HDS制御=標準HDS介入制御(), 初期選択=initial,
        )
        self.assertEqual(out.選択.回答ラベル, "A")
        self.assertEqual(out.HDS作用, ("REFERENCE",))
        self.assertEqual(out.参照, (extra,))
        mock_extra.assert_called_once()
        mock_normal.assert_called_once()

    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_STOPだけなら初期SUSPENDを改変しない(self, mock_normal):
        initial = result("SUSPEND", None, ("AMBIGUOUS_EVIDENCE",))
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=_StopControl(), 初期選択=initial,
        )
        self.assertIs(out.選択, initial)
        self.assertEqual(out.HDS介入数, 0)
        self.assertEqual(out.停止理由, ("TEST_STOP",))
        mock_normal.assert_not_called()

    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_初期選択省略時も通常MINIDORAを一度だけ先に実行(self, mock_normal):
        normal = result("APPROVE", "A", ("NORMAL_MINIDORA",), proof=1)
        mock_normal.return_value = normal
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=None,
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(),
        )
        self.assertIs(out.選択, normal)
        self.assertEqual(out.HDS介入数, 0)
        self.assertEqual(mock_normal.call_count, 1)


if __name__ == "__main__":
    unittest.main()
