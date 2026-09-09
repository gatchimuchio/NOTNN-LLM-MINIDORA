from __future__ import annotations

from pathlib import Path
import json


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, got {count}")
    return text.replace(old, new, 1)


readme = Path("README.md")
text = readme.read_text(encoding="utf-8")
anchor = "Windowsで開発する場合は [Windowsネイティブ開発環境](docs/Windows開発環境.md) を参照してください。\n"
current = """

## 現行GPQA正本 — Core 30 / Module込み80

2026-09-09以後、GPQAの正本性能評価では**固定参照Dataを禁止**し、実行時に新規取得する `LIVE_ONLY` 参照だけを使う。

| 評価層 | 正本名 | GPQA Diamond | 意味 |
|---|---|---:|---|
| Core / HDS | **MINIDORA30** | **30 / 198 (15.15%)** | 現行Core汎用E2E性能セーブポイント |
| Core + 科学Capability Module | **MINIDORA80** | **80 / 198 (40.40%)** | 現行Module込みシステム能力セーブポイント |

MINIDORA80は、同一run・同一LIVE参照を使うModule OFF / ON controlled A/Bで次を確認した。

```text
Module OFF = 29 / 198  (14.65%)
Module ON  = 80 / 198  (40.40%)
正答純増   = +51
Module発火 = 55
発火55件の正答 = 55
改善       = 51
退行       = 0
```

4択一様ランダム期待値25%を超え、Module追加が実効能力の追加としてLIVE E2Eでも成立した。

> **GPQAスコアという限定した観測軸では、MINIDORA + 科学Capability Moduleは、GPQA原論文の最強GPT-4ベースライン（39%）と同じ約40%帯の水準に到達した。**

MINIDORA80は40.40%であり数値上39%を上回る。ただし、原論文GPT-4値と今回のGPQA Diamond LIVE E2Eはsubset・参照条件・実行方式が完全同一ではないため、これは**GPQAスコア帯の比較**であり、GPT-4との総合能力同等を意味しない。

- [MINIDORA80 Module E2E正本](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [MINIDORA80機械可読manifest](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json)
- [現行正本](CURRENT_CANONICAL.md)
"""
text = replace_once(text, anchor, anchor + current, "README current insertion")

old = """2026-09-02のcontrolled replayでは、リポジトリ内に既に存在していた科学専門能力群を明示接続し、新しいGPQA解法器・gold参照solver・問題番号分岐を追加せず、次を観測しました。

| 条件 | 正答 | 全体正答率 | 回答時正答率 |
|---|---:|---:|---:|
| Module OFF | 8 / 198 | 4.04% | 20.51% |
| Module ON | **63 / 198** | **31.82%** | **73.26%** |

```text
Module発火 = 55
改善       = 55
退行       = 0
正答差     = +55
```

このReplay境界では、Moduleが発火した55問は55問すべてgoldと一致し、Module不発火問題には新しい差を作っていません。

したがって、この実験の中心的な意味は **31.82%という絶対スコアではありません。**
"""
new = """2026-09-09、固定参照Dataを禁止した現行運用で、既存科学専門能力群を明示接続し、新しいGPQA解法器・gold参照solver・問題番号分岐を追加せず、LIVE参照の同一run controlled A/Bを198問全数で実行しました。

| 条件 | 正答 | 全体正答率 | 回答数 |
|---|---:|---:|---:|
| Module OFF | 29 / 198 | 14.65% | 123 |
| Module ON | **80 / 198** | **40.40%** | 148 |

```text
Module発火 = 55
発火正答   = 55
改善       = 51
退行       = 0
正答差     = +51
```

Module発火55件は55件すべて正答し、51件でbaselineの非正答を正答へ変えた。残る4件はbaselineも既に同じ正答であり、既存正答を壊していない。

2026-09-02の固定Replay `8/198 → 63/198` は、モジュール拡張成立を最初に確認した履歴証拠として保持する。現行のModule込みシステム能力正本は、固定参照Dataを使わない **MINIDORA80 = 80/198** である。

したがって、この実験の中心的な意味は **40.40%という絶対スコアだけではありません。**
"""
text = replace_once(text, old, new, "README module evidence")
text = text.replace(
    "| **GPT-4級性能の宣言** | 現時点でフロンティアLLMと同等の総合性能を主張していない |",
    "| **GPT-4総合性能同等の宣言** | GPQAスコアではGPT-4原論文baselineと同じ約40%帯に到達したが、総合能力同等は主張しない |",
)
old_core = """### Core汎用能力

専門solverをactive pathから外した2026-09-01 GPQA Diamond全198問:

```text
正式MINIDORA汎用模型核 / HDS非介入 = 19 / 198  (9.60%)
最小汎用Core + HDS異常時最小介入  = 23 / 198 (11.62%)
```

この値は現行Core能力の観測であり、MINIDORAがGPT-4等のフロンティアモデルと同等性能であることを示しません。

### Module込みシステム能力

科学専門能力Moduleを接続したcontrolled replayでは、Module OFF 8/198からON 63/198へ変化し、55発火・55改善・0退行を観測しました。

この値はCore単体性能ではなく、**同一Coreへ外部Capabilityを追加したシステム能力差**です。
"""
new_core = """### Core汎用能力

現行Core正本は **MINIDORA30** です。

```text
GPQA Diamond E2E LIVE = 30 / 198 (15.15%)
固定参照Data = 禁止
```

### Module込みシステム能力

現行Module込みシステム能力正本は **MINIDORA80** です。

```text
同一run Module OFF = 29 / 198 (14.65%)
Module ON          = 80 / 198 (40.40%)
純増               = +51
Module発火         = 55
発火正答           = 55
退行               = 0
```

この値はCore単体性能ではなく、**成立済みCoreへ外部Capabilityを追加したシステム能力**です。GPQAスコア帯では原論文GPT-4ベースライン39%と同じ約40%帯に到達していますが、GPT-4との総合性能同等を意味しません。
"""
text = replace_once(text, old_core, new_core, "README current capability")
text = text.replace("!= GPT-4級性能到達\n", "GPQAでGPT-4ベースライン同水準帯\n!= GPT-4総合能力同等\n")
readme.write_text(text, encoding="utf-8")

