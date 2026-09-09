# MINIDORA80 Savepoint — 2026-09-09

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
