# tools

`tools/` は、取得物の同一性確認、公開物inventory、リポジトリ整合性監査、外部ベンチ実測など、**開発・監査用の補助ツール**を置く。

Runtime本体は `src/minidora/` であり、`tools/` のスクリプトをMINIDORAの推論Runtime依存として扱わない。

## 現在のツール

| Tool | 役割 | 追加依存 |
|---|---|---|
| `benchmark_strict.py` | **正本Benchmark入口**。汎用E2E / 固定Replayを別IDで実行し、直接比較可否を機械判定する | なし |
| `benchmark_contract.py` | Benchmark Contract v1。評価種別・入力境界・fingerprint・主張可能範囲を生成する | なし |
| `benchmark.py` | 低水準GPQA runner。単独出力を正本性能値として引用しない | なし |
| `gpqa_measure_current.py` | GPQA現行測定の低水準実装 | なし |
| `repository_consistency_check.py` | v0.4模型核、上流LLM成立規定、version、Legacy境界、主要文書リンクの整合性監査 | なし |
| `k3_hf_identity_inventory.py` | K3 Hugging Face固定revisionのファイル同一性inventory | `huggingface_hub` |
| `k3_public_artifact_inventory.py` | K3固定revisionの公開artifact inventory | `huggingface_hub` |

## Benchmark Contract v1

評価の正本は [`../評価/BENCHMARK_CONTRACT_v1.md`](../評価/BENCHMARK_CONTRACT_v1.md) とする。

同じ `GPQA Diamond 198問` でも、実際の入力境界が異なる結果を同一性能値として扱わない。

```text
GPQA-E2E-LIVE
= 問題 + 選択肢 + 実行時LIVE参照取得
= 汎用E2Eスナップショット

GPQA-FIXED-REPLAY
= 問題 + 選択肢 + 固定参照/Data bundle
= 実装差分・回帰差分
```

FIXED-REPLAY得点を汎用E2E性能へ読み替えない。LIVE別run間の得点差をコード変更だけの因果差へ読み替えない。

## 正本ベンチ入口

GPQA Diamondの汎用E2Eスナップショット:

```bash
python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
```

固定Replayによる実装差分:

```bash
python tools/benchmark_strict.py gpqa-fixed-replay replay.jsonl --out gpqa_replay.json
```

二つの結果が直接比較可能か確認:

```bash
python tools/benchmark_strict.py compare before.json after.json
```

`compare` が拒否した二結果を正本の直接差分として主張しない。

結果JSONの `benchmark_contract` には最低限次が入る。

- `benchmark_id`
- `evaluation_class`
- `input_boundary`
- `retrieval_mode`
- `condition_fingerprint_sha256`
- `input_snapshot_sha256`
- `cross_run_code_delta_direct`
- `claim_scope`
- `forbidden_claims`

## 低水準GPQA runner

`benchmark.py` / `benchmark_formal.py` は部分実行・診断・内部実装用として残す。

これらを直接実行して得たJSONは、Benchmark Contract v1を付与していない限り**正本性能値として採用しない**。

GPQA Diamond 198問の低水準実測:

```bash
python tools/benchmark.py gpqa-diamond --out gpqa_current_measurement.json
```

まず10問だけ確認:

```bash
python tools/benchmark.py gpqa-diamond --limit 10 --out gpqa_smoke.json
```

途中で停止した同一範囲を再開:

```bash
python tools/benchmark.py gpqa-diamond --limit 10 --out gpqa_smoke.json --resume
```

任意位置から分割実行:

```bash
python tools/benchmark.py gpqa-diamond --start-index 50 --limit 25 --out gpqa_050_074.json
```

ベンチデータは既定で `.cache/minidora-bench/` に保存する。`--refresh-dataset` を明示した場合だけ再取得する。

部分実行値はK3の198問スコアと直接比較しない。198/198完走時だけ比較差・比率を結果へ確定する。

## リポジトリ整合性監査

```bash
python tools/repository_consistency_check.py
```

CIでも同じ監査をLinux / Windows × Python 3.11–3.14で実行する。

v0.4では、旧Layer0の5責任を期待値にするのではなく、

- `LLM-Constitutive-Specification` の参照版・commit
- `src/minidora/模型.py` の独立性
- `Layer0`旧名が計算実行器へ限定されること
- HDS-IRが模型中核と分離されること
- v0.3履歴が保持されること

を監査する。

## K3 inventory

K3 inventoryは外部サービスへアクセスする開発用処理のため、Runtime依存から分離する。必要な場合だけ追加依存を導入する。

```bash
python -m pip install huggingface_hub
python tools/k3_hf_identity_inventory.py --out /tmp/k3-hf-identities.json
python tools/k3_public_artifact_inventory.py --out /tmp/k3-public-artifacts.json
```

両ツールは指定した出力先へJSONを書くだけで、ブランチ作成・commit・pushを自動実行しない。