en = Path("README.en.md")
text = en.read_text(encoding="utf-8")
anchor_en = "> This file is an English translation for international access. The Japanese documents are the normative source of meaning and design.\n"
current_en = """

## Current GPQA canon — Core 30 / System with Modules 80

Since 2026-09-09, canonical GPQA performance runs forbid frozen reference data and use newly retrieved `LIVE_ONLY` references.

| Layer | Canon | GPQA Diamond | Meaning |
|---|---|---:|---|
| Core / HDS | **MINIDORA30** | **30 / 198 (15.15%)** | current general E2E Core savepoint |
| Core + scientific Capability Modules | **MINIDORA80** | **80 / 198 (40.40%)** | current system-capability savepoint |

In the same-run LIVE controlled A/B that established MINIDORA80:

```text
Module OFF = 29 / 198 (14.65%)
Module ON  = 80 / 198 (40.40%)
net correct gain = +51
Module activations = 55
correct Module activations = 55
improvements = 51
regressions = 0
```

> **On the limited axis of GPQA score, MINIDORA + scientific Capability Modules reached the same roughly-40% score range as the strongest GPT-4-based baseline reported by the original GPQA paper (39%).**

MINIDORA80 is numerically above 39%, but the original GPT-4 result and this GPQA Diamond LIVE E2E run do not use identical subsets or execution conditions. This is therefore a **same-score-band statement, not a claim of overall GPT-4 capability equivalence**.
"""
text = replace_once(text, anchor_en, anchor_en + current_en, "README.en current insertion")
old_en = """The prior GPQA Diamond controlled replay measured a Module OFF → ON change from **8/198 to 63/198**, with 55 Module activations, 55 improvements, and 0 regressions. This is **not claimed as Core-only performance**; it is evidence that external capability Modules can create measurable system-level capability gains.
"""
new_en = """The current LIVE GPQA Diamond same-run controlled A/B measured Module OFF **29/198 (14.65%)** → Module ON **80/198 (40.40%)**, with 55 Module activations, 55 correct activations, 51 net improvements, and 0 regressions. The earlier 8/198 → 63/198 frozen replay remains historical evidence only. This is **not claimed as Core-only performance**; it is evidence that external capability Modules can create measurable system-level capability gains without retraining the established Core.
"""
text = replace_once(text, old_en, new_en, "README.en module evidence")
text = text.replace(
    "A **GPT-4-class general chat experience** is a development target, not a current equivalence claim.",
    "A **GPT-4-class general chat experience** remains a development target. MINIDORA80 has reached the same roughly-40% GPQA score band as the original GPT-4-based baseline, but this is not a general capability equivalence claim.",
)
text = text.replace(
    "Current Core GPQA observation with specialist solvers excluded from the active path:\n\n```text\nFormal MINIDORA general Core / HDS off = 19 / 198  (9.60%)\nMinimal general Core + HDS supervision = 23 / 198 (11.62%)\n```",
    "Current canonical GPQA savepoints:\n\n```text\nMINIDORA30 Core E2E LIVE              = 30 / 198 (15.15%)\nMINIDORA80 Core + scientific Modules  = 80 / 198 (40.40%)\n```",
)
text = text.replace(
    "!= GPT-4-class performance achieved",
    "GPQA same score band as GPT-4 baseline\n!= overall GPT-4 capability equivalence",
)
en.write_text(text, encoding="utf-8")

