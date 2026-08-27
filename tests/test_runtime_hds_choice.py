from __future__ import annotations

import unittest

from minidora import (
    HDSIR,
    HDS実行核,
    HDS座標,
    HDS関係,
    値状態,
    ミニドラ,
    参照記録,
    実行状態,
    要求,
)


def _ir(
    text: str,
    coords: tuple[HDS座標, ...],
    relations: tuple[HDS関係, ...] = (),
    *,
    reference_required: bool = False,
) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID="runtime-choice-test",
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        参照必須=reference_required,
        種別="knowledge_choice",
        閉包状態="CLOSED_FOR_SEMANTIC_TRANSFER",
        入力言語="en",
        手順=None,
    )


def _question(choice_b_state: 値状態 = 値状態.確定) -> HDSIR:
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
            HDS座標("use", "関係.述語表層", "use", 原文範囲=(16, 19)),
            HDS座標("choice:A", "目的.候補", "engine"),
            HDS座標("choice:B", "目的.候補", "stone", 値状態=choice_b_state),
            HDS座標("unknown", "目的.未知終点", "entity", 値状態.未観測),
        ),
        (HDS関係(
            "question-use", ("alpha",), ("unknown",), "使用",
            条件=("検索述語=use", "不足位置=終点", "英日意味射影=v0.5"),
            値状態=値状態.未観測,
        ),),
        reference_required=True,
    )


def _candidate(text: str) -> HDSIR:
    return _ir(text, (HDS座標("candidate", "対象.実体", text, 原文範囲=(0, len(text))),))


def _data() -> HDSIR:
    return _ir(
        "Alpha uses engine.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("engine", "対象.実体", "engine", 原文範囲=(11, 17)),
        ),
        (HDS関係("use", ("alpha",), ("engine",), "使用", 条件=("検索述語=use",)),),
    )


class _Compiler:
    def __init__(self, *, fail_choice: str | None = None, fail_data: set[str] | None = None, choice_state: 値状態 = 値状態.確定) -> None:
        self.fail_choice = fail_choice
        self.fail_data = set(fail_data or ())
        self.choice_state = choice_state
        self.calls: list[str] = []

    def コンパイル(self, 入力: str, **kwargs) -> HDSIR:
        self.calls.append(入力)
        if 入力 == "What does Alpha use?":
            return _question(self.choice_state)
        if 入力 in {"engine", "stone"}:
            if 入力 == self.fail_choice:
                raise ValueError("choice compile failed")
            return _candidate(入力)
        if 入力 in self.fail_data:
            raise ValueError("data compile failed")
        if 入力 == "Alpha uses engine.":
            return _data()
        raise ValueError(f"unknown input: {入力}")


class _Provider:
    名称 = "fixture-R"

    def __init__(self, records: tuple[参照記録, ...]) -> None:
        self.records = records

    def 検索(self, 問合せ: str, 上限: int = 8):
        return self.records[:上限]


class RuntimeHDSChoice試験(unittest.TestCase):
    def test_手順なしchoiceを正式模型核_HDS_J経路で解く(self) -> None:
        compiler = _Compiler()
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        runtime = ミニドラ(_Provider((record,)), HDSコンパイラ_=compiler)

        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.合格, result.採否.理由)
        self.assertEqual(result.値, "engine")
        self.assertEqual(result.言語計画, "HDS_CHOICE_NATIVE")
        self.assertEqual(result.状態["HDS候補ラベル"], "A")
        self.assertEqual(result.状態["HDS候補コンパイル数"], 2)
        self.assertEqual(result.状態["HDS_Dataコンパイル数"], 1)
        self.assertEqual(result.状態["K追加事実数"], 0)
        self.assertEqual(result.状態["K証拠事実数"], 0)
        self.assertIn("FORMAL_MODEL_CORE_WITH_HDS_J", result.採否.理由)
        self.assertIn("HDS_JUDGEMENT_SUBJECT_V1", result.採否.理由)
        self.assertIn("engine", compiler.calls)
        self.assertIn("stone", compiler.calls)
        self.assertIn("Alpha uses engine.", compiler.calls)
        self.assertTrue(any(item["op"] == "R_TO_HDS_TO_K" for item in result.履歴))

    def test_参照信頼0はHDS_JがCommitせず保留する(self) -> None:
        compiler = _Compiler()
        record = 参照記録(
            "doc:untrusted", "Alpha", "Alpha uses engine.", "fixture://untrusted", "fixture", 信頼=0.0
        )
        runtime = ミニドラ(_Provider((record,)), HDSコンパイラ_=compiler)

        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.保留, result.採否.理由)
        self.assertIsNone(result.値)
        self.assertIn("HDS_EVIDENCE_INSUFFICIENT", result.採否.理由)
        self.assertIn("FORMAL_MODEL_CORE_WITH_HDS_J", result.採否.理由)

    def test_choiceのHDSコンパイル失敗は生文字列fallbackせずSUSPEND(self) -> None:
        compiler = _Compiler(fail_choice="stone")
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        runtime = ミニドラ(_Provider((record,)), HDSコンパイラ_=compiler)

        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIsNone(result.値)
        self.assertIn("HDS_CHOICE_COMPILE_FAILED", result.採否.理由)

    def test_Data一件失敗でも生Dataを使わず残りHDS証拠だけで判断する(self) -> None:
        compiler = _Compiler(fail_data={"bad raw document"})
        records = (
            参照記録("bad", "bad", "bad raw document", "fixture://bad", "fixture", 信頼=0.2),
            参照記録("good", "Alpha", "Alpha uses engine.", "fixture://good", "fixture", 信頼=1.0),
        )
        runtime = ミニドラ(_Provider(records), HDSコンパイラ_=compiler)

        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.合格, result.採否.理由)
        self.assertEqual(result.値, "engine")
        self.assertEqual(result.状態["HDS_Dataコンパイル数"], 1)
        self.assertEqual(result.状態["HDS_Dataコンパイル失敗数"], 1)
        self.assertTrue(any(reason == "DATA_COMPILE_PARTIAL:1" for reason in result.採否.理由))

    def test_未確定choice集合はJへ進めずSUSPEND(self) -> None:
        compiler = _Compiler(choice_state=値状態.未確定)
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        runtime = ミニドラ(_Provider((record,)), HDSコンパイラ_=compiler)

        result = runtime.実行(要求("What does Alpha use?"))

        self.assertEqual(result.採否.状態, 実行状態.保留)
        self.assertIsNone(result.値)
        self.assertIn("HDS_CHOICE_UNRESOLVED", result.採否.理由)
        self.assertNotIn("engine", compiler.calls)
        self.assertNotIn("Alpha uses engine.", compiler.calls)


if __name__ == "__main__":
    unittest.main()
