from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.hds_ir import HDSIR, HDS実行核, HDS座標
from minidora.hds介入制御 import 標準HDS介入制御
from minidora.hds監督選択runtime import HDS監督選択実行
from minidora.k3_functional import K3相当能力核
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


def legacy(status="SUSPEND", label=None, reasons=(), proof=0):
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
        K証拠事実数=0,
        K証拠阻害事実数=0,
    )


def model(status="SUSPEND", label=None, reasons=(), score=0):
    m = SimpleNamespace(
        参照最有力候補ID=label if score > 0 else None,
        参照同率候補ID=(),
        参照候補辞書=lambda: {"A": score if label == "A" else 0, "B": score if label == "B" else 0},
    )
    return HDS選択実行結果(
        状態=status,
        回答ラベル=label,
        回答内容={"A": "alpha", "B": "beta"}.get(label),
        理由=tuple(reasons),
        K3結果=None,
        候補コンパイル数=2,
        Dataコンパイル数=0,
        Dataコンパイル失敗数=0,
        K追加事実数=0,
        K証拠事実数=0,
        K証拠阻害事実数=0,
        MINIDORA模型結果=m,
    )


class SupervisoryChoiceRuntimeTest(unittest.TestCase):
    @patch("minidora.hds監督選択runtime.HDS候補提案実行")
    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_既存能力で閉じればHDS介入ゼロ(self, mock_legacy, mock_model):
        mock_legacy.return_value = legacy("APPROVE", "A", ("EVIDENCE_PRESENT",), proof=2)
        mock_model.return_value = model("SUSPEND", None, ("MINIDORA_OUTPUT_ABSENT",))
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=K3相当能力核(),
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(),
        )
        self.assertEqual(out.選択.状態, "APPROVE")
        self.assertEqual(out.選択.回答ラベル, "A")
        self.assertEqual(out.HDS介入数, 0)
        self.assertIn("NO_FINAL_HDS_JUDGEMENT_WRAPPER", out.選択.理由)

    @patch("minidora.hds監督選択runtime.HDS候補提案実行")
    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_未閉包時だけHDSがworkingを起動する(self, mock_legacy, mock_model):
        mock_legacy.side_effect = [
            legacy("SUSPEND", None, ("AMBIGUOUS_EVIDENCE",)),
            legacy("APPROVE", "B", ("EVIDENCE_PRESENT",), proof=3),
        ]
        mock_model.return_value = model("SUSPEND", None, ("MINIDORA_OUTPUT_ABSENT",))
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=K3相当能力核(),
            模型核=標準能力模型核(), HDS制御=標準HDS介入制御(),
        )
        self.assertEqual(out.選択.状態, "APPROVE")
        self.assertEqual(out.選択.回答ラベル, "B")
        self.assertEqual(out.HDS作用, ("EXISTING_WORKING_RECONCILE",))
        self.assertEqual(out.HDS介入数, 1)
        self.assertEqual(mock_legacy.call_count, 2)
        first = mock_legacy.call_args_list[0].kwargs
        second = mock_legacy.call_args_list[1].kwargs
        self.assertFalse(first["作業再作用"])
        self.assertFalse(first["局所再照合"])
        self.assertTrue(second["作業再作用"])
        self.assertFalse(second["局所再照合"])

    @patch("minidora.hds監督選択runtime.HDS候補提案実行")
    @patch("minidora.hds監督選択runtime.HDS選択推論実行")
    def test_HDSなしでは通常評価だけで終了(self, mock_legacy, mock_model):
        mock_legacy.return_value = legacy("SUSPEND", None, ("AMBIGUOUS_EVIDENCE",))
        mock_model.return_value = model("SUSPEND", None, ("MINIDORA_OUTPUT_ABSENT",))
        out = HDS監督選択実行(
            qir(), (), コンパイル=lambda x: qir(), 基礎能力核=K3相当能力核(),
            模型核=標準能力模型核(), HDS制御=None,
        )
        self.assertEqual(out.選択.状態, "SUSPEND")
        self.assertEqual(out.HDS介入数, 0)
        self.assertEqual(mock_legacy.call_count, 1)
        self.assertEqual(mock_model.call_count, 1)


if __name__ == "__main__":
    unittest.main()
