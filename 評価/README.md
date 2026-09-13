# 評価

`評価/` はMINIDORAの適合・性能・回帰・完成判定の実測記録を保持する。

## 現行正本 — MINIDORA30 / 2026-09-09

現行GPQA Diamond性能正本は次とする。

```text
MINIDORA30
GPQA-E2E-LIVE
30 / 198
15.151515151515152%
```

実測由来:

- GitHub Actions run `34281226412`
- benchmark head `63603f39d62bd77ae40732f6c51701aaab9fe468`
- measured implementation parent `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- aggregate artifact `10078256754`
- dataset CSV SHA256 `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

| 条件 | 正答 | 全体正答率 | 回答数 | 回答率 |
|---|---:|---:|---:|---:|
| 現行MINIDORA | **30 / 198** | **15.15%** | 130 | 65.66% |
| 同run controlled baseline | 27 / 198 | 13.64% | 109 | 55.05% |

```text
正答差       = +3
正答率差     = +1.52 points
changed      = 21
改善case     = 3
退行case     = 0
```

正本:

- [`GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md`](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [`GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json`](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [`BENCHMARK_CONTRACT_v2.md`](BENCHMARK_CONTRACT_v2.md)
- [`../docs/SAVEPOINT_2026-09-09_MINIDORA30.md`](../docs/SAVEPOINT_2026-09-09_MINIDORA30.md)

2026-09-09以後、**GPQA正本性能評価では固定参照Dataを禁止する。** C2、保存済み検索結果、固定Reference/Data bundle、Replay fixture、過去run参照の再投入は現行性能・将来正本・GPQA性能比較の入力へ使わない。

GPQA正本は198/198全数・seed 0・OpenAlex disabled・Wikipedia en・LIVE_ONLY・controlled A/Bで実行する。

## 現行Module込みシステム正本 — MINIDORA80 / 2026-09-09

現行Module込みGPQA Diamondシステム能力正本は **MINIDORA80** とする。Core正本MINIDORA30は置換せず、評価層を分離して併存させる。

```text
MINIDORA80
GPQA-E2E-LIVE + SCIENTIFIC-CAPABILITY-MODULE
80 / 198
40.4040404040404%
```

同一run controlled A/B:

| 条件 | 正答 | 正答率 | 回答数 | SUSPEND |
|---|---:|---:|---:|---:|
| Module OFF | 29 / 198 | 14.65% | 123 | 75 |
| Module ON | **80 / 198** | **40.40%** | 148 | 50 |

```text
正答純増   = +51
正答率差   = +25.76 points
Module発火 = 55
発火正答   = 55 / 55
改善       = 51
退行       = 0
changed    = 51
```

実測は固定参照Dataを使わず、198/198全数、seed 0、OpenAlex disabled、Wikipedia en、LIVE_ONLYで実行した。

実行証拠:

- GitHub Actions run `34301888230`
- benchmark head `562f6c915eff4a1da863153b3f8be63e888139ca`
- measured implementation content `55463b40df987fc77b36bd4ce69cc6858dcf43bc`
- aggregate artifact `10085678050`
- artifact SHA256 `819633bd8a102e4687fcdf23e82e75ca076481eed9eb77d6f00af108ce08aebc`
- dataset CSV SHA256 `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

GPQA原論文の最強GPT-4ベースラインは39%である。MINIDORA80の40.40%は、**GPQAスコアという限定軸ではGPT-4ベースラインと同じ約40%帯**に位置する。評価subset・実行条件が完全同一ではないため、GPT-4との総合能力同等とは扱わない。

正本:

- [`GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md`](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [`GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json`](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json)
- [`../docs/SAVEPOINT_2026-09-09_MINIDORA80.md`](../docs/SAVEPOINT_2026-09-09_MINIDORA80.md)

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

これがこの履歴系列の主要成果である。

正本履歴:

- [`MINIDORA_モジュール拡張成立実証_2026-09-02.md`](MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [`GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md`](GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)
- [`GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.summary.json`](GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.summary.json)

このReplay実証は履歴証拠として保持するが、2026-09-09以後のGPQA現行性能測定へ固定参照Dataを再利用しない。

## 旧セーブポイント — 2026-09-01

旧能力観測:

- [`GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)
- [`MINIDORA_v0_5_厳密LM受入_2026-08-28.md`](MINIDORA_v0_5_厳密LM受入_2026-08-28.md)

当時のGPQA:

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

この値は当時の汎用core現在地として履歴保持する。現行正本はMINIDORA30である。

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
| 2026-09-01 最小汎用core + HDS | 23 / 198 | 旧savepoint |
| 2026-09-02 Module OFF replay | 8 / 198 | 履歴モジュール拡張実証対照 |
| 2026-09-02 Module ON replay | 63 / 198 | 履歴モジュール拡張成立証拠 |
| 2026-09-08 Core37 C2 replay | 37 / 198 | 履歴固定Replay。現行性能ではない |
| 2026-09-09 MINIDORA30 E2E LIVE | **30 / 198** | **現行Core正本** |
| 2026-09-09 Module OFF E2E LIVE | 29 / 198 | MINIDORA80同run対照 |
| 2026-09-09 MINIDORA80 Module ON E2E LIVE | **80 / 198** | **現行Module込みシステム正本** |

専門領域solver接続版の高得点は、現行汎用coreの比較系列へ混ぜない。

過去Replay差分自体は当時の構造実証として保持する。ただし今後のGPQA性能測定では固定参照Dataを禁止する。

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
!= 2026-09-08 Core37 Replay履歴
!= 2026-09-09 MINIDORA30 Core正本
!= 2026-09-09 MINIDORA80 Module込みシステム正本
!= 推論能力
!= Large
!= 現代LLM呼称適合
!= 製品完成
```

## 第25バッチの開発検証

[通常入口・意味接続の検証](通常入口意味接続_第25バッチ_検証_2026-09-13.md) と [変更前後の開発診断](第25バッチ_開発診断.json)。既存GPQA正本値の置換ではない。
