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
    参照_required: bool = False,
) -> HDSIR:
    return HDSIR(
        原文=text,
        正規化文=text,
        認知世界ID='実行系-選択肢-test',
        座標=coords,
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("意味構造転送"),
        参照必須=参照_required,
        種別='knowledge_選択肢',
        閉包状態='CLOSED_FOR_意味_TRANSFER',
        入力言語="en",
        手順=None,
    )


def _question(選択肢_b_状態: 値状態 = 値状態.確定) -> HDSIR:
    return _ir(
        "What does Alpha use?",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(10, 15)),
            HDS座標("use", "関係.述語表層", "use", 原文範囲=(16, 19)),
            HDS座標('選択肢:A', "目的.候補", "engine"),
            HDS座標('選択肢:B', "目的.候補", "stone", 値状態=選択肢_b_状態),
            HDS座標('未知', "目的.未知終点", "entity", 値状態.未観測),
        ),
        (HDS関係(
            "question-use", ("alpha",), ('未知',), "使用",
            条件=("検索述語=use", "不足位置=終点", "英日意味射影=v0.5"),
            値状態=値状態.未観測,
        ),),
        参照_required=True,
    )


def _候補(text: str) -> HDSIR:
    return _ir(text, (HDS座標('候補', "対象.実体", text, 原文範囲=(0, len(text))),))


def _資料() -> HDSIR:
    return _ir(
        "Alpha uses engine.",
        (
            HDS座標("alpha", "対象.実体", "Alpha", 原文範囲=(0, 5)),
            HDS座標("engine", "対象.実体", "engine", 原文範囲=(11, 17)),
        ),
        (HDS関係("use", ("alpha",), ("engine",), "使用", 条件=("検索述語=use",)),),
    )


class _構文化器:
    def __init__(self, *, fail_選択肢: str | None = None, fail_資料: set[str] | None = None, 選択肢_状態: 値状態 = 値状態.確定) -> None:
        self.fail_選択肢 = fail_選択肢
        self.fail_資料 = set(fail_資料 or ())
        self.選択肢_状態 = 選択肢_状態
        self.calls: list[str] = []

    def コンパイル(self, 入力: str, **kwargs) -> HDSIR:
        self.calls.append(入力)
        if 入力 == "What does Alpha use?":
            return _question(self.選択肢_状態)
        if 入力 in {"engine", "stone"}:
            if 入力 == self.fail_選択肢:
                raise ValueError("choice compile failed")
            return _候補(入力)
        if 入力 in self.fail_資料:
            raise ValueError("data compile failed")
        if 入力 == "Alpha uses engine.":
            return _資料()
        raise ValueError(f"unknown input: {入力}")


class _Provider:
    名称 = "fixture-R"

    def __init__(self, records: tuple[参照記録, ...]) -> None:
        self.records = records

    def 検索(self, 問合せ: str, 上限: int = 8):
        return self.records[:上限]


