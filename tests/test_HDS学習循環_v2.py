from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS終端
from minidora.HDS選択実行系 import HDS選択実行結果
from minidora.HDS選択継承循環 import (
    HDS選択継承供給,
    _強固定可能,
    回答成果名,
    非退行判定成果名,
    参照成果名,
    参照履歴成果名,
    観測計画主体名,
)
from minidora.HDS駆動コア import HDS駆動コア
from minidora.参照 import 参照記録


class 固定参照:
    名称 = "学習試験参照"

    def __init__(self):
        self.呼出回数 = 0

    def 検索(self, 問合せ, 上限=8):
        self.呼出回数 += 1
        return (
            参照記録(
                識別子="learn:1",
                対象="追加観測",
                内容="Additional observation for candidate discrimination.",
                由来="学習試験",
                供給器=self.名称,
                信頼=1.0,
            ),
        )[:上限]


def 結果(label: str, *reasons: str, K3結果=None, K証拠事実数: int = 0) -> HDS選択実行結果:
    return HDS選択実行結果(
        状態="APPROVE",
        回答ラベル=label,
        回答内容=label,
        理由=tuple(reasons),
        K3結果=K3結果,
        候補コンパイル数=2,
        資料コンパイル数=1,
        資料コンパイル失敗数=0,
        K追加事実数=0,
        K証拠事実数=K証拠事実数,
        K証拠阻害事実数=0,
    )


