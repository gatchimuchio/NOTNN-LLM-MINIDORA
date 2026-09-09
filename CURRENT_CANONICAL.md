# MINIDORA 現行正本

## 状態

```text
Core canonical baseline: MINIDORA30
System capability canonical: MINIDORA80
Date: 2026-09-09
Development state: ACTIVE
GPQA canonical benchmark: LIVE_ONLY
GPQA fixed reference Data: FORBIDDEN
```

現行MINIDORAは、Core性能とModule込みシステム能力を分離して二層正本として保持する。

```text
Core正本               = MINIDORA30
Module込みシステム正本 = MINIDORA80
```

## 1. Core正本 — MINIDORA30

| 指標 | 正本値 |
|---|---:|
| GPQA Diamond E2E LIVE | **30 / 198 (15.15%)** |
| 同run controlled baseline | 27 / 198 (13.64%) |
| current - baseline | +3問 / +1.52pt |
| 回答数 | 130 / 198 |
| SUSPEND | 68 / 198 |
| 改善 / 退行 | 3 / 0 |

正本表記:

```text
MINIDORA30 / GPQA-E2E-LIVE / 30/198 / 15.151515151515152%
```

実測由来:

- 主要実装commit: `b70344677c3a761af3e3bfac57b1fe92980b6f0e`
- 実測対象実装親commit: `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- benchmark workflow commit: `63603f39d62bd77ae40732f6c51701aaab9fe468`
- GitHub Actions run: `34281226412`
- aggregate artifact: `10078256754`
- artifact SHA256: `0c7ef2b4a474bf5cd6ee55d5ca170480292186babbc7d559afb268c347ede83c`
- GPQA CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

詳細:

- [MINIDORA30 GPQA E2E正本](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [MINIDORA30 manifest](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [MINIDORA30 Savepoint](docs/SAVEPOINT_2026-09-09_MINIDORA30.md)

## 2. Module込みシステム能力正本 — MINIDORA80

2026-09-09、同一の現行Coreへ既存科学Capability Module群を接続し、固定参照Dataを使わないLIVE E2E同一run controlled A/BをGPQA Diamond 198問全数で実行した。

| 指標 | Module OFF | Module ON |
|---|---:|---:|
| 正答 | 29 / 198 | **80 / 198** |
| 正答率 | 14.65% | **40.40%** |
| 回答数 | 123 | 148 |
| SUSPEND | 75 | 50 |

```text
正答純増   = +51
正答率差   = +25.76pt
Module発火 = 55
発火正答   = 55 / 55
改善       = 51
退行       = 0
changed    = 51
```

正本表記:

```text
MINIDORA80 / GPQA-E2E-LIVE + SCIENTIFIC-CAPABILITY-MODULE / 80/198 / 40.4040404040404%
```

この結果はCore単体性能ではない。**成立済みCoreへ独立Capabilityを追加することで、Core再学習なしにシステム実効能力を増設できることの現行LIVE正本**である。

実測由来:

- measured implementation content: main `55463b40df987fc77b36bd4ce69cc6858dcf43bc` と同一（benchmark workflow追加のみ）
- benchmark head: `562f6c915eff4a1da863153b3f8be63e888139ca`
- GitHub Actions run: `34301888230`
- aggregate artifact: `10085678050`
- artifact SHA256: `819633bd8a102e4687fcdf23e82e75ca076481eed9eb77d6f00af108ce08aebc`
- GPQA CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`
- reference: `LIVE_ONLY`
- OpenAlex: disabled
- Wikipedia: en
- choice seed: 0
- fixed reference Data: forbidden

詳細:

- [MINIDORA80 Module E2E正本](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [MINIDORA80 manifest](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json)
- [MINIDORA80 Savepoint](docs/SAVEPOINT_2026-09-09_MINIDORA80.md)

## 3. GPT-4比較の正本表現

GPQA原論文は、当時の最強GPT-4ベースラインを **39%** と報告している。

MINIDORA80はGPQA Diamondで **40.40%** を実測した。

したがって正本では次の表現を許可する。

> **GPQAスコアという限定した観測軸では、MINIDORA + 科学Capability ModuleはGPT-4ベースラインと同じ約40%帯の水準に到達した。**

数値上は `40.40% > 39%` である。

ただし、原論文GPT-4値と今回のGPQA Diamond LIVE E2Eはsubset・参照条件・実行方式が完全同一ではない。よって次は主張しない。

```text
MINIDORA80のGPQA 40.40%
!= GPT-4との厳密な同条件勝敗
!= GPT-4との総合能力同等
!= GPT-4級一般チャット性能の完成認定
```

比較根拠: https://arxiv.org/abs/2311.12022

## 4. GPQA正本運用

2026-09-09のユーザー明示指示により、**以後GPQAでは固定参照Dataを禁止する。**

禁止対象:

```text
固定C2
保存済み検索結果
問題別Reference/Data bundle
Replay fixture
過去run参照の再投入
```

Core正本・Module込みシステム正本のいずれも、公式GPQA Diamond 198問へ実行時に参照を新規取得するLIVE E2Eで測る。

正本条件:

```text
198 / 198 全数
choice seed = 0
OpenAlex = disabled
Wikipedia = en
reference = LIVE_ONLY
fixed reference Data = forbidden
```

Module効果は同一runでModule OFF / ONへ同一取得資料を共有したcontrolled A/B差を直接差分として扱う。

異なる日時のLIVE run得点差は時系列スナップショットであり、コード変更だけの純粋因果差とは扱わない。

## 5. 過去Replay

- Core37 C2 replay: 37 / 198
- 科学Capability Module replay: 63 / 198

は履歴証拠として保持するが、現行GPQA正本性能ではない。固定参照Dataを将来のGPQA正本性能比較へ再利用しない。

## 6. 局所解釈起点

2026-09-09に再開した局所解釈起点は現行MINIDORAへ実装済みである。

```text
現在の局所解釈 S_t
+ 現在入力
→ 解釈 / 計画 / 判断 / 実行
→ 結果
→ S_t+1
```

これは同一Runtime寿命の局所意思決定連続性であり、永続人格・端末間同期・長期主体記憶をLLMへ追加するものではない。長期保持はAgent / AGI等の上位主体の責任として分離する。

- [局所解釈起点契約](設計/36_MINIDORA_局所解釈起点_v1.md)

## 7. 正本置換条件

Core正本またはModule込みシステム正本を置換する場合は、固定参照Data禁止を維持したLIVE_ONLY GPQA Diamond 198/198全数実測と、dataset hash・seed・provider条件・artifact・runを保存する。
