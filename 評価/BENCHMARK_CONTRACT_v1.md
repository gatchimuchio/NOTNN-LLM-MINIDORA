# MINIDORA Benchmark Contract v1

## 目的

同じ外部タスク名でも、実際にMINIDORAへ与えた入力境界が異なる結果を同一性能値として混同しない。

以後、GPQA Diamondは最低でも次の二つへ分離する。

## 1. GPQA-E2E-LIVE

Benchmark ID:

```text
gpqa-diamond-e2e-live-v1
```

評価対象:

```text
問題文 + 選択肢
→ 実行時の標準参照取得
→ HDS / Core / J
→ 回答
```

これは、未知参照環境を含む現行システムの汎用E2Eスナップショットを測る。

ただし参照取得内容は実行日時で変わり得るため、別run間の得点差をコード変更だけの因果差として扱ってはならない。

同一run内のcontrolled A/Bは、同じ取得資料をbaseline/currentへ共有する場合に限って直接差分として扱える。

## 2. GPQA-FIXED-REPLAY

Benchmark ID:

```text
gpqa-diamond-fixed-replay-v1
```

評価対象:

```text
固定済み問題文 + 選択肢 + 参照/Data bundle
→ 実装A / 実装B
→ 回答差
```

これは汎用E2E性能ではない。

目的は、同一入力を与えたときの実装差分・回帰差分を測ることである。

直接比較には `input_snapshot_sha256` の一致を必須とする。

## 3. 数値の表記規則

裸の `37/198`、`30/198` のような表記を正本比較には使わない。

最低限、次を併記する。

```text
Benchmark ID
Evaluation class
Dataset hash
Input snapshot hash または LIVE
Repository commit
正答 / 総数
```

例:

```text
GPQA-FIXED-REPLAY / C2 / Core+HDS / 37/198
```

または

```text
GPQA-E2E-LIVE / 2026-09-09 snapshot / 30/198
```

## 4. Core37の扱い

2026-09-08に固定した `Core+HDS = 37/198` は、**固定C2 Replay正本値**である。

これは次を意味する。

```text
同一C2入力に対する再現可能な比較基準
```

次を意味しない。

```text
未知参照環境を含む無条件の汎用GPQA性能 = 37/198
```

Core37から実装を変更した場合の純粋差分は、同じC2 bundleを用いたFIXED-REPLAYで測る。

汎用E2E性能の変化は、別途GPQA-E2E-LIVEで測る。

この二つの結果を一つの数字へ統合しない。

## 5. 機械契約

正本入口:

```bash
python tools/benchmark_strict.py gpqa-e2e --out result.json
python tools/benchmark_strict.py gpqa-fixed-replay replay.jsonl --out result.json
python tools/benchmark_strict.py compare before.json after.json
```

`compare` は、Benchmark IDまたは固定入力hashが異なる直接比較を拒否する。

結果JSONには `benchmark_contract` を持たせる。

最低限のフィールド:

```text
schema
benchmark_id
evaluation_class
input_boundary
retrieval_mode
condition_fingerprint_sha256
input_snapshot_sha256
cross_run_code_delta_direct
claim_scope
forbidden_claims
```

## 6. 主張規則

以後、MINIDORAの性能主張は次のどちらかに必ず分類する。

```text
汎用E2Eスナップショット
または
固定入力による実装差分
```

分類不能なベンチ結果は正本性能値として採用しない。
