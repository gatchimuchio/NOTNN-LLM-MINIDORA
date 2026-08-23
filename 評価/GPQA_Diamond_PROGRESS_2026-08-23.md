# MINIDORA GPQA Diamond 性能変遷記録 — 2026-08-23

## 目的

MINIDORAのGPQA Diamond実測値を、過去ログを上書きせず時系列で固定する。

この文書は**開発変遷の索引**であり、条件が異なる測定値を同一条件の性能曲線として扱わない。

## 今回の実測 — v0.6系

2026-08-23、GitHub ActionsのGPQA測定workflowを再実行し、GPQA Diamond 198問を完走した。

```text
workflow run id: 32582547752
workflow job id: 97131890431
artifact id: 9486518870
workflow head branch: chappie/perf-brushup-v0-6
workflow head sha: 28d25cd57728b3765c8d0586e970410736d33eef
rerun checkout merge sha: 5d82f055727f102f046da784ce9e556816e0ddf8
result: SUCCESS
```

注意: この測定はv0.6 PR文脈の再実行である。測定後にmainは `edc48556f922b93e56da4a19cd8e27599f58af85` まで進んでいるため、**31/198を後続main HEADのスコアとは扱わない**。

### 主要指標

| 指標 | 実測 |
|---|---:|
| 正答 | 31 / 198 |
| 総合正答率 | 15.6565657% |
| 回答 | 128 / 198 |
| 回答率 | 64.6464646% |
| 誤答 | 97 |
| SUSPEND | 70 |
| 回答した問題のみの正答率 | 24.21875% |
| retrieval empty | 0 |
| 取得文書 | 2,934 |
| Data compile | 2,934 |
| Data compile failure | 0 |
| K facts added | 323,611 |
| evidence facts | 370,570 |
| blocked evidence facts | 0 |

### 参照源

- Crossref: 1,583
- Europe PMC: 1,334
- Wikipedia:en: 17
- OpenAlex: 無効

### 判断理由集計

- `AMBIGUOUS_EVIDENCE`: 53
- `AUTHORITY_SEPARATED`: 128
- `EVIDENCE_PRESENT`: 128
- `EXCEPTION_NOT_RESOLVED`: 6
- `NO_GUESS`: 70
- `NO_KNOWLEDGE_EVIDENCE`: 11
- `RUBRIC_PASS`: 128

## GPQA Diamondの変遷

| 時点 | 状態 | 正答 | 正答率 | 回答 | SUSPEND | 扱い |
|---|---|---:|---:|---:|---:|---|
| 2026-08-22 | 初期診断 | 5 / 198 | 2.5253% | - | - | **無効診断**。raw retrieved Dataが必要なHDS経路を通らずKへ入っていた |
| 2026-08-22 | Prototype completion baseline | 8 / 198 | 4.0404% | 27 | 171 | **固定baseline**。上書き禁止 |
| 2026-08-22 | v0.5開発途中実測 | 17 / 198 | 8.5859% | - | - | **開発途中参照値**。正式baselineではない |
| 2026-08-23 | v0.6系今回実測 | 31 / 198 | 15.6566% | 128 | 70 | **Workflow完走実測** |

数値上の変化は次の通り。

- Prototype baseline 8 → v0.6実測31: `+23問`, `+11.6162pt`, 正答数3.875倍
- v0.5途中17 → v0.6実測31: `+14問`, `+7.0707pt`
- Prototype baselineの回答数27 → v0.6実測128: `+101問`
- Prototype baselineのSUSPEND 171 → v0.6実測70: `-101問`

ただし、prototype baselineは後続測定と完全に同一の実行可能Compiler/configurationではない。したがって上記は**開発履歴上の変化量**であり、統制された同条件比較の改善量ではない。

## 現時点の診断

今回の実測では、R取得とDataコンパイルは安定した。

```text
retrieval empty = 0
Data compile failure = 0
```

一方、回答した128問中31正答で、回答時正答率は24.21875%だった。GPQA Diamondは4択であり、単純な一様選択の基準25%に近い。

この観測だけから統計的な同値性を断定しないが、**現行v0.6系では候補識別・証拠差分・Jへの接続が主要ボトルネック候補**と扱う。

SUSPEND境界を緩めて全問回答することを改善とは扱わない。次の性能改善は、取得済み証拠から候補間差分を正しく形成する能力で評価する。

## Kimi K3参照

既存評価記録でKimi K3のGPQA Diamond参照値は **93.5%** としている。

これは比較目標の参照値であり、MINIDORA今回実測とはtool条件・実行構成が同一ではないため、厳密な直接比較値として扱わない。

## 保存物

- `GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json` — prototype完成時の不変baseline
- `PERFORMANCE_V0_5_WORKLOG_2026-08-22.md` — v0.5開発履歴
- `PERFORMANCE_V0_6_WORKLOG_2026-08-23.md` — v0.6実装・runner開始前failure時点の履歴
- `GPQA_Diamond_V0_6_MEASUREMENT_2026-08-23.summary.json` — 今回の機械可読実測サマリ
- 本文書 — GPQA性能変遷の索引

GitHub Actions artifact `9486518870` には今回の元の `gpqa_current_measurement.json` が保存されている。サマリJSONにはartifact ID・digest・workflow/run/head SHAを固定し、元実測との対応を追跡できるようにする。

## 履歴保全規則

1. Prototype completion baselineは上書きしない。
2. 新しい実測は新規日付ファイルとして追加する。
3. 開発途中値・無効診断・正式実測を混同しない。
4. 異なるCompiler/configuration間は「変遷」として記録し、同条件比較と称さない。
5. workflow run / head SHA / artifact digestを残し、後から測定対象を再同定できるようにする。
