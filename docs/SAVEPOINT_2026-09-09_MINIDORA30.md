# MINIDORA SAVEPOINT — 2026-09-09 MINIDORA30

状態: **現行正本セーブポイント**  
基底言語: 日本語

## 1. 目的

局所解釈起点の実装を含む現行MINIDORAについて、GPQA Diamond 198問を固定参照Dataなしの汎用E2Eで完走した時点を `MINIDORA30` として固定する。

このセーブポイント以後、GPQA正本性能評価では固定参照Dataを使用しない。

## 2. 固定した履歴点

- 局所解釈起点主要実装: `b70344677c3a761af3e3bfac57b1fe92980b6f0e`
- 実測対象実装親commit: `a3473fbdacc5e0e2ac1927faa08c60717ace0544`
- benchmark workflow commit: `63603f39d62bd77ae40732f6c51701aaab9fe468`
- GitHub Actions run: `34281226412`
- aggregate artifact: `10078256754`
- artifact SHA256: `0c7ef2b4a474bf5cd6ee55d5ca170480292186babbc7d559afb268c347ede83c`

## 3. 現行GPQA正本性能

```text
Canonical name = MINIDORA30
Benchmark      = GPQA-E2E-LIVE
Current        = 30 / 198
Accuracy       = 15.151515151515152%
Answered       = 130 / 198
SUSPEND        = 68 / 198
```

同run controlled baseline:

```text
baseline       = 27 / 198
correct delta  = +3
improved       = 3
regressed      = 0
```

正本実測記録:

- [`../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md`](../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [`../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json`](../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)

## 4. GPQA運用固定

以後のGPQA正本は次だけを認める。

```text
公式GPQA Diamond 198問
+ seed 0
+ 実行時LIVE参照取得
+ OpenAlex disabled
+ Wikipedia en
+ controlled A/B
+ 198/198全数
```

次は禁止する。

```text
固定C2
保存済み検索結果
固定Reference/Data bundle
Replay fixture
過去run参照の再投入
```

固定するのは評価構成であり、外部参照結果そのものではない。

## 5. 過去値の扱い

Core37の `37/198`、Module replayの `63/198` 等は当時の履歴・成立実証として保存する。

ただし、2026-09-09以後の現行GPQA正本性能値、将来GPQA性能比較の入力、正本置換基準として固定参照Replayを再利用しない。

```text
Core37 / Replay系列 = HISTORY
MINIDORA30 / LIVE E2E = CURRENT CANONICAL
```

## 6. 次回置換条件

次に正本GPQA性能を置換する場合は、同じBenchmark Contract v2の正本入口で198/198を完走する。

```bash
python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
```

新しいrunについて、dataset hash、全数、seed、LIVE_ONLY、固定参照Data禁止を機械確認したうえで `CURRENT_CANONICAL.md` を更新する。

異なるrun間の得点差はE2E性能スナップショットの時系列差として扱い、コード変更だけの純粋因果差とはしない。

## 7. 通常検証

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

GPQA198問全数は通常pushでは自動実行せず、正本性能更新時に明示実行する。
