# MINIDORA Benchmark Contract v2

## 目的

GPQA Diamondの正本性能評価を、**未知参照環境を含む汎用E2E性能**だけへ固定する。

2026-09-09以後、GPQAで保存済み参照結果・固定参照コーパス・Replay bundle等を入力する評価を、新しい正本性能値、回帰基準、性能比較値として採用しない。

## 1. GPQA正本はE2E LIVEのみ

Benchmark ID:

```text
gpqa-diamond-e2e-live-v2
```

評価対象:

```text
GPQA Diamond 問題文 + 選択肢
↓
実行時に新規取得する標準参照Data
↓
MINIDORA Core / HDS / J
↓
回答
```

この境界全体を、その実行時点のMINIDORA汎用性能として測る。

## 2. 固定参照Data禁止

GPQA正本では次を禁止する。

- C2等の固定参照コーパス
- 過去runで保存した検索結果・参照結果
- 問題別に凍結した参照/Data bundle
- Replay fixtureを外部知識入力として使う測定
- goldまたは正解情報を利用して選別・整形した参照Data
- 上記を別名・cache名へ変更して正本GPQAへ再投入すること

GPQA問題集合そのもののdataset cacheは、公式datasetの同一性確認用なので禁止対象ではない。

同一run内のcontrolled A/Bで、**そのrun中に新規取得した同一参照Dataをbaseline/currentへ共有すること**は許可する。これはrun間の固定Replayではなく、同一観測入力に対するHDS介入差分を測るためである。

## 3. 正本運用条件

MINIDORA30を固定した条件を以後のGPQA正本入口とする。

```text
benchmark                 = GPQA Diamond
full total                = 198
selected                  = 0..197 全数
GPQA CSV SHA256           = 41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305
choice shuffle seed       = 0
OpenAlex                  = disabled
Wikipedia                 = en
reference                 = LIVE_ONLY
controlled A/B            = required
fixed reference Data      = forbidden
```

固定するのは**評価構成**であり、検索結果そのものではない。

## 4. 正本入口

```bash
python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
```

この入口は198/198全数、`--no-openalex`、controlled A/Bを内部で固定する。

`benchmark.py` / `benchmark_formal.py` の部分実行、任意開始位置、任意provider条件は診断用途として残すが、直接の出力を正本性能値として採用しない。

`gpqa-fixed-replay` は正本入口から廃止する。

## 5. 正本結果の必須情報

正本JSONは `benchmark_contract` に最低限次を持つ。

```text
schema
benchmark_id
evaluation_class
input_boundary
retrieval_mode
fixed_reference_data_allowed
condition_fingerprint_sha256
canonical_full_run
canonical_score_field
within_run_controlled_ab_direct
cross_run_code_delta_direct
snapshot_score_chronology_allowed
claim_scope
forbidden_claims
```

`fixed_reference_data_allowed` は必ず `false` とする。

## 6. 得点の扱い

各正本runの得点は、そのrun時点の**汎用E2E性能セーブポイント**として時系列保存してよい。

ただし参照Dataは毎run新規取得されるため、異なる日時の得点差をコード変更だけの純粋因果差とは主張しない。

```text
同一run controlled A/B差
= 直接差分として扱える

別runのE2E得点差
= 性能スナップショットの時系列差
!= コード変更だけの純粋因果差
```

GPQAでコードだけの効果を切り出すために固定参照Dataへ戻ることは禁止する。必要な因果監査は、GPQAとは別の局所A/B・機能受入・退行試験で行う。

## 7. MINIDORA30

2026-09-09に採用した現行正本性能セーブポイント:

```text
MINIDORA30
GPQA-E2E-LIVE
30 / 198
15.151515151515152%
```

根拠:

- GitHub Actions run: `34281226412`
- benchmark head: `63603f39d62bd77ae40732f6c51701aaab9fe468`
- measured implementation parent: `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- aggregate artifact: `10078256754`
- artifact SHA256: `0c7ef2b4a474bf5cd6ee55d5ca170480292186babbc7d559afb268c347ede83c`
- dataset CSV SHA256: `41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305`

詳細は `GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md` を参照する。

## 8. Module込みシステム正本 — MINIDORA80

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

Core37のC2 37/198、科学専門Module replay 63/198等の過去固定Replayは、**当時の実験・履歴証拠として削除しない**。

ただし2026-09-09以後、それらを現行GPQA性能、現行正本、将来のGPQA比較基準として再利用しない。

```text
過去Replay = 履歴
現行GPQA正本 = LIVE E2Eのみ
```
