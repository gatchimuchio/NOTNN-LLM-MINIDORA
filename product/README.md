# MINIDORA 製品Runtime

**版：1.0.0-rc.2**  
**正本：main**  
**主要言語：日本語**

このdirectoryは、研究用参照実装ではなく、永続化・監査・失敗状態・API・CLI・試験・ベンチを閉じた製品Runtimeです。

## 起動

```bash
cd product
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,documents]"
pytest
minidora serve
```

## 質問

```bash
minidora ask "Project Atlasは文書をどこに保存していますか？" --effort high
```

## ベンチ

```bash
python benchmarks/run_benchmark.py --output benchmark_results --repetitions 300
```

## 製品境界

- 成立：根拠拘束型の日本語文書・事実・規則・監査Runtime
- 未成立：実K3相当のopen-domain知識、自由生成、multimodal、frontier性能
