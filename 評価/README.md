# 評価

`評価/` はMINIDORAの適合・性能・回帰・完成判定の実測記録を保持する。

## 現行 v0.5

正本受入:

- [`MINIDORA_v0_5_厳密LM受入_2026-08-28.md`](MINIDORA_v0_5_厳密LM受入_2026-08-28.md) — 上位v7に基づく非ニューラル厳密LM核とRuntime二核分離。

現行区別:

```text
厳密LM成立 != 能力 != GPQA != Large != 現代LLM呼称
```

v0.5のLargeは **再監査要**。v0.4の三面規模 `局所成立候補` を自動継承しない。

## v0.4履歴

次は削除せず履歴として保持する。

- [`MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md`](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md)
- [`計算中間表現_実行境界_v1_受入_2026-08-26.md`](計算中間表現_実行境界_v1_受入_2026-08-26.md)
- [`HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md`](HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md)
- [`MINIDORA_v0_4_規模測定_v2_2026-08-26.md`](MINIDORA_v0_4_規模測定_v2_2026-08-26.md)
- [`GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json`](GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json)

v0.4三面規模測定は当時の上位規定に基づく履歴値であり、v0.5のLarge証拠ではない。

## GPQA履歴

GPQAは推論・知識能力評価として保持し、LM成立判定へ直接投影しない。

代表履歴:

| 時点 | 正答 | 扱い |
|---|---:|---|
| 2026-08-22 prototype baseline | 8 / 198 | 履歴baseline |
| 2026-08-23 v0.6系 | 31 / 198 | 過去workflow |
| 2026-08-26 v0.4再構成 | 19 / 198 | 完走実測 |
| 2026-08-26 再作用P0 | 22 / 198 | 再作用効果には帰属しない |

最新GPQA・構成監査は各日付の評価記録を参照する。

## 状態の区別

```text
v0.3 PROTOTYPE COMPLETE
!= v0.4構造受入
!= v0.5厳密LM受入
!= 推論能力
!= Large
!= 現代LLM呼称適合
!= 製品完成
```
