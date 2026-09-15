from __future__ import annotations

import unittest
from unittest.mock import patch

import minidora.hds_choice_runtime as runtime
from minidora.hds_choice_runtime import HDS選択実行結果
from minidora.参照 import 参照記録


class CoreLocalViewMonotonicV1Test(unittest.TestCase):
    def _結果(self, state: str, label=None, content=None):
        return HDS選択実行結果(state, label, content, (state,), None, 2, 1, 0, 0, 0, 0)

    def test_既存承認は完全透過する(self) -> None:
        approved = self._結果("APPROVE", "A", "alpha")
        with patch.object(runtime, "_基準選択推論", return_value=approved) as base, \
             patch.object(runtime, "MINIDORA局所観測view") as local:
            result = runtime.HDS選択推論実行(
                object(),
                (参照記録("r", "q", "data", "test", "test"),),
                コンパイル=lambda x: x,
                基礎能力核=None,
                模型核=object(),
                正式模型評価=True,
            )
        self.assertIs(result, approved)
        self.assertEqual(base.call_count, 1)
        local.assert_not_called()

    def test_保留は新規閉包だけを追加する(self) -> None:
        suspended = self._結果("SUSPEND")
        approved = self._結果("APPROVE", "B", "beta")
        original = (参照記録("r", "q", "global data", "test", "test"),)
        local_refs = (参照記録("r", "q", "local beta data", "test", "test"),)
        with patch.object(runtime, "_基準選択推論", side_effect=(suspended, approved)) as base, \
             patch.object(runtime, "MINIDORA局所観測view", return_value=(local_refs, 1)):
            result = runtime.HDS選択推論実行(
                object(),
                original,
                コンパイル=lambda x: x,
                基礎能力核=None,
                模型核=object(),
                正式模型評価=True,
            )
        self.assertEqual(base.call_count, 2)
        self.assertEqual(result.状態, "APPROVE")
        self.assertEqual(result.回答ラベル, "B")
        self.assertIn("FORMAL_LOCAL_VIEW_RECHECK_SELECTED", result.理由)
        self.assertEqual(result.局所Window数, 1)
        self.assertEqual(result.局所再照合数, 1)


if __name__ == "__main__":
    unittest.main()
