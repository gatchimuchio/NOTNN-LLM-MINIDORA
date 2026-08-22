from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.hds_replay import HDSIR辞書化
from minidora.hds_replay_eval import HDSReplayCase評価, HDSReplay評価


def _ir(text: str, coords: tuple[HDS座標, ...], relations: tuple[HDS関係, ...] = ()) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="replay-eval-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        種別="意味構造",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
    )


def _question() -> HDSIR:
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha"),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
        ),
    )


def _candidate(text: str) -> HDSIR:
    return _ir(text, (HDS座標("candidate", "対象.実体", text),))


def _data(target: str) -> HDSIR:
    return _ir(
        f"Alpha uses {target}.",
        (
            HDS座標("alpha", "対象.実体", "Alpha"),
            HDS座標("target", "対象.実体", target),
        ),
        (HDS関係("use", ("alpha",), ("target",), "作用"),),
    )


class HDSReplay評価試験(unittest.TestCase):
    def test_source_confidenceを再生して高信頼source側を選ぶ(self) -> None:
        row = {
            "schema": "minidora.hds-choice-replay.v1",
            "id": "confidence-case",
            "question_ir": HDSIR辞書化(_question()),
            "choices_ir": {
                "A": HDSIR辞書化(_candidate("engine")),
                "B": HDSIR辞書化(_candidate("stone")),
            },
            "data": [
                {
                    "provenance": ["fixture", "doc:engine"],
                    "source_confidence": 0.2,
                    "ir": HDSIR辞書化(_data("engine")),
                },
                {
                    "provenance": ["fixture", "doc:stone"],
                    "source_confidence": 0.9,
                    "ir": HDSIR辞書化(_data("stone")),
                },
            ],
            "gold": "B",
        }

        detail = HDSReplayCase評価(row)
        self.assertEqual(detail.状態, "APPROVE", detail.候補診断)
        self.assertEqual(detail.予測, "B", detail.候補診断)
        self.assertTrue(detail.正解)

    def test_集計は回答率正答率理由努力分布を返す(self) -> None:
        row = {
            "schema": "minidora.hds-choice-replay.v1",
            "id": "one",
            "question_ir": HDSIR辞書化(_question()),
            "choices_ir": {
                "A": HDSIR辞書化(_candidate("engine")),
                "B": HDSIR辞書化(_candidate("stone")),
            },
            "data": [
                {
                    "provenance": ["fixture", "doc:engine"],
                    "source_confidence": 1.0,
                    "ir": HDSIR辞書化(_data("engine")),
                }
            ],
            "gold": "A",
        }
        result = HDSReplay評価((row,))
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["with_gold"], 1)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["answered"], 1)
        self.assertEqual(result["suspended"], 0)
        self.assertIn(result["details"][0]["effort"], {"low", "high", "max"})


if __name__ == "__main__":
    unittest.main()
