# MINIDORA 参照正本

この文書は、MINIDORAが外部成果をどの位置づけで参照するかを固定する。

## 1. 論理上位契約 — 大規模言語模型成立規定

MINIDORAにおけるLLM模型性の論理的基盤は、次の外部リポジトリである。

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 現行版: `2026-08-26-成立規定-2`
- 現行MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`
- 日本語正本: `規定/02_大規模言語模型成立.md`

MINIDORAは上位規定を独自に再定義しない。特に、旧Layer-0 v4の5責任を現行LLM構成条件へ自動継承しない。

MINIDORA側の [`設計/02_大規模言語模型成立契約.md`](設計/02_大規模言語模型成立契約.md) は、上位規定をMINIDORA v0.4へどう写像するかを定める局所契約である。

現行実装の中心は次である。

- `src/minidora/模型.py` — 言語対応、文脈付き内部状態、再利用可能な模型側関係、成立差。
- `src/minidora/計算実行器.py` — 算術・比較・状態更新等の汎用計算作用。LLM模型中核ではない。
- `src/minidora/layer0.py` — 旧公開API互換窓口。新設計の正本ではない。

### 更新規則

外部正本の `main` が更新されてもMINIDORAは自動追従しない。

1. 新しい正本・版・commitを確認する。
2. MINIDORA模型核への意味影響を監査する。
3. 局所契約・実装・試験の整合を確認する。
4. 問題がなければ参照commitを明示更新する。

下流MINIDORAに合わせて上流規定を曲げない。

## 2. 能力・構造の観測基盤

次は論理上位契約ではなく、MINIDORAの能力構造を抽出・比較するための観測基盤である。

- **K3** — 主たる能力・状態関係の観測元。
- **Llama 3** — 自己一貫性の対抗観測元。
- **その他LLM** — K3 / Llama 3の差分を相対化する補助観測点。

これらのニューラルモデル推論を公開MINIDORA Runtimeが呼び出すことを、模型成立の必要条件にしない。

## 3. HDSの位置

HDSは観測・分別・意味Projection・外部運用に用いる。

ただし、HDSであること、HDS-IRを持つこと、HDS Compilerを通ること自体は、大規模言語模型成立規定の模型性条件ではない。

公開MINIDORAが規定するHDS-IRは、現在の運用接続・履歴・意味Projection境界である。次段のCompute IR確定後にlowering境界を再監査する。

## 4. 正本優先順位

LLM模型性に関する矛盾が生じた場合は、次の順で監査する。

1. 外部 `LLM-Constitutive-Specification` の参照版 / commit
2. `設計/02_大規模言語模型成立契約.md`
3. `src/minidora/模型.py`
4. `src/minidora/runtime.py` の統合境界
5. tests / 評価記録

HDS Compiler、K3相当能力核、主体主幹、参照R、計算実行器は、それぞれの局所責任について監査する。これらの実装差からLLM成立規定を逆定義しない。

## 5. 旧Layer-0

旧Layer-0 v4参照と5責任契約は履歴である。

旧局所契約は [`設計/旧/02_Layer0責任契約_v4.md`](設計/旧/02_Layer0責任契約_v4.md) に退避し、現行正本には使用しない。
