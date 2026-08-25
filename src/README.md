# src

`src/` はMINIDORA Runtimeの実装ソースを保持する。

現行パッケージは `src/minidora/`。意味正本は `../設計/`、外部LLM成立正本は `../REFERENCES.md`、実測は `../評価/` を参照する。実装コードだけから上位仕様を逆定義しない。

## 現行主要境界

| Module | 主な責任 |
|---|---|
| `模型.py` | 言語対応、文脈付き内部状態、再利用可能な模型側関係、成立差 |
| `計算中間表現.py` | Compute IRに相当する計算専用型。即値・状態値・状態住所を分離 |
| `計算実行境界.py` | ABI v1に相当する決定論的計算実行契約 |
| `命令計算降下.py` | 日本語命令形Pから計算中間表現への降下 |
| `HDS計算降下.py` | 閉包済みHDS-IRから計算中間表現への移行用降下 |
| `計算実行器.py` | P互換入口を計算中間表現へ降下し、計算実行境界で実行する汎用計算器 |
| `layer0.py` | 旧Layer0 API互換窓口。現行LLM模型中核ではない |
| `runtime.py` | v0.4模型核とv0.3運用経路の統合入口 |
| `runtime_v03.py` | v0.3 Runtimeの履歴互換実装 |
| `旧_layer0_v03.py` | v0.3 Layer0命令器の履歴実装 |
| `命令.py` | 日本語命令形Pの実行前表現 |
| `参照.py` | 外部参照Rの供給・競合判定 |
| `hds_ir.py` | 公開HDS semantic IR Recordと実行Gate |
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

## 主従

```text
模型.py           = LLM模型中核
HDS系             = 意味Projection / 運用 / 監査
命令.py           = 人間可読の運用命令P
計算中間表現.py   = 実行専用中間表現
計算実行境界.py   = 実行ABI
計算実行器.py     = ABIを使う計算作用
参照系            = 外部Data
主体.py           = 運用主体性
```

旧Layer0命令器を模型中核へ戻さない。

## 計算経路

```text
日本語命令形P
      ↓
命令計算降下
      ↓
計算中間表現
      ↓
計算実行境界
      ↓
計算結果
```

計算実行境界は自然言語/HDS/模型核/外部参照を解釈しない。

## HDS公開境界

公開HDS Compiler群は引き続き公開実装である。ただしHDS-IRをLLM模型中核または計算中間表現と同一視しない。

現行 `HDS計算降下` は閉包済み互換 `HDSIR.手順` を使う移行境界。次段でCompilerをsemantic frontendとcompute lowering backendへ分離する。
