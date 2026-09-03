# 評価

`評価/` はMINIDORAの適合・性能・回帰・完成判定の実測記録を保持する。

## 主要成立証拠 — モジュール拡張可能性

2026-09-02、MINIDORAの**モジュール拡張可能性を実測で確認した**。

この実証の意味は「科学Moduleを付けたらGPQAスコアが上がった」ことではない。

> **MINIDORAは既にLLMとして成立している。その成立済みCoreを再学習・再訓練・大型化せず、Core外に分離した能力Moduleを追加接続することで、システム全体の実効能力と性能を後から拡張できる。**

これを、同一baselineへ既存科学専門能力群を接続するcontrolled replayで確認した。

| 条件 | 正答 | 全体正答率 | 回答時正答率 |
|---|---:|---:|---:|
| Module OFF | 8 / 198 | 4.04% | 20.51% |
| Module ON | **63 / 198** | **31.82%** | **73.26%** |

```text
Module発火  55
改善        55
退行         0
正答差      +55
```

不発火時は保存済みbaselineをそのまま返すため、差分はModuleが実際に作用したケースへ限定される。発火55ケースは、このReplay境界では55ケースすべてgoldと一致した。

したがって、この系列はCore単体のGPQA性能比較ではなく、次の成立証拠として保持する。

```text
MINIDORA成立済み
      ↓
Coreと専門能力を分離可能
      ↓
外部Moduleを後付け可能
      ↓
複数Moduleを累積接続可能
      ↓
Module追加が実際の性能増加を発生
      ↓
Core再学習なしでシステム能力を継続拡張可能
```

### 固定有限ベンチにおける100%到達可能性

GPQA Diamond 100%を実測したわけではない。

しかし、GPQA Diamondは198問の固定有限集合である。今回、その未被覆集合のうち55問を、Coreの再学習なしにModule追加だけで新たに正答可能へ変えた。

未被覆問題へ正しく作用するModuleを追加し、不発火時の透過性と既存正答を退行させない接続境界を維持できる限り、未被覆集合は反復的に縮小できる。

```text
未被覆 U0
↓ Module追加
U1 ⊂ U0
↓ Module追加
U2 ⊂ U1
↓
...
↓
未被覆 = 0
```

したがって、**GPQA Diamondのような固定有限ベンチに限れば、Module被覆を追加し続けることで理論上100%へ到達可能な構成である。**

この主張の価値は「100点を取れる」というベンチ攻略そのものではない。

> **MINIDORAの能力上限が成立済みCoreの初期性能へ固定されず、外部Capability集合の増設によって後から押し上げられることが、実装と実測で示された。**

これが今回の主要成果である。

正本:

- [`MINIDORA_モジュール拡張成立実証_2026-09-02.md`](MINIDORA_モジュール拡張成立実証_2026-09-02.md) — モジュール拡張可能性、反復的能力増設、固定有限ベンチ100%到達経路の成立結論と根拠。
- [`GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md`](GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md) — 詳細測定条件、solver発火、実行証拠。
- [`GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.summary.json`](GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.summary.json) — 固定サマリ。

この成立証拠以後、`Module` は将来構想ではなく**実装・実測済みの能力拡張・性能向上経路**として扱う。

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

ここで区別する。

```text
Core単体性能を測る系列
!=
Module接続による拡張可能性を実証する系列
```

前者では専門solverを外す。後者では、既存Moduleを接続して能力増加がModule由来であることをcontrolled A/Bで確認する。

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
| 2026-09-02 Module OFF replay | 8 / 198 | モジュール拡張実証対照 |
| 2026-09-02 Module ON replay | **63 / 198** | **モジュール拡張成立証拠** |

専門領域solver接続版の高得点は、現行汎用coreの比較系列へ混ぜない。

ただし、**その差分自体は「Core外Moduleを接続して能力を追加できる」という別の成立事実を示すため、主要証拠として保持する。**

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
!= 2026-09-02モジュール拡張成立実証
!= 推論能力
!= Large
!= 現代LLM呼称適合
!= 製品完成
```
