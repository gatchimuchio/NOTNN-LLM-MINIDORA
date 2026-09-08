# GPQA Diamond MINIDORA30 E2E 正本 — 2026-09-09

## 結論

**現行MINIDORAのGPQA Diamond汎用E2E性能セーブポイントを `MINIDORA30` として固定する。**

```text
GPQA-E2E-LIVE
30 / 198
15.151515151515152%
```

2026-09-09以後、GPQA正本性能評価では固定参照Dataを使用しない。

## 1. 実測由来

- GitHub Actions run: `34281226412`
- workflow: `MINIDORA GPQA full 198 diff`
- conclusion: `success`
- benchmark head: `63603f39d62bd77ae40732f6c51701aaab9fe468`
- measured implementation parent: `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- 局所解釈起点の主要実装commit: `b70344677c3a761af3e3bfac57b1fe92980b6f0e`
- aggregate artifact ID: `10078256754`
- aggregate artifact SHA256: `0c7ef2b4a474bf5cd6ee55d5ca170480292186babbc7d559afb268c347ede83c`

benchmark headは測定用workflowを追加したcommitであり、MINIDORA実装本体は親commit `a3473fbd...` を測定している。

## 2. GPQA条件

```text
benchmark                 = GPQA Diamond
full total                = 198
selected                  = 0..197
GPQA CSV SHA256           = 41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305
choice shuffle seed       = 0
OpenAlex                  = disabled
Wikipedia                 = en
reference                 = run時LIVE取得
controlled A/B            = enabled
fixed reference Data      = none
```

実行時コマンドは8 shardで次と同等の条件を使用した。

```bash
python tools/benchmark_formal.py gpqa-diamond --controlled-ab --no-openalex ...
```

各shardは同じ公式198問集合の互いに重ならない範囲を処理し、最終集計で `0..197` の198件が一度ずつ揃うことをassertしている。

## 3. 実測結果

| 指標 | Current | 同run controlled baseline | 差 |
|---|---:|---:|---:|
| 正答 | **30 / 198** | 27 / 198 | **+3** |
| 正答率 | **15.15%** | 13.64% | **+1.52pt** |
| 回答数 | **130** | 109 | +21 |
| 回答率 | **65.66%** | 55.05% | +10.61pt |
| SUSPEND | 68 | 89 | -21 |

同run controlled差分:

```text
changed answers = 21
improved cases  = 3
regressed cases = 0
net improved    = +3
```

このcontrolled baselineは同じrunで取得した同じ参照Dataを共有するため、同run内HDS介入差分として扱える。

## 4. 正本として固定する値

現行正本性能値:

```text
Canonical name = MINIDORA30
Benchmark      = GPQA-E2E-LIVE
Score          = 30 / 198
Accuracy       = 15.151515151515152%
```

以後、単に「現行MINIDORAのGPQA性能」と言う場合は、この値を指す。

ただし将来新しい正本runが成立した場合は、`CURRENT_CANONICAL.md` の更新によって置換する。

## 5. 固定参照Data禁止

本セーブポイント採用と同時に、GPQAの正本運用を次へ変更する。

```text
過去参照を固定して再生するGPQA
→ 正本性能評価として禁止

実行時に参照を新規取得するGPQA E2E
→ 正本性能評価
```

C2、保存済み検索結果、問題別Reference bundle、Replay fixture等をGPQAの現行性能や将来性能比較へ使用しない。

過去のCore37 37/198やModule replay 63/198は削除せず履歴として保持するが、現行正本性能とはしない。

## 6. 比較の意味

MINIDORA30は**その時点の汎用E2E性能値**である。

LIVE参照Dataはrunごとに変わり得るため、将来のE2E得点との差は性能スナップショットの時系列差として記録する。コード変更だけの純粋因果差をGPQAで得るために固定参照Dataへ戻ることは禁止する。

コード単位の因果監査は、局所機能A/B、受入試験、退行試験等で別途行う。

## 7. 機械可読正本

- [`GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json`](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [`BENCHMARK_CONTRACT_v2.md`](BENCHMARK_CONTRACT_v2.md)
