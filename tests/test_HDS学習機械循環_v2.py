from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from minidora.HDS構文化器_v1 import 公開HDSコンパイラ
from minidora.HDS実行主体 import HDS関数作用, HDS作用結果, HDS作用状態, HDS終端
from minidora.HDS選択継承循環 import HDS選択継承供給, 初回評価参照成果名
from minidora.HDS駆動コア import HDS駆動コア
from minidora.参照 import 参照記録
from minidora.統合駆動_v2.記憶 import HDS資料


class _空参照供給器:
    名称 = "学習機械空参照"
    並列安全 = False

    def __init__(self) -> None:
        self.問合せ: list[str] = []

    def 検索(self, 問合せ, 上限=8):
        self.問合せ.append(" ".join(str(問合せ).split()))
        return ()


class HDS学習機械循環V2試験(unittest.TestCase):
    def test_評価結果より前に現在状態から候補関係観測が発火する(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        供給器 = _空参照供給器()
        元評価 = HDS選択継承供給._評価
        評価時問合せ数: list[int] = []

        def 評価を監査(自己, 参照群):
            評価時問合せ数.append(len(供給器.問合せ))
            self.assertGreater(len(供給器.問合せ), 0)
            return 元評価(自己, 参照群)

        with patch.object(HDS選択継承供給, "_評価", new=評価を監査):
            中核.選択実行(
                "Which molecule inhibits Enzyme X?",
                ("Molecule A", "Molecule B"),
                初期参照=(),
                参照供給器=供給器,
                最大回復回数=2,
            )

        self.assertTrue(評価時問合せ数)
        self.assertGreater(評価時問合せ数[0], 0)

    def test_実観測参照は同一中核の次処理へ継承される(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        中核 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        問い = "Which molecule inhibits Enzyme X?"
        選択肢 = ("Molecule A", "Molecule B")
        観測 = 参照記録(
            識別子="memory-a",
            対象="Molecule A",
            内容="Molecule A inhibits Enzyme X.",
            由来="試験観測",
            供給器="試験",
            信頼=1.0,
        )

        中核.選択実行(問い, 選択肢, 初期参照=(観測,))
        self.assertGreaterEqual(中核.継続参照件数, 1)

        次 = 中核.選択実行(問い, 選択肢, 初期参照=())
        初回参照 = 次.状態.成果辞書().get(初回評価参照成果名, ())
        self.assertTrue(any(x.識別子 == "memory-a" for x in 初回参照))

    def test_継続状態は別中核へ漏れない(self) -> None:
        構文化器 = 公開HDSコンパイラ()
        問い = "Which molecule inhibits Enzyme X?"
        選択肢 = ("Molecule A", "Molecule B")
        観測 = 参照記録(
            識別子="memory-a",
            対象="Molecule A",
            内容="Molecule A inhibits Enzyme X.",
            由来="試験観測",
            供給器="試験",
            信頼=1.0,
        )
        第一 = HDS駆動コア(HDSコンパイラ=構文化器, 最大作用回数=40)
        第一.選択実行(問い, 選択肢, 初期参照=(観測,))
        self.assertGreaterEqual(第一.継続参照件数, 1)

        第二 = HDS駆動コア(HDSコンパイラ=公開HDSコンパイラ(), 最大作用回数=40)
        結果 = 第二.選択実行(問い, 選択肢, 初期参照=())
        初回参照 = 結果.状態.成果辞書().get(初回評価参照成果名, ())
        self.assertEqual(初回参照, ())
        self.assertEqual(第二.継続参照件数, 0)

    def test_HDS記憶は次実行の処理前提になる(self) -> None:
        中核 = HDS駆動コア(最大作用回数=16)
        資料 = HDS資料("経験資料", "1", "扉は施錠されていた", "試験")

        def 記憶する(状態):
            return HDS作用結果(
                HDS作用状態.成立,
                追加状態=frozenset({"記憶済み"}),
                記憶更新=状態.記憶.更新((資料,)),
            )

        初回 = 中核.実行(
            "経験を保持する",
            要求状態=("記憶済み",),
            追加作用=(HDS関数作用("経験保持", 記憶する, 出力状態=("記憶済み",)),),
        )
        self.assertEqual(初回.終端, HDS終端.採用)

        def 記憶を使う(状態):
            if "経験資料" not in 状態.記憶.正本辞書():
                return HDS作用結果(HDS作用状態.保留)
            return HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"経験利用済み"}))

        次回 = 中核.実行(
            "保持経験を後続処理で使う",
            要求状態=("経験利用済み",),
            追加作用=(HDS関数作用("経験利用", 記憶を使う, 出力状態=("経験利用済み",)),),
        )
        self.assertEqual(次回.終端, HDS終端.採用)

    def test_実行経験から形成した適応が同一中核の次実行へ継承される(self) -> None:
        中核 = HDS駆動コア(最大作用回数=24)
        作用群 = (
            HDS関数作用(
                "段1",
                lambda 状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"途中"})),
                出力状態=("途中",),
                純粋作用=True,
            ),
            HDS関数作用(
                "段2",
                lambda 状態: HDS作用結果(HDS作用状態.成立, 追加状態=frozenset({"完了"})),
                入力状態=("途中",),
                出力状態=("完了",),
                純粋作用=True,
            ),
        )

        初回 = 中核.実行("手順経験", 要求状態=("完了",), 追加作用=作用群)
        self.assertEqual(初回.終端, HDS終端.採用)
        self.assertTrue(初回.状態.形成関係)

        次回 = 中核.実行("手順経験", 要求状態=("完了",), 追加作用=作用群)
        self.assertEqual(次回.終端, HDS終端.採用)
        self.assertGreater(次回.計装.形成再利用数, 0)

    def test_継続状態を明示初期化できる(self) -> None:
        中核 = HDS駆動コア(HDSコンパイラ=公開HDSコンパイラ(), 最大作用回数=40)
        観測 = 参照記録("r", "Molecule A", "Molecule A inhibits Enzyme X.", "試験", "試験", 1.0)
        中核.選択実行(
            "Which molecule inhibits Enzyme X?",
            ("Molecule A", "Molecule B"),
            初期参照=(観測,),
        )
        self.assertGreater(中核.継続参照件数, 0)
        中核.継続状態を初期化()
        self.assertEqual(中核.継続参照件数, 0)


if __name__ == "__main__":
    unittest.main()