canonical = """# MINIDORA 現行正本

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
"""
Path("CURRENT_CANONICAL.md").write_text(canonical, encoding="utf-8")

evaluation = Path("評価/README.md")
text = evaluation.read_text(encoding="utf-8")
marker = "## 主要成立証拠 — モジュール拡張可能性\n"
module_section = """## 現行Module込みシステム正本 — MINIDORA80 / 2026-09-09

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

"""
text = replace_once(text, marker, module_section + marker, "evaluation insert")
text = text.replace(
    "| 2026-09-09 MINIDORA30 E2E LIVE | **30 / 198** | **現行正本** |",
    "| 2026-09-09 MINIDORA30 E2E LIVE | **30 / 198** | **現行Core正本** |\n| 2026-09-09 Module OFF E2E LIVE | 29 / 198 | MINIDORA80同run対照 |\n| 2026-09-09 MINIDORA80 Module ON E2E LIVE | **80 / 198** | **現行Module込みシステム正本** |",
)
text = text.replace(
    "!= 2026-09-09 MINIDORA30現行正本\n",
    "!= 2026-09-09 MINIDORA30 Core正本\n!= 2026-09-09 MINIDORA80 Module込みシステム正本\n",
)
evaluation.write_text(text, encoding="utf-8")

design = Path("設計/35_MINIDORA_能力Module拡張境界_v1.md")
text = design.read_text(encoding="utf-8")
marker = "### 実測\n"
live = """### 2026-09-09 LIVE正本実測

固定参照Data禁止後、同一現行Coreへ既存科学Capability Module群を接続し、GPQA Diamond 198問をLIVE_ONLY同一run controlled A/Bで再実測した。

```text
Module OFF = 29 / 198  (14.65%)
Module ON  = 80 / 198  (40.40%)
Module発火 = 55
発火正答   = 55 / 55
改善       = 51
退行       = 0
正答差     = +51
```

55発火は全件正答した。51件はbaselineの非正答を正答へ変え、残る4件はbaselineも既に同じ正答であった。したがって既存正答の退行は0である。

このLIVE実測によって、固定Replayに依存せず、**実行時に新規取得する参照環境でもCapability Module追加が実効能力増加として成立する**ことを確認した。

現行Module込みシステム能力正本は **MINIDORA80 = 80/198 (40.40%)** とする。

GPQA原論文の最強GPT-4ベースライン39%との関係は、**GPQAスコア帯では同じ約40%帯**である。ただし評価条件が完全同一ではないため、GPT-4総合能力同等とは解釈しない。

### 2026-09-02 Replay履歴
"""
text = replace_once(text, marker, live, "design live evidence")
old_final = "> **このModule追加は実際の性能向上手段として機能し、GPQA Diamond controlled replayでは8/198から63/198へ上昇、Module発火55、改善55、退行0として実測された。**\n"
new_final = "> **このModule追加は実際の性能向上手段として機能し、現行LIVE E2Eでは29/198から80/198へ上昇、Module発火55、発火正答55、改善51、退行0として実測された。**\n>\n> **2026-09-02の8/198→63/198固定Replayは成立履歴として保持し、現行Module込みシステム能力正本はMINIDORA80 = 80/198 (40.40%)とする。**\n"
text = replace_once(text, old_final, new_final, "design final")
text = text.replace(
    "> **今回の31.82%という数値は成果そのものではない。この能力成長方式が実際に成立していることを示す外部観測証拠である。**",
    "> **今回の40.40%という数値だけが成果なのではない。固定参照Dataを使わないLIVE環境でも、この能力成長方式が実際に成立していることを示す外部観測証拠である。**",
)
design.write_text(text, encoding="utf-8")

