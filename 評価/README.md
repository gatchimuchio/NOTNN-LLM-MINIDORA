# 評価

`評価/` は、MINIDORAの適合・性能・回帰・完成判定に関する**実測記録**を保持する。

設計そのものは `../設計/`、Runtime実装は `../src/minidora/` を参照する。

## 現在の状態

### MINIDORA v0.4

2026-08-26、上流 **大規模言語模型成立規定 `2026-08-26-成立規定-2`** に基づく構造再構成を受入PASSとした。

正本:

- [`MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md`](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md) — 模型核・計算実行器分離、HDS境界、全CI行列、受入結果。

受入で確認した主な境界:

```text
対象言語状態
→ 言語対応
→ 文脈付き内部状態
→ 再利用可能な模型側関係
→ 成立差
```

旧 `Layer0` 命令器は **計算実行器** へ再分類した。

構造受入CI:

- workflow run id: `32883059625`
- validated head: `89b88f727d289b1f1b66feb609374feeee6130c6`
- Ubuntu / Windows × Python 3.11–3.14: **全8 job PASS**
- 代表job: **329 tests / OK**
- K3相当構造: **47 / 47 PASS**
- CLI: `5です。`

ただし、v0.4の大規模性は**再測定要**である。

```text
v0.4構造受入PASS
!= v0.4大規模性測定完了
!= 製品・最終完成
```

次段はCompute IR / ABIを確定し、その後にHDS semantic IR loweringとHDS Compilerを更新する。

### v0.3プロトタイプ履歴

2026-08-22時点で、旧v0.3系MINIDORAは **PROTOTYPE COMPLETE** と判定されている。

これは非ニューラル／非Transformer経路が閉じ、外部未知ベンチで非ゼロの正答能力を実測した**プロトタイプ段階の完成**を意味する。製品版・最終完成やK3級性能の達成を意味しない。

正本:

- [`PROTOTYPE_COMPLETION_2026-08-22.md`](PROTOTYPE_COMPLETION_2026-08-22.md) — 完成判定、成立条件、解釈境界。
- [`GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json`](GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json) — 機械可読な固定baseline。

このbaselineは履歴固定値であり、将来の改善値で上書きしない。またv0.4模型核の大規模性へ自動転用しない。

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

v0.6系実測:

- [`GPQA_Diamond_V0_6_MEASUREMENT_2026-08-23.summary.json`](GPQA_Diamond_V0_6_MEASUREMENT_2026-08-23.summary.json)
- GitHub Actions artifact `9486518870`
- workflow run id `32582547752` / job id `97131890431`
- v0.6 head `28d25cd57728b3765c8d0586e970410736d33eef`

これらは過去の運用経路に対する履歴実測であり、再構成後v0.4模型核の規模・性能測定とは別記録とする。

過去作業ログ:

- [`PERFORMANCE_V0_5_WORKLOG_2026-08-22.md`](PERFORMANCE_V0_5_WORKLOG_2026-08-22.md)
- [`PERFORMANCE_V0_6_WORKLOG_2026-08-23.md`](PERFORMANCE_V0_6_WORKLOG_2026-08-23.md)

異なるCompiler/configuration間の値は**開発変遷**として記録し、統制された同条件比較とは称さない。

## 標準評価状態

製品統合経路の標準状態は外部参照Rを有効にしたMINIDORAである。

一方、LLM模型核の成立監査では外部参照Rを切った単体試験も必要である。評価目的を明示して混同しない。

## 評価軸

- 言語模型性
- 状態域規模
- 関係域規模
- 共有適用規模
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
PROTOTYPE COMPLETE(v0.3)
!= v0.4構造受入PASS
!= v0.4大規模性測定完了
!= 製品・最終完成
!= K3級性能
!= 将来スケーリング上限の確定
```

製品・最終完成の関門は [`../設計/05_完成判定関門.md`](../設計/05_完成判定関門.md) を参照する。
