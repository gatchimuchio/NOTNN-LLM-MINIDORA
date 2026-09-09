# GPQA Diamond MINIDORA80 Module E2E 正本 — 2026-09-09

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