contract = Path("評価/BENCHMARK_CONTRACT_v2.md")
text = contract.read_text(encoding="utf-8")
marker = "## 8. 過去Replayの扱い\n"
section = """## 8. Module込みシステム正本 — MINIDORA80

Core正本MINIDORA30とは別に、Module込みシステム能力正本を保持してよい。

現行Module込み正本:

```text
MINIDORA80
GPQA-E2E-LIVE + SCIENTIFIC-CAPABILITY-MODULE
80 / 198
40.4040404040404%
```

成立条件:

```text
198 / 198 全数
choice seed = 0
OpenAlex = disabled
Wikipedia = en
reference = LIVE_ONLY
fixed reference Data = forbidden
Module OFF / ON = same-run controlled A/B
```

Module効果の直接差分は同一runのOFF/ON差だけへ帰属する。MINIDORA80成立runでは `29/198 → 80/198`、正答純増+51、改善51、退行0、Module発火55、発火55件全正答を観測した。

GPQA原論文の最強GPT-4ベースライン39%とMINIDORA80 40.40%は、**GPQAスコア帯として同じ約40%帯**と表現できる。ただしsubset・実行条件が完全同一ではないため、厳密同条件勝敗や総合能力同等は主張しない。

比較根拠: https://arxiv.org/abs/2311.12022

## 9. 過去Replayの扱い
"""
text = replace_once(text, marker, section, "contract module canon")
contract.write_text(text, encoding="utf-8")

md = """# GPQA Diamond MINIDORA80 Module E2E 正本 — 2026-09-09

## 結論

**判定: PASS — MINIDORA80を現行Module込みシステム能力正本として採用する。**

```text
MINIDORA80
GPQA-E2E-LIVE + SCIENTIFIC-CAPABILITY-MODULE
80 / 198
40.4040404040404%
```

Core正本MINIDORA30は置換しない。MINIDORA80は、成立済みCoreへ科学Capability Module群を接続した**システム能力正本**である。

## 実測条件

```text
benchmark            = GPQA Diamond 198問
selected             = 0..197 全数
choice seed          = 0
OpenAlex             = disabled
Wikipedia            = en
reference            = LIVE_ONLY
fixed reference Data = forbidden
A/B                  = same-run Module OFF / ON
```

## 結果

| 指標 | Module OFF | Module ON |
|---|---:|---:|
| 正答 | 29 / 198 | **80 / 198** |
| 正答率 | 14.6465% | **40.4040%** |
| 回答数 | 123 | 148 |
| SUSPEND | 75 | 50 |

```text
正答純増   = +51
正答率差   = +25.7576 points
Module発火 = 55
発火正答   = 55 / 55
改善       = 51
退行       = 0
changed    = 51
```

Module発火55件は55件すべてgoldと一致した。51件はModule OFFで非正答だったケースを正答へ変更した。4件はOFF時点でも既に同じ正答であり、既存正答の退行は0だった。

## 実行証拠

- GitHub Actions run: `34301888230`
- workflow: `MINIDORA sandbox GPQA module LIVE A-B`
- benchmark head: `562f6c915eff4a1da863153b3f8be63e888139ca`
- measured implementation content: `55463b40df987fc77b36bd4ce69cc6858dcf43bc` と同一（benchmark workflowのみ追加）
- aggregate artifact: `10085678050`
- artifact SHA256: `819633bd8a102e4687fcdf23e82e75ca076481eed9eb77d6f00af108ce08aebc`
- dataset CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

## 能力追加の成立判定

今回の観測は次の因果をLIVE E2Eで確認した。

```text
成立済みMINIDORA Core
↓
科学Capability Moduleを追加接続
↓
責任範囲でModule発火
↓
55発火すべて正答
↓
51ケースを新規正答化
↓
既存正答退行0
↓
29/198 → 80/198
```

したがって、**Coreを再学習・再訓練・大型化・置換せず、Capability Module追加によってシステムの実効能力を増設できる**ことを現行LIVE評価でも確認した。

## 4択ランダム期待値

GPQA Diamondは4択であるため、一様ランダム回答の期待正答率は25%。MINIDORA80は40.40%であり、この水準を上回った。

## GPT-4との比較境界

GPQA原論文は、当時の最強GPT-4ベースラインを39%と報告している。

MINIDORA80は40.40%であるため、正本では次を採用する。

> **GPQAスコアという限定した観測軸では、MINIDORA + 科学Capability ModuleはGPT-4ベースラインと同じ約40%帯の水準に到達した。**

数値上は40.40%が39%を上回る。

ただし原論文GPT-4値と今回のGPQA Diamond LIVE E2Eはsubset・参照条件・実行方式が完全同一ではないため、次は主張しない。

- GPT-4との厳密な同条件勝敗
- GPT-4との総合能力同等
- GPT-4級一般チャット性能の完成

比較根拠: https://arxiv.org/abs/2311.12022

## 過去Replayとの関係

2026-09-02の固定Replay `Module OFF 8/198 → ON 63/198` は、Module拡張成立を最初に示した履歴証拠として保持する。

2026-09-09以後は固定参照DataをGPQA正本へ使わない。したがって現行Module込み正本は本書のLIVE E2E `80/198` である。
"""
Path("評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md").write_text(md, encoding="utf-8")

