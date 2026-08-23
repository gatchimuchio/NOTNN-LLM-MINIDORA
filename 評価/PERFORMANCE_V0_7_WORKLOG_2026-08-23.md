# MINIDORA 性能改善 v0.7 作業記録 — 2026-08-23

## 状態

```text
BASELINE RE-MEASUREMENT IN PROGRESS
ATTEMPT 1 REVERTED
CI 8/8 PASS
```

本記録は、現行mainに対する性能改善の探索履歴を保持する。過去のv0.6系実測 `31 / 198 = 15.6565657%` は有力な参照値だが、その後にHDS Compiler Architecture v1.2等がmainへ入っているため、現行mainとの直接差分として扱わない。

## 事前観測

v0.6系実測では、APPROVEした128問中31問正解で、回答時正答率は24.21875%だった。候補診断を再解析すると、正解候補の得点順位は1位から4位へほぼ均等に分布し、証拠得点とgraph得点の単純な重み変更だけでは改善しなかった。

実装経路の監査では、候補ごとの検索queryで取得した資料にも `query_choice:*` / `query_kind:*` provenanceが付与される一方、Data→HDS-IR→K投入後は通常資料と同じ候補証拠へ利用されることを確認した。

## Attempt 1 — 検索選択独立性の減衰

### 仮説

「候補を検索語へ含めたため取得できた」という選択条件と、「その資料が候補の真偽を独立に支持する」という証拠価値を分離し、候補指定queryだけで取得された資料を補助証拠へ落とせば候補識別が改善する。

### 実装

- `source confidence` と `retrieval independence` を分離。
- 候補指定queryだけで発見された資料へ `retrieval_independence = 0.25` を適用。
- 候補非依存queryでも同一資料が見つかった場合は1.0を維持。
- 一般回帰fixtureを追加。
- GPQA/gold固有分岐は追加していない。

### 通常CI

GitHub Actions `MINIDORA 再構築CI`:

- Ubuntu / Windows × Python 3.11–3.14
- 8 / 8 job PASS
- repository consistency / compileall / unittest / CLI smoke PASS

### GPQA Diamond実測

run: `32618022541`

```text
correct: 19 / 198 = 9.5959596%
answered: 113 / 198 = 57.0707071%
answered accuracy: 19 / 113 = 16.8141593%
suspended: 85
retrieval empty: 0
data compile failed: 0
```

この値は旧v0.6系の31/198を下回る。ただし旧31/198は別code head / 別Compiler時点であり、Attempt 1の因果効果だけを示す比較ではない。

## Attempt 1の扱い

Attempt 1のRuntime変更と追加fixtureは**revert済み**。mainへ採用しない。

理由:

1. 現行main無改修baselineが未測定で、19/198の低下を変更だけへ帰属できない。
2. 少なくとも絶対性能として採用を正当化する改善値は出ていない。
3. 次の改修前に、現行mainの同一ベンチ・同一runner経路でbaselineを固定する必要がある。

## 現行main baseline再測定

現在のPR差分からRuntime変更を外し、`.github/workflows/gpqa_current_measure.yml` のPR自動測定経路だけを残して、現行main RuntimeそのものをGPQA Diamond 198問で再測定する。

この値をv0.7開発の比較基準とし、以後は同じcurrent-main系コードから一変更ずつ測る。

## 評価規則

- 単なる回答率増加を性能改善としない。
- correct / answered accuracy / SUSPEND / candidate diagnosticsを併記する。
- GPQA問題番号・gold・正答ラベル・設問固有文字列による分岐は禁止。
- `NO_GUESS` / `SUSPEND` 境界を点数目的で緩めない。
- 悪化した変更はmainへ統合しない。
