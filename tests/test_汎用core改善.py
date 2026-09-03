from __future__ import annotations

import unittest

from minidora.能力状態差循環 import MINIDORA能力状態差模型核, 標準能力模型核
from minidora.模型 import 成立候補, 言語状態, 関係寄与


class 汎用Core改善試験(unittest.TestCase):
    def test_同一Dataの出典ID違いは票を増幅しない(self) -> None:
        def 評価(refs):
            return 標準能力模型核().評価言語状態(
                言語状態("which"),
                (成立候補("A", 言語状態("alpha")), 成立候補("B", 言語状態("beta"))),
                参照状態=tuple(refs),
            )
        base = 評価((言語状態("alpha", 識別子="r-alpha"), 言語状態("beta", 識別子="r-beta-1")))
        duplicated = 評価((言語状態("alpha", 識別子="r-alpha"), 言語状態("beta", 識別子="r-beta-1"), 言語状態("beta", 識別子="r-beta-2")))
        self.assertEqual(len(duplicated.文脈.参照状態), 2)
        self.assertEqual(base.参照候補辞書(), duplicated.参照候補辞書())
        self.assertEqual(base.参照最有力候補ID, duplicated.参照最有力候補ID)

    def test_異なるDataは別Dataとして保持する(self) -> None:
        result = 標準能力模型核().評価言語状態(
            言語状態("which"),
            (成立候補("A", 言語状態("alpha")), 成立候補("B", 言語状態("beta"))),
            参照状態=(言語状態("alpha first", 識別子="r-alpha"), 言語状態("beta first", 識別子="r-beta-1"), 言語状態("beta second", 識別子="r-beta-2")),
        )
        self.assertEqual(len(result.文脈.参照状態), 3)
        self.assertEqual(result.参照最有力候補ID, "B")

    def test_再作用は現在首位と最強変化候補を比較する(self) -> None:
        class 初期差:
            名称 = "初期差"
            def 評価(self, 文脈, 候補):
                if "leader" in 候補.意味語集合: return 関係寄与(self.名称, 5, ("leader",))
                if "challenger" in 候補.意味語集合: return 関係寄与(self.名称, 2, ("challenger",))
                if "decoy" in 候補.意味語集合: return 関係寄与(self.名称, 1, ("decoy",))
                return None
        class 境界再作用:
            名称 = "境界再作用"
            def 評価群(self, 文脈, 候補群):
                out = {}
                for cid, state in 候補群:
                    if "challenger" in state.意味語集合: out[cid] = 関係寄与(self.名称, 2, ("primary",))
                    elif "decoy" in state.意味語集合: out[cid] = 関係寄与(self.名称, 2, ("primary",))
                return out
            def 再評価群(self, 文脈, 候補群, round_index):
                tokens = {cid: state.意味語集合 for cid, state in 候補群}
                leader = next((cid for cid, vals in tokens.items() if "leader" in vals), None)
                challenger = next((cid for cid, vals in tokens.items() if "challenger" in vals), None)
                if leader is None or challenger is None: return {}
                return {challenger: 関係寄与(f"境界再作用:{round_index}", 3, ("leader-vs-challenger",))}
        core = MINIDORA能力状態差模型核((初期差(),), 能力作用群=(境界再作用(),), 最大再作用回数=1)
        result = core.評価言語状態(
            言語状態("question"),
            (成立候補("A", 言語状態("leader")), 成立候補("B", 言語状態("challenger")), 成立候補("C", 言語状態("decoy"))),
        )
        self.assertEqual(result.最有力候補ID, "B")
        self.assertEqual(result.統計.checkpoint再活性数, 1)
        self.assertGreaterEqual(result.統計.候補横断更新数, 1)


if __name__ == "__main__":
    unittest.main()
