from __future__ import annotations

from dataclasses import dataclass
import unittest

from minidora.hds形成循環 import HDS形成台帳, HDS形成観測
from minidora.hds作用実効監査 import HDS作用実効監査
from minidora.hds統一状態循環 import HDS統一作用, HDS統一状態Session
from minidora.参照 import 参照記録


def _refs(n: int) -> tuple[参照記録, ...]:
    return tuple(
        参照記録(
            識別子=f"R{i:02d}",
            対象="test",
            内容=("target decisive evidence " if i >= n - 2 else "generic material ") + str(i),
            由来="unit",
            供給器="unit",
        )
        for i in range(n)
    )


@dataclass(frozen=True)
class _Subject:
    主体ID: str = "MINIDORA"
    版: int = 0

    def 辞書化(self):
        return {"主体ID": self.主体ID, "版": self.版}


class HDS統一状態RepoTests(unittest.TestCase):
    def test_plan_is_separate_from_archive_and_has_lease(self):
        session = HDS統一状態Session("target", _refs(12))
        self.assertEqual(len(session.参照正本), 12)
        self.assertEqual(len(session.選択参照()), 8)
        session.計画消費(1)
        self.assertEqual(session.参照計画.残存利用回数, 3)
        self.assertEqual(len(session.参照正本), 12)

    def test_candidate_change_rebinds_plan(self):
        session = HDS統一状態Session("target", _refs(12))
        session.選択参照()
        session.計画消費(1)
        session.候補状態記録({"A": 2.0, "B": 1.0}, stage="PASS1")
        session.選択参照()
        self.assertEqual(session.参照計画.残存利用回数, 4)
        self.assertTrue(any("PLAN_BINDING_CHANGED" in row for row in session.作用履歴))

    def test_subject_change_is_a_real_plan_invalidation_condition(self):
        session = HDS統一状態Session("target", _refs(4), 主体状態=_Subject())
        old = session.主体署名
        self.assertTrue(session.主体状態更新(_Subject(版=1)))
        self.assertNotEqual(old, session.主体署名)

    def test_parallel_pass_disagreement_opens_global_reconcile(self):
        session = HDS統一状態Session("target", _refs(4))
        session.候補状態記録({"A": 3.0, "B": 1.0}, stage="P1")
        session.候補状態記録({"A": 1.0, "B": 3.0}, stage="P2")
        self.assertEqual(session.lane不一致度(), 1.0)
        self.assertEqual(
            session.次作用(状態="SUSPEND", 出力存在=False, 理由=("UNRESOLVED",)),
            HDS統一作用.大域再照合,
        )

    def test_formation_is_not_active_until_explicitly_approved(self):
        ledger = HDS形成台帳()
        for i in range(3):
            ledger.記録(HDS形成観測(
                f"run{i}", f"input{i}", "REBUILD_RETRIEVAL_PLAN",
                ("EVIDENCE_GAP",), (), f"b{i}", f"a{i}", True, (f"R{i}",),
            ))
        candidate = ledger.候補群()[0]
        self.assertEqual(candidate.状態, "ELIGIBLE")
        self.assertEqual(ledger.推奨作用(("EVIDENCE_GAP",)), ())
        ledger.承認(candidate.候補ID, 理由=("independent repeated progress",))
        self.assertEqual(ledger.推奨作用(("EVIDENCE_GAP",)), ("REBUILD_RETRIEVAL_PLAN",))

    def test_effect_audit_requires_downstream_difference(self):
        audited = HDS作用実効監査(
            "checkpoint",
            基準実行=lambda: {"状態": "S1", "経路": ("REACTIVATE",), "結果": "A"},
            変種実行={"removed": lambda: {"状態": "S0", "経路": (), "結果": "B"}},
        )
        self.assertTrue(audited.実効作用)


if __name__ == "__main__":
    unittest.main()
