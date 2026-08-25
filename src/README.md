# src

`src/` はMINIDORA Runtimeの実装ソースを保持する。

現行パッケージは `src/minidora/`。意味正本は `../設計/`、外部LLM成立正本は `../REFERENCES.md`、実測は `../評価/` を参照する。実装コードだけから上位仕様を逆定義しない。

## v0.4主要境界

| Module | 主な責任 |
|---|---|
| `模型.py` | 言語対応、文脈付き内部状態、再利用可能な模型側関係、成立差 |
| `計算実行器.py` | 日本語命令形Pの算術・比較・状態更新等を実行する汎用計算器 |
| `layer0.py` | 旧Layer0 API互換窓口。現行LLM模型中核ではない |
| `runtime.py` | v0.4模型核とv0.3運用経路の統合入口 |
| `runtime_v03.py` | v0.3 Runtimeの履歴互換実装 |
| `旧_layer0_v03.py` | v0.3 Layer0命令器の履歴実装 |
| `命令.py` | 日本語命令形Pの実行単位 |
| `参照.py` | 外部参照Rの供給・競合判定 |
| `hds_ir.py` | 公開HDS-IR Recordと実行Gate |
| `hds_adapter.py` | HDS CompilerとのProtocol境界 |
| `主体.py` | 主体状態、理由付き更新、主体整合Gate |
| `採否.py` | 合格・保留・失敗・非適用の採否 |
| `言語.py` | 既存運用の決定論的自然言語計画・表面化 |
| `semantic_tokens.py` | 言語対応で再利用する意味語内部住所 |
| `k3_functional.py` | K3構文化由来の能力補助 |
| `__main__.py` | module / console CLI入口 |

## 上位LLM成立規定

- [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版 `2026-08-26-成立規定-2`
- 参照commit `e94a13ba32208aabd9dc88b6de320872963725be`

`模型.py` は上位正本をMINIDORAへ写像する実装であり、外部正本の意味を置き換えない。

## v0.4の主従

```text
模型.py       = LLM模型中核
計算実行器.py = 計算作用
HDS系         = 意味Projection / 運用 / 監査
参照系        = 外部Data
主体.py       = 運用主体性
```

旧Layer0命令器を模型中核へ戻さない。

## HDS公開境界

公開HDS Compiler群は引き続き公開実装である。ただしHDS-IRをLLM模型中核またはCompute IRと同一視しない。

v0.4ではCompiler本体の大規模再設計を先行させず、次段のCompute IR確定後にlowering境界を更新する。
