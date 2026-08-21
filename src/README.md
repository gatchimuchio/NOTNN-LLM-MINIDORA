# src

`src/` はMINIDORA Runtimeの実装ソースを保持する。

現行パッケージは `src/minidora/` である。設計の意味は `../設計/`、外部参照正本は `../REFERENCES.md`、実測は `../評価/` を参照する。実装コードだけから上位仕様を再定義しない。

## `minidora/` の主要境界

| Module | 主な責任 |
|---|---|
| `layer0.py` | Layer-0 v4上位契約のMINIDORA命令実行実装と参照情報 |
| `命令.py` | 日本語命令形Pの実行単位 |
| `参照.py` | 外部参照Rの供給・競合判定 |
| `hds_ir.py` | 公開HDS-IR Recordと実行Gate |
| `hds_adapter.py` | 外部HDS CompilerとのProtocol境界 |
| `trinity_context.py` | Trinity J/C/M文脈の保持・帰還 |
| `主体.py` | 主体状態、理由付き更新、主体整合Gate |
| `採否.py` | 合格・保留・失敗・非適用の採否 |
| `runtime.py` | HDS-IR / Layer-0 / P / R / 主体主幹の統合Runtime |
| `multilingual_surface.py` | HDS経路の多言語結果表面 |
| `言語.py` | HDS Compiler未接続時のLegacy互換自然言語入口 |
| `k3_functional.py` | K3構文化由来の非ニューラル機能相当能力核 |
| `k3_hds_native.py` | HDS-IRとK/J構造照合の直接接続 |
| `hds_data_k.py` | Data HDS-IRからK構造Factへの射影 |
| `hds_graph_reasoning.py` | HDS方向付き関係の経路探索 |
| `k3_benchmark.py` | K3機能相当評価harness |
| `__main__.py` | module / console CLI入口 |

## Layer-0

Layer-0の論理上位正本は外部Repository:
[gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)
である。

`layer0.py` はそのMINIDORA固有実装であり、外部正本の意味を置き換えない。

## 公開境界

HDS Compiler内部実装および上流HDSの内部解析方法そのものは `src/` に含めない。公開RuntimeはHDS-IR入出力契約を通して外部Compilerと接続する。