class RuntimeHDS選択肢試験(unittest.TestCase):
    def test_手順なし選択肢を通常MINIDORAで解きHDS非介入なら完全透過(self) -> None:
        構文化器 = _構文化器()
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        実行系 = ミニドラ(_Provider((record,)), HDSコンパイラ_=構文化器)

        結果 = 実行系.実行(要求("What does Alpha use?"))

        self.assertEqual(結果.採否.状態, 実行状態.合格, 結果.採否.理由)
        self.assertEqual(結果.値, "engine")
        self.assertEqual(結果.言語計画, 'HDS_選択肢_NATIVE')
        self.assertEqual(結果.状態["HDS候補ラベル"], "A")
        self.assertEqual(結果.状態["HDS候補コンパイル数"], 2)
        self.assertEqual(結果.状態['HDS_資料コンパイル数'], 1)
        self.assertNotIn('EXISTING_MINIDORA_能力_RESOLVER', 結果.採否.理由)
        self.assertNotIn("HDS_SUPERVISORY_INTERVENTION", 結果.採否.理由)
        self.assertNotIn("HDS_SUPERVISORY_INTERVENTIONS:0", 結果.採否.理由)
        self.assertIn("engine", 構文化器.calls)
        self.assertIn("stone", 構文化器.calls)
        self.assertIn("Alpha uses engine.", 構文化器.calls)
        self.assertTrue(any(item["op"] == "R_TO_HDS_TO_K" for item in 結果.履歴))

    def test_参照信頼をHDSが最終採否しない(self) -> None:
        構文化器 = _構文化器()
        record = 参照記録(
            "doc:untrusted", "Alpha", "Alpha uses engine.", "fixture://untrusted", "fixture", 信頼=0.0
        )
        実行系 = ミニドラ(_Provider((record,)), HDSコンパイラ_=構文化器)

        結果 = 実行系.実行(要求("What does Alpha use?"))

        self.assertEqual(結果.採否.状態, 実行状態.合格, 結果.採否.理由)
        self.assertEqual(結果.値, "engine")
        self.assertNotIn("HDS_SUPERVISORY_INTERVENTION", 結果.採否.理由)
        self.assertNotIn('HDS_証拠_INSUFFICIENT', 結果.採否.理由)

    def test_選択肢のHDSコンパイル失敗は生文字列代替経路せずSUSPEND(self) -> None:
        構文化器 = _構文化器(fail_選択肢="stone")
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        実行系 = ミニドラ(_Provider((record,)), HDSコンパイラ_=構文化器)

        結果 = 実行系.実行(要求("What does Alpha use?"))

        self.assertEqual(結果.採否.状態, 実行状態.保留)
        self.assertIsNone(結果.値)
        self.assertIn('HDS_選択肢_COMPILE_FAILED', 結果.採否.理由)
        self.assertNotIn("HDS_SUPERVISORY_INTERVENTIONS:0", 結果.採否.理由)

    def test_資料一件失敗でも生資料を使わず残りHDS入力だけでMINIDORAを実行する(self) -> None:
        構文化器 = _構文化器(fail_資料={"bad raw document"})
        records = (
            参照記録("bad", "bad", "bad raw document", "fixture://bad", "fixture", 信頼=0.2),
            参照記録("good", "Alpha", "Alpha uses engine.", "fixture://good", "fixture", 信頼=1.0),
        )
        実行系 = ミニドラ(_Provider(records), HDSコンパイラ_=構文化器)

        結果 = 実行系.実行(要求("What does Alpha use?"))

        self.assertEqual(結果.採否.状態, 実行状態.合格, 結果.採否.理由)
        self.assertEqual(結果.値, "engine")
        self.assertEqual(結果.状態['HDS_資料コンパイル数'], 1)
        self.assertEqual(結果.状態['HDS_資料コンパイル失敗数'], 1)
        self.assertTrue(any(reason == '資料_COMPILE_PARTIAL:1' for reason in 結果.採否.理由))

    def test_未確定選択肢集合はMINIDORAへ進めずSUSPEND(self) -> None:
        構文化器 = _構文化器(選択肢_状態=値状態.未確定)
        record = 参照記録("doc:1", "Alpha", "Alpha uses engine.", "fixture://doc1", "fixture")
        実行系 = ミニドラ(_Provider((record,)), HDSコンパイラ_=構文化器)

        結果 = 実行系.実行(要求("What does Alpha use?"))

        self.assertEqual(結果.採否.状態, 実行状態.保留)
        self.assertIsNone(結果.値)
        self.assertIn('HDS_選択肢_UNRESOLVED', 結果.採否.理由)
        self.assertNotIn("HDS_SUPERVISORY_INTERVENTIONS:0", 結果.採否.理由)
        self.assertNotIn("engine", 構文化器.calls)
        self.assertNotIn("Alpha uses engine.", 構文化器.calls)


if __name__ == "__main__":
    unittest.main()
