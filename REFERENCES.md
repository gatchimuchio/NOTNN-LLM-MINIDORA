# MINIDORA 参照正本

この文書は、MINIDORAが外部成果をどの位置づけで参照するかを固定する。

## 1. 論理上位契約 — Layer-0

MINIDORAにおけるLLM機能責任の論理的基盤は、次の外部リポジトリである。

- Repository: [gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)
- 現行仕様: `v4.0-provisional`
- 現行MINIDORA参照commit: `4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc`
- 日本語正本: 上記リポジトリの `docs/layer0_v4_spec.ja.md`

Layer-0の意味、5機能責任、責任と機構の分離、適合状態、negative controlは、MINIDORA内で独自に再定義しない。

MINIDORA側の [`設計/02_Layer0責任契約.md`](設計/02_Layer0責任契約.md) は、Layer-0正本をMINIDORAへどう写像するかを定める**局所契約**であり、Layer-0そのものの代替正本ではない。

実装上の対応は `src/minidora/layer0.py`、受入・回帰確認は `tests/test_layer0.py` および関連negative control試験が担う。

### 更新規則

外部Layer-0リポジトリの `main` が更新されても、MINIDORAは自動追従しない。

1. 新しいLayer-0正本を確認する。
2. MINIDORAへの意味影響を監査する。
3. `設計/02_Layer0責任契約.md` と実装・試験の整合を確認する。
4. 問題がなければ参照commitを明示更新する。

これにより、論理上位契約と再現可能な実装pinを分離する。

## 2. 能力・構造の観測基盤

次はLayer-0のような上位規範ではなく、MINIDORAの能力構造を抽出・比較するための観測基盤である。

- **K3** — 主基盤。能力処理・状態関係の主要観測元。
- **Llama 3** — 自己一貫性の対抗基準。主体主幹の成立関係を抽出する観測元。
- **その他LLM** — K3 / Llama 3の差分を相対化する補助観測点。

これらのニューラルモデル推論を公開MINIDORA Runtimeが呼び出すことは、Runtime成立の必要条件ではない。

## 3. HDSの公開境界

HDS / HDS Compilerは上流の分別・意味Projectionに用いるが、HDS Compilerの内部実装および上流HDSの内部解析方法そのものは本リポジトリの公開対象外とする。

公開MINIDORAが規定するのは、HDS-IRの受入・実行・帰還境界である。

## 4. 正本優先順位

Layer-0に関する矛盾が生じた場合は、次の順で監査する。

1. 外部Layer-0正本の参照version / commit
2. `設計/02_Layer0責任契約.md` のMINIDORA局所写像
3. `src/minidora/layer0.py` の実装
4. tests / 評価記録

下位層の記述が上位契約と食い違う場合、食い違いを仕様変更として正当化せず、まず不整合として扱う。
