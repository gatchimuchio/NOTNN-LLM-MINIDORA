# 評価

`評価/` はMINIDORAの適合・性能・回帰・完成判定の実測記録を保持する。

## 現行セーブポイント — 2026-09-01

現行能力観測の正本:

- [`GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md) — 専門solverをactive pathから除外した最小汎用coreのGPQA Diamond全198問controlled A/B。
- [`MINIDORA_v0_5_厳密LM受入_2026-08-28.md`](MINIDORA_v0_5_厳密LM受入_2026-08-28.md) — 非ニューラル厳密言語模型核と実行系二核分離の受入。

現行GPQA:

| 条件 | 正答 | 全体正答率 | 回答数 | 回答率 |
|---|---:|---:|---:|---:|
| 最小汎用core + HDS異常時最小介入 | 23 / 198 | 11.62% | 124 | 62.63% |
| 同一正式汎用模型核 / HDS非介入 | 19 / 198 | 9.60% | 88 | 44.44% |

```text
正答差          = +4
正答率差        = +2.02 points
回答数差        = +36
改善case        = 4
退行case        = 0
専門作用起動    = 0
retrieval空振り = 0
```

この値は**汎用coreの現在地**として保持する。benchmark専用機能を追加して得点を上げることを、MINIDORA本体の汎用能力改善とは扱わない。

## 現行区別

```text
厳密言語模型成立
!= 能力
!= GPQA
!= Large
!= 現代LLM呼称
```

v0.5のLargeは **再監査要**。v0.4の三面規模 `局所成立候補` を自動継承しない。

## HDS境界

2026-09-01の測定では、HDSは未閉包・競合・観測不足等の異常時だけ介入した。

- HDS intervention cases: 108
- HDS supervisory interventions: 483
- `REFERENCE`: 108
- `EXISTING_COMPUTE_EXECUTOR`: 9
- specialist actions: 0

HDSは回答を生成せず、候補winnerを選ばない。

## GPQA履歴

GPQAは推論・知識能力評価として保持し、言語模型成立判定へ直接投影しない。

代表履歴:

| 時点 | 正答 | 扱い |
|---|---:|---|
| 2026-08-22 prototype baseline | 8 / 198 | 履歴baseline |
| 2026-08-23 v0.6系 | 31 / 198 | 過去workflow |
| 2026-08-26 v0.4再構成 | 19 / 198 | 完走実測 |
| 2026-08-26 再作用P0 | 22 / 198 | 再作用効果には帰属しない |
| 2026-08-28 状態差起動current | 16 / 198 | 機構発火PASS・能力退行 |
| 2026-08-28 同run controlled baseline | 22 / 198 | 同一取得資料対照 |
| 2026-09-01 最小汎用core baseline | 19 / 198 | HDS非介入対照 |
| 2026-09-01 最小汎用core + HDS | 23 / 198 | 現行savepoint |

専門領域solver接続版の高得点は履歴として削除しないが、現行汎用coreの比較系列へ混ぜない。

## v0.4履歴

次は削除せず履歴として保持する。

- [`MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md`](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md)
- [`計算中間表現_実行境界_v1_受入_2026-08-26.md`](計算中間表現_実行境界_v1_受入_2026-08-26.md)
- [`HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md`](HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md)
- [`MINIDORA_v0_4_規模測定_v2_2026-08-26.md`](MINIDORA_v0_4_規模測定_v2_2026-08-26.md)
- [`GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json`](GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json)

v0.4三面規模測定は当時の上位規定に基づく履歴値であり、v0.5のLarge証拠ではない。

## 状態の区別

```text
v0.3 PROTOTYPE COMPLETE
!= v0.4構造受入
!= v0.5厳密言語模型受入
!= v0.5能力状態差循環受入
!= 2026-09-01最小汎用core savepoint
!= 推論能力
!= Large
!= 現代LLM呼称適合
!= 製品完成
```
