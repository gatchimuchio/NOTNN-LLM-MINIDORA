# tools

`tools/` は、取得物の同一性確認、公開物inventory、リポジトリ整合性監査、外部ベンチ実測など、**開発・監査用の補助ツール**を置く。

Runtime本体は `src/minidora/` であり、`tools/` のスクリプトをMINIDORAの推論Runtime依存として扱わない。

## 現在のツール

| Tool | 役割 | 追加依存 |
|---|---|---|
| `benchmark.py` | リポジトリ標準ベンチランナー。GPQA Diamondの部分実行・途中保存・再開・K3参照比較 | なし |
| `gpqa_measure_current.py` | GPQA現行測定の低水準実装。標準実行入口は `benchmark.py` | なし |
| `repository_consistency_check.py` | v0.4模型核、上流LLM成立規定、version、Legacy境界、主要文書リンクの整合性監査 | なし |
| `k3_hf_identity_inventory.py` | K3 Hugging Face固定revisionのファイル同一性inventory | `huggingface_hub` |
| `k3_public_artifact_inventory.py` | K3固定revisionの公開artifact inventory | `huggingface_hub` |

## リポジトリ標準ベンチ

GitHub Actionsを実行装置の正本にしない。ベンチはclone済みリポジトリから直接実行でき、Actionsは同じコマンドを自動実行するだけとする。

利用可能なベンチ一覧:

```bash
python tools/benchmark.py --list
```

GPQA Diamond 198問を全実測:

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

結果JSONは各問題の診断に加えて、最低限次を保持する。

- `correct / wrong / answered / suspended`
- `answer_rate_percent / answered_accuracy_percent`
- `retrieval_empty / retrieval_empty_rate_percent`
- provider別取得数
- `NO_GUESS` 等の理由集計
- Data compile / K evidence集計
- Kimi K3の同一GPQA Diamond公式参照値と出典

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