manifest = {
    "schema": "minidora.gpqa.module-e2e-canonical.v1",
    "canonical_name": "MINIDORA80",
    "date_jst": "2026-09-09",
    "benchmark": "GPQA Diamond",
    "evaluation": "LIVE_ONLY same-run controlled A/B; fixed reference data forbidden",
    "dataset_csv_sha256": "41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305",
    "choice_shuffle_seed": 0,
    "openalex_enabled": False,
    "wikipedia_languages": ["en"],
    "fixed_reference_data_allowed": False,
    "module_off": {"correct": 29, "total": 198, "accuracy_percent": 14.646464646464647, "answered": 123, "suspended": 75},
    "module_on": {"correct": 80, "total": 198, "accuracy_percent": 40.4040404040404, "answered": 148, "suspended": 50},
    "delta": {"correct": 51, "accuracy_points": 25.757575757575758, "improved": 51, "regressed": 0, "net": 51, "changed": 51, "fired": 55, "fired_correct": 55},
    "execution_evidence": {
        "workflow_run_id": 34301888230,
        "benchmark_head": "562f6c915eff4a1da863153b3f8be63e888139ca",
        "measured_implementation_content_commit": "55463b40df987fc77b36bd4ce69cc6858dcf43bc",
        "aggregate_artifact_id": 10085678050,
        "aggregate_artifact_sha256": "819633bd8a102e4687fcdf23e82e75ca076481eed9eb77d6f00af108ce08aebc",
    },
    "gpt4_comparison": {
        "source": "https://arxiv.org/abs/2311.12022",
        "reported_strongest_gpt4_based_baseline_percent": 39.0,
        "minidora80_percent": 40.4040404040404,
        "statement": "same roughly-40% GPQA score band; MINIDORA80 is numerically above 39%",
        "boundary": "not a direct identical-setup comparison and not an overall capability-equivalence claim",
    },
    "claim_scope": [
        "scientific Capability Modules add measurable system capability without Core retraining",
        "same-run LIVE A/B attributes +51 net correct cases to Module ON with 0 regressions",
        "GPQA score is in the same roughly-40% band as the original paper GPT-4-based baseline",
    ],
    "forbidden_claims": [
        "MINIDORA80 is Core-only performance",
        "MINIDORA80 and original GPT-4 were measured under identical conditions",
        "MINIDORA80 proves overall GPT-4 capability equivalence",
    ],
}
Path("評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

savepoint = """# MINIDORA80 Savepoint — 2026-09-09

## 正本

```text
Core canonical = MINIDORA30
System capability canonical = MINIDORA80
```

MINIDORA80は、現行MINIDORA Coreへ既存科学Capability Module群を接続したGPQA Diamond LIVE E2Eシステム能力セーブポイントである。

```text
Module OFF = 29 / 198
Module ON  = 80 / 198
正答純増   = +51
Module発火 = 55
発火正答   = 55 / 55
改善       = 51
退行       = 0
```

固定参照Dataは使用していない。198/198全数、seed 0、OpenAlex disabled、Wikipedia en、LIVE_ONLY。

## 意味

このセーブポイントは、成立済みCoreを再学習せず、Capability Moduleを追加することで実効能力を後付けできることをLIVE E2Eで固定したもの。

GPQAスコア帯では原論文GPT-4ベースライン39%と同じ約40%帯に到達した。ただしこれはGPQA限定のスコア帯比較であり、GPT-4総合能力同等を意味しない。

## 実行証拠

- run: `34301888230`
- benchmark head: `562f6c915eff4a1da863153b3f8be63e888139ca`
- aggregate artifact: `10085678050`
- artifact SHA256: `819633bd8a102e4687fcdf23e82e75ca076481eed9eb77d6f00af108ce08aebc`
- dataset CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`
"""
Path("docs/SAVEPOINT_2026-09-09_MINIDORA80.md").write_text(savepoint, encoding="utf-8")

Path(".github/workflows/tmp_canonicalize_minidora80.yml").unlink(missing_ok=True)
Path("tools/tmp_canonicalize_minidora80.py").unlink(missing_ok=True)
