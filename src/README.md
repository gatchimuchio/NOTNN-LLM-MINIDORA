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
| `計算実行器.py` | P互換入口を計算中間表現へ降下し、計算実行境界で実行する汎用計算器 |
| `hds_compiler_v1.py` | Meaning/Audit Architecture v1.2 + Pipeline v1.3の公開HDS Compiler入口 |
| `hds_compiler_pipeline_v1_3.py` | 意味IR・計算計画・計算降下の責任分離 |
| `hds_ir.py` | 公開HDS意味IR RecordとGate |
| `hds_adapter.py` | HDS CompilerとのProtocol境界。独立Dataでは意味入口を優先 |
| `layer0.py` | 旧Layer0 API互換窓口。現行LLM模型中核ではない |
| `runtime.py` | v0.4模型核と既存運用経路の統合入口 |
| `runtime_v03.py` | v0.3 Runtimeの履歴互換実装 |
| `旧_layer0_v03.py` | v0.3 Layer0命令器の履歴実装 |
| `命令.py` | 日本語命令形Pの実行前表現 |
| `参照.py` | 外部参照Rの供給・競合判定 |
| `主体.py` | 主体状態、理由付き更新、主体整合Gate |
| `採否.py` | 合格・保留・失敗・非適用の採否 |
| `言語.py` | Legacy互換の決定論的計算意図形成・表面化 |
| `semantic_tokens.py` | 言語対応で再利用する意味語内部住所 |
| `k3_functional.py` | K3構文化由来の能力補助 |
| `__main__.py` | module / console CLI入口 |

## 上位LLM成立規定

- [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版 `2026-08-26-成立規定-2`
- 参照commit `e94a13ba32208aabd9dc88b6de320872963725be`

## 主従

```text
模型.py                        = LLM模型中核
hds_compiler_v1.py             = 意味/監査Compiler入口
hds_compiler_pipeline_v1_3.py  = 意味/計算責任分離
命令.py                        = 人間可読の計算計画P
計算中間表現.py                = 実行専用中間表現
計算実行境界.py                = 実行ABI
計算実行器.py                  = ABIを使う計算作用
参照系                         = 外部Data
主体.py                        = 運用主体性
```

## HDS Compiler現行経路

```text
自然言語
↓
意味コンパイル
↓
意味HDS-IR
├─ R / K / J / 監査
└─ 計算計画
   ↓
 計算降下
   ↓
 計算中間表現
```

`意味コンパイル()` の結果へP・計算初期状態を混入しない。`コンパイル()` は旧Runtime向け互換窓口に限定する。

旧Layer0命令器を模型中核へ戻さない。
