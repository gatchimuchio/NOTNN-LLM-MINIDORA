from __future__ import annotations

import unittest

from minidora.hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係
from minidora.hds_reference import HDS参照予算選択, HDS参照検索
from minidora.参照 import 参照記録


def _ir(choice_count: int, relation_count: int = 0) -> HDSIR:
    coords = [HDS座標("alpha", "対象.実体", "Alpha")]
    for index in range(choice_count):
        coords.append(HDS座標(f"choice:{index}", "目的.候補", f"option{index}"))
    relations = tuple(
        HDS関係(f"r{index}", ("alpha",), ("alpha",), f"relation{index}")
        for index in range(relation_count)
    )
    return HDSIR(
        原文="Which option applies?",
        正規化文="Which option applies?",
        認知世界ID="reference-budget-test",
        座標=tuple(coords),
        関係=relations,
        残差=(),
        意味作用履歴=(),
        実行核=HDS実行核("参照回答"),
        参照必須=True,
        種別="knowledge_choice",
    )


class _ManyProvider:
    並列安全 = True
    名称 = "many"

    def 検索(self, query: str, limit: int = 8):
        token = str(abs(hash(query)))
        return tuple(
            参照記録(f"{token}:{i}", query, f"content:{i}", f"fixture://{token}/{i}", self.名称)
            for i in range(limit)
        )


class HDS参照Budget試験(unittest.TestCase):
    def test_4択はhighで12件budgetを持つ(self) -> None:
        budget = HDS参照予算選択(_ir(4))
        self.assertEqual(budget.努力水準, "high")
        self.assertEqual(budget.取得上限, 12)
        self.assertEqual(budget.一問合せ上限, 4)

    def test_高関係密度はmaxで16件budgetへ上がる(self) -> None:
        budget = HDS参照予算選択(_ir(4, relation_count=4))
        self.assertEqual(budget.努力水準, "max")
        self.assertEqual(budget.取得上限, 16)

    def test_highの既定検索は固定8件を越えて12件取得できる(self) -> None:
        records = HDS参照検索(_ManyProvider(), _ir(4))
        self.assertEqual(len(records), 12)

    def test_呼出側が明示上限を指定すればそれを尊重する(self) -> None:
        records = HDS参照検索(_ManyProvider(), _ir(4), 上限=5)
        self.assertEqual(len(records), 5)


if __name__ == "__main__":
    unittest.main()