class HDS学習循環V2試験(unittest.TestCase):
    def setUp(self):
        self.構文化器 = 公開HDSコンパイラ()
        self.問い = "Which molecule inhibits Enzyme X?"
        self.選択肢 = ("Molecule A", "Molecule B")

    def _実行(self, 評価列, *, 最大回復回数=2):
        provider = 固定参照()
        calls = []

        def 擬似評価(_self, refs):
            calls.append(len(refs))
            index = min(len(calls) - 1, len(評価列) - 1)
            return 評価列[index]

        コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=32)
        with patch.object(HDS選択継承供給, "_評価", new=擬似評価):
            out = コア.選択実行(
                self.問い,
                self.選択肢,
                初期参照=(),
                参照供給器=provider,
                最大回復回数=最大回復回数,
            )
        return out, provider, calls

    def test_満杯の旧評価窓を新観測へ更新し履歴は欠落させない(self):
        初期参照 = tuple(
            参照記録(
                識別子=f"old:{番号}",
                対象="旧観測",
                内容=f"old evidence {番号}",
                由来="学習試験",
                供給器="test",
                信頼=1.0,
            )
            for 番号 in range(4)
        )
        新観測 = (
            参照記録(
                識別子="new:A",
                対象="新観測A",
                内容="new evidence A",
                由来="学習試験",
                供給器="test",
                信頼=1.0,
                条件=(("hds_query_選択肢", "A"),),
            ),
            参照記録(
                識別子="new:B",
                対象="新観測B",
                内容="new evidence B",
                由来="学習試験",
                供給器="test",
                信頼=1.0,
                条件=(("hds_query_選択肢", "B"),),
            ),
        )

        def 擬似評価(_self, refs):
            ids = {x.識別子 for x in refs}
            if "new:A" in ids:
                return 結果("A", "DIRECTED_関係_VERIFIED", "EXISTING_DIRECT_関係_VERIFIED")
            return HDS選択実行結果(
                状態="SUSPEND",
                回答ラベル=None,
                回答内容=None,
                理由=("MINIDORA_模型_模型核_NO_参照_CONTRIBUTION", "NO_GUESS"),
                K3結果=None,
                候補コンパイル数=2,
                資料コンパイル数=len(refs),
                資料コンパイル失敗数=0,
                K追加事実数=0,
                K証拠事実数=0,
                K証拠阻害事実数=0,
            )

        コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=32)
        with patch.object(HDS選択継承供給, "_評価", new=擬似評価), patch(
            "minidora.HDS選択継承循環.HDS追加参照検索", return_value=新観測
        ):
            out = コア.選択実行(
                self.問い,
                self.選択肢,
                初期参照=初期参照,
                参照供給器=固定参照(),
                最大回復回数=1,
                拡張採用証明=lambda _基準, _拡張: True,
            )

        self.assertEqual(out.終端, HDS終端.採用, out.理由)
        成果 = out.状態.成果辞書()
        評価窓 = 成果[参照成果名]
        履歴 = 成果[参照履歴成果名]
        self.assertEqual(len(評価窓), 4)
        self.assertTrue({"new:A", "new:B"}.issubset({x.識別子 for x in 評価窓}))
        self.assertEqual(
            {x.識別子 for x in 履歴},
            {"old:0", "old:1", "old:2", "old:3", "new:A", "new:B"},
        )
        self.assertIn("HDS継承/追加参照", [x.作用ID for x in out.履歴])

    def test_弱い初期承認の再検証は候補差探索へ接続する(self):
        基準 = 結果("A", "EXISTING_SINGLE_CAPABILITY_PROPOSAL")
        再検証 = 結果("A", "DIRECTED_関係_VERIFIED", "EXISTING_DIRECT_関係_VERIFIED")
        探索種別群 = []

        def 擬似評価(_self, refs):
            return 基準 if not refs else 再検証

        def 擬似追加参照(_provider, _ir, *, 段階=1, 最大取得上限=32, 探索種別="標準"):
            探索種別群.append(探索種別)
            return (
                参照記録(
                    識別子=f"mode:{段階}",
                    対象="再検証",
                    内容="Independent candidate evidence.",
                    由来="学習試験",
                    供給器="test",
                    信頼=1.0,
                ),
            )

        コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=32)
        with patch.object(HDS選択継承供給, "_評価", new=擬似評価), patch(
            "minidora.HDS選択継承循環.HDS追加参照検索", new=擬似追加参照
        ):
            out = コア.選択実行(
                self.問い,
                self.選択肢,
                初期参照=(),
                参照供給器=固定参照(),
                最大回復回数=2,
            )

        self.assertEqual(out.終端, HDS終端.採用, out.理由)
        self.assertTrue(探索種別群)
        self.assertEqual(探索種別群[0], "候補差")

    def test_観測無進展の次世代は縮退探索へ切り替える(self):
        保留 = HDS選択実行結果(
            状態="SUSPEND",
            回答ラベル=None,
            回答内容=None,
            理由=("MINIDORA_模型_模型核_NO_参照_CONTRIBUTION", "NO_GUESS"),
            K3結果=None,
            候補コンパイル数=2,
            資料コンパイル数=0,
            資料コンパイル失敗数=0,
            K追加事実数=0,
            K証拠事実数=0,
            K証拠阻害事実数=0,
        )
        探索種別群 = []
        呼出 = 0

        def 擬似評価(_self, _refs):
            return 保留

        def 擬似追加参照(_provider, _ir, *, 段階=1, 最大取得上限=32, 探索種別="標準"):
            nonlocal 呼出
            呼出 += 1
            探索種別群.append(探索種別)
            if 呼出 == 1:
                return ()
            return (
                参照記録(
                    識別子="new:after-stall",
                    対象="縮退観測",
                    内容="New evidence after stalled observation.",
                    由来="学習試験",
                    供給器="test",
                    信頼=1.0,
                ),
            )

        コア = HDS駆動コア(HDSコンパイラ=self.構文化器, 最大作用回数=40)
        with patch.object(HDS選択継承供給, "_評価", new=擬似評価), patch(
            "minidora.HDS選択継承循環.HDS追加参照検索", new=擬似追加参照
        ):
            コア.選択実行(
                self.問い,
                self.選択肢,
                初期参照=(),
                参照供給器=固定参照(),
                最大回復回数=2,
            )

        self.assertGreaterEqual(len(探索種別群), 2)
        self.assertEqual(探索種別群[0], "標準")
        self.assertEqual(探索種別群[1], "縮退")

    def test_K3同一出典の複数事実だけでは初期承認を強固定しない(self):
        診断 = SimpleNamespace(候補="A", 合計得点=5.0, 独立出典数=1, 識別一致出典数=1)
        K3結果 = SimpleNamespace(候補診断=(診断,), 根拠事実数=4)
        基準 = 結果("A", "EXISTING_SINGLE_CAPABILITY_PROPOSAL", K3結果=K3結果, K証拠事実数=4)
        self.assertFalse(_強固定可能(基準))

    def test_K3独立二出典かつ識別一致なら強固定できる(self):
        採用 = SimpleNamespace(候補="A", 合計得点=6.0, 独立出典数=2, 識別一致出典数=1)
        他候補 = SimpleNamespace(候補="B", 合計得点=2.0, 独立出典数=1, 識別一致出典数=0)
        K3結果 = SimpleNamespace(候補診断=(採用, 他候補), 根拠事実数=3)
        基準 = 結果("A", "EXISTING_SINGLE_CAPABILITY_PROPOSAL", K3結果=K3結果, K証拠事実数=3)
        self.assertTrue(_強固定可能(基準))

    def test_弱い初期承認は別観測で同じ回答なら再検証して閉包(self):
        base = 結果("A", "EXISTING_CAPABILITIES_AGREE", "AGREEING_EXISTING_CAPABILITIES:1")
        same = 結果("A", "EXISTING_CAPABILITIES_AGREE", "AGREEING_EXISTING_CAPABILITIES:1")
        out, provider, calls = self._実行((base, same))

        self.assertEqual(out.終端, HDS終端.採用, out.理由)
        self.assertEqual(out.状態.成果辞書()[回答成果名], "A")
        self.assertGreaterEqual(provider.呼出回数, 1)
        self.assertGreaterEqual(len(calls), 2)
        self.assertIn(観測計画主体名, out.状態.主体辞書())
        self.assertIn("HDS継承/観測計画導出", [x.作用ID for x in out.履歴])
        self.assertIn("HDS継承/追加参照", [x.作用ID for x in out.履歴])

    def test_弱い初期承認より強い直接証拠が別回答を示せば更新(self):
        base = 結果("A", "EXISTING_CAPABILITIES_AGREE", "AGREEING_EXISTING_CAPABILITIES:1")
        stronger = 結果("B", "DIRECTED_関係_VERIFIED", "EXISTING_DIRECT_関係_VERIFIED")
        out, provider, _calls = self._実行((base, stronger))

        self.assertEqual(out.終端, HDS終端.採用, out.理由)
        self.assertEqual(out.状態.成果辞書()[回答成果名], "B")
        decision = out.状態.成果辞書()[非退行判定成果名]
        self.assertTrue(decision.拡張採用)
        self.assertFalse(decision.基準固定)
        self.assertGreaterEqual(provider.呼出回数, 1)

    def test_弱い別回答しか得られなければ回復上限後に旧基準を保持(self):
        base = 結果("A", "EXISTING_CAPABILITIES_AGREE", "AGREEING_EXISTING_CAPABILITIES:1")
        weak_other = 結果("B", "EXISTING_CAPABILITIES_AGREE", "AGREEING_EXISTING_CAPABILITIES:1")
        out, provider, _calls = self._実行((base, weak_other), 最大回復回数=1)

        self.assertEqual(out.終端, HDS終端.採用, out.理由)
        self.assertEqual(out.状態.成果辞書()[回答成果名], "A")
        self.assertGreaterEqual(provider.呼出回数, 1)


if __name__ == "__main__":
    unittest.main()
