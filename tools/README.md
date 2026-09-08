# tools

`tools/` は、取得物の同一性確認、公開物inventory、リポジトリ整合性監査、外部ベンチ実測など、**開発・監査用の補助ツール**を置く。

Runtime本体は `src/minidora/` であり、`tools/` のスクリプトをMINIDORAの推論Runtime依存として扱わない。

## 現在のツール

| Tool | 役割 | 追加依存 |
|---|---|---|
| `benchmark_strict.py` | **正本GPQA入口**。198/198全数・LIVE_ONLY・固定参照Data禁止を機械固定する | なし |
| `benchmark_contract.py` | Benchmark Contract v2。正本GPQA条件・fingerprint・主張可能範囲を生成する | なし |
| `benchmark.py` | 低水準GPQA runner。部分実行・診断用。単独出力を正本性能値として引用しない | なし |
| `benchmark_formal.py` | HDS監督介入を含む低水準GPQA runner。正本入口から呼ばれる | なし |
| `gpqa_measure_current.py` | GPQA現行測定の低水準実装 | なし |
| `repository_consistency_check.py` | v0.4模型核、上流LLM成立規定、version、Legacy境界、主要文書リンクの整合性監査 | なし |
| `k3_hf_identity_inventory.py` | K3 Hugging Face固定revisionのファイル同一性inventory | `huggingface_hub` |
| `k3_public_artifact_inventory.py` | K3固定revisionの公開artifact inventory | `huggingface_hub` |

## Benchmark Contract v2

評価の正本は [`../評価/BENCHMARK_CONTRACT_v2.md`](../評価/BENCHMARK_CONTRACT_v2.md) とする。

2026-09-09以後、GPQA Diamondの正本性能評価は次だけを認める。

```text
GPQA-E2E-LIVE
= 問題 + 選択肢 + 実行時に新規取得する参照Data
= 汎用E2E性能スナップショット
```

GPQAでは、C2、保存済み検索結果、固定Reference/Data bundle、Replay fixture等の**固定参照Dataを正本性能評価へ使用しない**。

過去の固定Replay資産は履歴として保持するが、現行性能・将来正本・GPQA性能比較の入力へ再利用しない。

## 正本GPQA入口

```bash
python tools/benchmark_strict.py gpqa-e2e --out gpqa_e2e.json
```

正本入口は内部で次を固定する。

```text
GPQA Diamond 198/198
CSV SHA256 = 41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305
choice seed = 0
OpenAlex = disabled
Wikipedia = en
reference = LIVE_ONLY
controlled A/B = required
fixed reference Data = forbidden
```

部分実行用の `--start-index` / `--limit` は低水準runner側にのみ残し、`benchmark_strict.py` の正本GPQA入口では受け付けない。

結果JSONの `benchmark_contract` には最低限次が入る。

- `benchmark_id`
- `evaluation_class`
- `input_boundary`
- `retrieval_mode`
- `fixed_reference_data_allowed`
- `condition_fingerprint_sha256`
- `canonical_full_run`
- `canonical_score_field`
- `cross_run_code_delta_direct`
- `snapshot_score_chronology_allowed`
- `claim_scope`
- `forbidden_claims`

`fixed_reference_data_allowed` は必ず `false`。

## 現行セーブポイント

現行正本は [`../docs/SAVEPOINT_2026-09-09_MINIDORA30.md`](../docs/SAVEPOINT_2026-09-09_MINIDORA30.md)。

```text
MINIDORA30
GPQA-E2E-LIVE
30 / 198
15.151515151515152%
```

正本実測記録:

- [`../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md`](../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [`../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json`](../評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)

## E2E run間の比較

同じ正本運用規則で得た別runの得点は、時系列のE2E性能セーブポイントとして並べてよい。

ただし参照Dataは毎run新規取得されるため、別runの得点差をコード変更だけの純粋因果差とは扱わない。

```bash
python tools/benchmark_strict.py compare before.json after.json
```

`compare` は得点差を表示するが、`correct_delta_is_code_only_causal=false` を明示する。

コード単位の因果監査はGPQA固定Replayへ戻さず、局所A/B・機能受入・退行試験で行う。

## 低水準GPQA runner

`benchmark.py` / `benchmark_formal.py` は部分実行・診断・内部実装用として残す。

これらを直接実行して得たJSONは、Benchmark Contract v2の正本条件を満たす入口から生成されていない限り**正本性能値として採用しない**。

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

ベンチdatasetは既定で `.cache/minidora-bench/` に保存する。これは公式GPQA問題集合の同一性確認用cacheであり、外部参照結果の固定Replayではない。

部分実行値は198問正本値と直接混同しない。198/198完走時だけ現行性能候補とする。

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
