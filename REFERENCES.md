# MINIDORA 参照正本

この文書は、MINIDORAが外部成果をどの位置づけで参照するかを固定する。

## 1. 論理上位契約 — 大規模言語模型成立規定

MINIDORAにおけるLLM模型性の論理的基盤は、次の外部リポジトリである。

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 現行版: `2026-08-27-成立規定-3`
- 現行MINIDORA参照commit: `306ff834e5ac7e7e958b513db723a24619c8895a`
- 日本語正本: `規定/02_大規模言語模型成立.md`

MINIDORAは上位規定を独自に再定義しない。特に、旧Layer-0 v4の5責任を現行LLM構成条件へ自動継承しない。

MINIDORA側の [`設計/02_大規模言語模型成立契約.md`](設計/02_大規模言語模型成立契約.md) は、上位規定をMINIDORA v0.4へどう写像するかを定める局所契約である。

現行実装の中心は次である。

- `src/minidora/模型.py` — LLM成立5条件を維持しつつ、構成再現7条件に従う状態保持・再作用・再結合・終端成立差。計算主体 `C`。
- `src/minidora/hds判断主体.py` — `C` が形成した候補差を、証拠・矛盾・候補横断・Commit・総暫定性で裁定する判断主体 `J`。
- `src/minidora/hds判断参照境界.py` — 成功したData IRと実参照識別子・信頼を同一添字で `J` へ保持する境界。
- `src/minidora/hds_model_projection.py` — HDS構文化済みQuestion / Candidate / Dataを `C → J` へ接続する正式射影境界。Data残差による局所証拠阻害も保持する。
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

HDSは観測・分別・意味Projection・Data Compiler・最終意思決定に用いる。

ただし、HDSであること、HDS-IRを持つこと、HDS Compilerを通ること自体は、大規模言語模型成立規定の模型性条件ではない。`src/minidora/模型.py` はHDS非依存を維持する。

正式knowledge choiceでは責務を次に分離する。

```text
HDS構文化済みQuestion / Candidate / Data
  ↓
MINIDORA模型核 C
  ↓ 候補差
HDS判断主体 J
  ↓
APPROVE / SUSPEND
```

`C` の出力は候補であり最終権威ではない。`J` は実参照識別子・信頼・残差証拠境界を保持したDataを使い、弱支持・競合・矛盾・未閉包を保持したままCommit/HOLDを裁定する。詳細は [`設計/27_HDS判断主体_MINIDORA終端接続_v1.md`](設計/27_HDS判断主体_MINIDORA終端接続_v1.md) を正本とする。

公開MINIDORAのHDS判断実装は、MINIDORA終端に必要な有限射影であり、HDS本体の原理探索全体・永続更新U・Owner権限変更・非公開解析正本を無断転記しない。

## 4. 正本優先順位

LLM模型性に関する矛盾が生じた場合は、次の順で監査する。

1. 外部 `LLM-Constitutive-Specification` の参照版 / commit
2. `設計/02_大規模言語模型成立契約.md`
3. `src/minidora/模型.py`
4. `設計/27_HDS判断主体_MINIDORA終端接続_v1.md` / `src/minidora/hds判断主体.py` の局所採否境界
5. `src/minidora/runtime.py` / `src/minidora/hds_choice_runtime.py` の統合境界
6. tests / 評価記録

HDS Compiler、K3相当能力核、主体主幹、参照R、計算実行器は、それぞれの局所責任について監査する。これらの実装差からLLM成立規定を逆定義しない。

## 5. 旧Layer-0

旧Layer-0 v4参照と5責任契約は履歴である。

旧局所契約は [`設計/旧/02_Layer0責任契約_v4.md`](設計/旧/02_Layer0責任契約_v4.md) に退避し、現行正本には使用しない。