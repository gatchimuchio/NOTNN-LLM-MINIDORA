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
