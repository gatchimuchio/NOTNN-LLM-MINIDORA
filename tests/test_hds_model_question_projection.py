from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, 値状態
from minidora.hds_model_projection import HDS内部言語状態, HDS模型問い表層
from minidora.hds_runtime_projection import HDSK質問射影, HDS模型質問射影
from minidora.模型 import 標準模型核


def fixture() -> HDSIR:
    return HDSIR(
        原文="Alpha belongs to Beta. Which item does Beta use?",
        正規化文="Alpha belongs to Beta. Which item does Beta use?",
        認知世界ID="model-question-projection-test",
        座標=(
            HDS座標("choice:A", "選択肢", "Gamma"),
            HDS座標("choice:B", "選択肢", "Delta"),
            HDS座標("alpha", "対象.実体", "Alpha"),
            HDS座標("beta", "対象.実体", "Beta"),
            HDS座標("unknown", "対象.未知", "?", 値状態.未観測),
        ),
        関係=(
            HDS関係("fact", ("alpha",), ("beta",), "所属", 値状態=値状態.確定),
            HDS関係(
                "question",
                ("beta",),
                ("unknown",),
                "使用",
                条件=("不足位置=終点", "検索述語=use"),
                値状態=値状態.推定,
            ),
        ),
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核(),
        種別="knowledge_query",
        入力言語="en",
    )


class 正式模型質問射影試験(unittest.TestCase):
    def test_旧K射影は問い関係だけへ縮約する(self):
        projected = HDSK質問射影(fixture())
        self.assertEqual(tuple(item.関係ID for item in projected.関係), ("question",))

    def test_正式模型射影は問いと確定背景事実を同時に保持する(self):
        projected = HDS模型質問射影(fixture())
        self.assertEqual({item.関係ID for item in projected.関係}, {"fact", "question"})
        question = next(item for item in projected.関係 if item.関係ID == "question")
        self.assertEqual(question.値状態, 値状態.確定)
        self.assertIn("MINIDORA質問射影", question.由来)

    def test_推定背景関係を推論前提へ昇格しない(self):
        base = fixture()
        uncertain = HDS関係("uncertain", ("alpha",), ("beta",), "因果", 値状態=値状態.推定)
        projected = HDS模型質問射影(
            HDSIR(
                原文=base.原文,
                正規化文=base.正規化文,
                認知世界ID=base.認知世界ID,
                座標=base.座標,
                関係=(*base.関係, uncertain),
                残差=base.残差,
                意味作用履歴=base.意味作用履歴,
                実行核=base.実行核,
                種別=base.種別,
                入力言語=base.入力言語,
            )
        )
        self.assertNotIn("uncertain", {item.関係ID for item in projected.関係})

    def test_問い表層から背景文を再解析しない(self):
        projected = HDSK質問射影(fixture())
        surface = HDS模型問い表層(projected)
        self.assertNotIn("Alpha", surface)
        self.assertNotIn("belongs", surface.casefold())
        state = HDS内部言語状態(
            projected,
            識別子="question",
            言語体系="自然言語:en",
            表層=surface,
        )
        internal = 標準模型核().言語対応.内部化(state)
        kinds = {item.種別 for item in internal.関係構造}
        self.assertIn("使用", kinds)
        self.assertNotIn("所属", kinds)


if __name__ == "__main__":
    unittest.main()
