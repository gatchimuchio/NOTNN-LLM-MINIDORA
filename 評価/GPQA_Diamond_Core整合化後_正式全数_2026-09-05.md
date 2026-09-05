# GPQA Diamond Core整合化後 正式全数 — 2026-09-05

標準 `tools/benchmark_formal.py` を4つの非重複index範囲へ分割し、全198問を結合した正式測定。
専門Capability Moduleは除外。Goldは推論完了後の採点にのみ使用。

```json
{
  "completed": 198,
  "current_correct": 26,
  "current_accuracy_percent": 13.131313131313131,
  "current_answered": 121,
  "current_answer_rate_percent": 61.111111111111114,
  "current_answered_accuracy_percent": 21.487603305785125,
  "current_suspended": 77,
  "baseline_correct": 20,
  "baseline_accuracy_percent": 10.1010101010101,
  "baseline_answered": 90,
  "baseline_suspended": 108,
  "correct_delta": 6,
  "improved_cases": 6,
  "regressed_cases": 0,
  "net_improved_cases": 6,
  "changed_answers": 31,
  "specialist_actions_invoked": 0,
  "hds_supervisory_interventions": 499,
  "hds_intervention_cases": 107,
  "hds_intervention_action_counts": {
    "EXISTING_COMPUTE_EXECUTOR": 11,
    "REFERENCE": 107
  }
}
```
