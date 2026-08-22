from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "hds_replay_compare_tool",
    ROOT / "tools" / "hds_replay_compare.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
compare = MODULE.compare


def _result(details, correct, answered):
    return {
        "total": len(details),
        "correct": correct,
        "accuracy_percent": 100.0 * correct / len(details),
        "answered": answered,
        "answer_rate_percent": 100.0 * answered / len(details),
        "details": details,
    }


class HDSReplay比較試験(unittest.TestCase):
    def test_SUSPENDから正答と誤答を別分類する(self) -> None:
        before = _result(
            [
                {"id": "a", "status": "SUSPEND", "predicted": None, "correct": False, "reasons": ["NO_KNOWLEDGE_EVIDENCE"]},
                {"id": "b", "status": "SUSPEND", "predicted": None, "correct": False, "reasons": ["NO_KNOWLEDGE_EVIDENCE"]},
            ],
            0,
            0,
        )
        after = _result(
            [
                {"id": "a", "status": "APPROVE", "predicted": "A", "correct": True, "reasons": ["EVIDENCE_PRESENT"]},
                {"id": "b", "status": "APPROVE", "predicted": "B", "correct": False, "reasons": ["EVIDENCE_PRESENT"]},
            ],
            1,
            2,
        )
        result = compare(before, after)
        self.assertEqual(result["transitions"]["SUSPEND_TO_CORRECT"], 1)
        self.assertEqual(result["transitions"]["SUSPEND_TO_WRONG"], 1)
        self.assertEqual(result["delta"]["correct"], 1)
        self.assertEqual(result["delta"]["answered"], 2)
        self.assertEqual(result["reason_delta"]["-NO_KNOWLEDGE_EVIDENCE"], 2)
        self.assertEqual(result["reason_delta"]["+EVIDENCE_PRESENT"], 2)

    def test_正答退行を明示分類する(self) -> None:
        before = _result(
            [{"id": "a", "status": "APPROVE", "predicted": "A", "correct": True, "reasons": []}],
            1,
            1,
        )
        after = _result(
            [{"id": "a", "status": "APPROVE", "predicted": "B", "correct": False, "reasons": []}],
            0,
            1,
        )
        result = compare(before, after)
        self.assertEqual(result["transitions"]["CORRECT_TO_WRONG"], 1)
        self.assertEqual(result["delta"]["correct"], -1)


if __name__ == "__main__":
    unittest.main()
