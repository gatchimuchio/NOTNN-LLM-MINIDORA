# MINIDORA GPQA Diamond — 最小汎用core全数実測

- 実測日: 2026-09-01 JST
- source commit: `06c0d24f0ce3203ac20d9b85b836fe184f29f49b`
- workflow run: `33408451266`
- benchmark: GPQA Diamond 198問
- controlled A/B: 有効
- specialist solver: active pathから除外
- specialist actions invoked: 0
- gold boundary: baseline/current推論後の採点にのみ使用

## Current — 最小汎用core + HDS異常時最小介入

- completed: 198 / 198
- correct: 23
- wrong: 101
- overall accuracy: 11.616161616161616%
- answered: 124
- answer rate: 62.62626262626262%
- answered accuracy: 18.548387096774192%
- suspended: 74
- retrieval empty: 0
- documents retrieved: 2718
- data compiled: 4550
- data compile failed: 0
- HDS intervention cases: 108
- HDS supervisory interventions: 483

## Controlled baseline — 同一正式汎用模型核 / HDS非介入

- completed: 198 / 198
- correct: 19
- wrong: 69
- overall accuracy: 9.595959595959595%
- answered: 88
- answer rate: 44.44444444444444%
- answered accuracy: 21.59090909090909%
- suspended: 110

## Controlled delta

- correct delta: +4
- accuracy: +2.0202020202020208 points
- answered delta: +36
- answer rate: +18.18181818181818 points
- answered accuracy: -3.0425219941348978 points
- changed answers: 36
- improved cases: 4
- regressed cases: 0
- net improved cases: +4

## 境界確認

この測定では、候補解決は正式MINIDORA汎用模型核のみを使用し、専門solver、supervisory resolver、HDSによるwinner selectionは使用していない。HDSは未閉包・競合・観測不足等の異常時に既存作用を起動する安全弁としてのみ介入した。

実測workflowは全step successで完了し、成果物 `minidora-gpqa-current-measurement` が保存された。
