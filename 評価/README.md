# 評価

`評価/` は、MINIDORAの適合・性能・回帰・完成判定に関する**実測記録**を保持する。

設計そのものは `../設計/`、Runtime実装は `../src/minidora/` を参照する。

## 現在の固定状態

2026-08-22時点で、MINIDORAは **PROTOTYPE COMPLETE** と判定されている。

これは非ニューラル／非Transformer経路が閉じ、外部未知ベンチで非ゼロの正答能力を実測した**プロトタイプ段階の完成**を意味する。製品版・最終完成やK3級性能の達成を意味しない。

正本:

- [`PROTOTYPE_COMPLETION_2026-08-22.md`](PROTOTYPE_COMPLETION_2026-08-22.md) — 完成判定、成立条件、解釈境界。
- [`GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json`](GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json) — 機械可読な固定baseline。

このbaselineは履歴固定値であり、将来の改善値で上書きしない。

`2026-08-20/`、`2026-08-21/` 等の日付ディレクトリは、完成前を含む診断・比較・回帰履歴として保持する。

## GPQA Diamond 性能変遷

GPQA関連の時系列索引は [`GPQA_Diamond_PROGRESS_2026-08-23.md`](GPQA_Diamond_PROGRESS_2026-08-23.md) を正本とする。

現在記録されている変遷:

| 時点 | 区分 | 正答 | 正答率 | 扱い |
|---|---|---:|---:|---|
| 2026-08-22 | 初期診断 | 5 / 198 | 2.5253% | 無効診断 |
| 2026-08-22 | Prototype baseline | 8 / 198 | 4.0404% | 不変baseline |
| 2026-08-22 | v0.5開発途中 | 17 / 198 | 8.5859% | 途中参照値 |
| 2026-08-23 | v0.6系workflow実測 | 31 / 198 | 15.6566% | 完走実測 |

今回のv0.6系実測:

- [`GPQA_Diamond_V0_6_MEASUREMENT_2026-08-23.summary.json`](GPQA_Diamond_V0_6_MEASUREMENT_2026-08-23.summary.json) — workflow/run/head SHA、主要metrics、履歴境界を含む機械可読サマリ。
- GitHub Actions artifact `9486518870` — 元の `gpqa_current_measurement.json`。
- workflow run id `32582547752` / job id `97131890431`。
- v0.6 head `28d25cd57728b3765c8d0586e970410736d33eef`。再実行checkoutはPR merge commit `5d82f055727f102f046da784ce9e556816e0ddf8`。

この実測は後続main HEADの値ではない。測定後にmainはHDS Compiler Architecture v1.2へ進んでいるため、新しいHEADのスコアは別実測として追加する。

過去作業ログ:

- [`PERFORMANCE_V0_5_WORKLOG_2026-08-22.md`](PERFORMANCE_V0_5_WORKLOG_2026-08-22.md)
- [`PERFORMANCE_V0_6_WORKLOG_2026-08-23.md`](PERFORMANCE_V0_6_WORKLOG_2026-08-23.md)

異なるCompiler/configuration間の値は**開発変遷**として記録し、統制された同条件比較とは称さない。

## 標準評価状態

標準状態は外部参照Rを有効にしたMINIDORAである。

Reference OFFは標準能力ではなくablationとして別記録する。

## 評価軸

- 推論
- 知識
- 命令追従
- 長文脈
- code
- agentic長期実行
- 未知停止
- 矛盾停止
- 主体的一貫性
- 理由付き自己訂正
- latency / memory / cost
- 日本語命令と英語互換表現の記号量

K3等との比較は同一prompt / dataset / judge / tool条件で行う。

## 状態の区別

```text
PROTOTYPE COMPLETE
!= 製品・最終完成
!= K3級性能
!= 将来スケーリング上限の確定
```

製品・最終完成の関門は [`../設計/05_完成判定関門.md`](../設計/05_完成判定関門.md) を参照する。
