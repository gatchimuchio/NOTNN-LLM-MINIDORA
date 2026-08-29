from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.runtime_hds_v1 import HDS駆動ミニドラ
from minidora.runtime_v03 import 要求
from minidora.参照 import 参照記録
from minidora.採否 import 実行状態


def _ir(text, coords, relations=(), *, required=False):
    return HDSIR(
        原文=text, 正規化文=text, 認知世界ID="hds-v1-integration",
        座標=coords, 関係=relations, 残差=(), 意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"), 参照必須=required,
        種別="knowledge_choice", 閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en", 手順=None,
    )


def _question():
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
            HDS座標("use", "関係.述語表層", "use", 原文範囲=(16, 19)),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone"),
            HDS座標("unknown", "目的.未知終点", "entity", 値状態.未観測),
        ),
        (HDS関係(
            "question-use", ("alpha",), ("unknown",), "使用",
            条件=("検索述語=use", "不足位置=終点", "英日意味射影=v0.5"),
            値状態=値状態.未観測,
        ),),
        required=True,
    )


def _candidate(text):
    return _ir(text, (HDS座標("candidate", "対象.実体", text, 原文範囲=(0, len(text))),))


def _data():
    return _ir(
        "Alpha uses engine.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("engine", "対象.実体", "engine", 原文範囲=(11, 17)),
        ),
        (HDS関係("use", ("alpha",), ("engine",), "使用", 条件=("検索述語=use",)),),
    )


class Compiler:
    def コンパイル(self, 入力: str, **kwargs):
        if 入力 == "What does Alpha use?":
            return _question()
        if 入力 in {"engine", "stone"}:
            return _candidate(入力)
        if 入力 == "Alpha uses engine.":
            return _data()
        raise ValueError(入力)


class Provider:
    名称 = "fixture-R"

    def 検索(self, 問合せ: str, 上限: int = 8):
        return (参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture"),)


class RuntimeHDSV1試験(unittest.TestCase):
    def test_実RuntimeでREFERENCE_EVALUATE_COMMITが成立する(self):
        runtime = HDS駆動ミニドラ(Provider(), HDSコンパイラ_=Compiler())
        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.合格, result.採否.理由)
        self.assertEqual(result.値, "engine")
        run = result.状態["HDS判断主体Run"]
        self.assertEqual(run["状態"], "COMMITTED")
        self.assertEqual(
            tuple(action for action, _ in run["作用履歴"]),
            ("REFERENCE", "EVALUATE", "COMMIT"),
        )
        self.assertEqual(run["評価状態"], "PROPOSE")
        self.assertIn("HDS_JUDGEMENT_SUBJECT_COMMIT", result.採否.理由)
        self.assertIn("FORMAL_MODEL_CORE_PROPOSAL_ONLY", result.採否.理由)
        self.assertNotIn("HDS_JUDGEMENT_SUBJECT_V2", result.採否.理由)
        self.assertNotIn("HDS_OUTPUT_ONLY_BOUNDARY", result.採否.理由)


if __name__ == "__main__":
    unittest.main()
