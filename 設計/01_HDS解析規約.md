# HDS解析規約

## 1. 目的

K3を構成部品へ分解することではなく、K3の観測結果から、LLM成立に必要な原理・責任・能力構造を抽出する。

## 2. 固定手順

解析は必ず次の順序で行う。

```text
観測
→ CognitiveWorld
→ 原理質問
→ OpenParallelField
→ 複数Model / Mechanism
→ 反対Model
→ 反実仮想
→ 摂動
→ 不可能性
→ 水平引き算
→ 暫定原理
→ 外部接触
→ Whole-Field Return
→ Layer-0射影
```

前段が未成立なら次段へ進まない。

## 3. 観測対象

K3について収集する対象は以下。

- 公開technical report
- 公開repository / config / code
- model card
- benchmark結果
- 入出力挙動
- reasoning effort差
- context長差
- Kimi Linear等の近縁系との差
- DeepSeek / Qwen / Llama / MiniMax等の異系統実装との差
- 公開ablation
- 計算量・遅延・memory・routing等の観測可能量

## 4. 原理質問

最低限、以下を問う。

1. K3の言語能力を成立させている最小作用は何か。
2. その作用はK3固有architectureがなくても成立するか。
3. capabilityとknowledgeを分離すると何が残るか。
4. 長い直列処理のうち、必要責任と効率化実装をどう分けるか。
5. 状態・関係・条件・変換・停止の最小集合は何か。
6. どの責任がLayer-0へ残り、どの構造が実装固有として消えるか。

## 5. OpenParallelField

一つの説明へ早期収束しない。

例：

```text
Model A: KDA自体が能力源
Model B: KDAは状態保持効率化の実装

Model C: MoE自体が能力源
Model D: MoEは条件付き能力選択の実装

Model E: 巨大weight自体が能力
Model F: weightはCapability/Knowledge/Relation/Transformationの混成媒体
```

各Modelは、支持証拠、反証証拠、未解決残差、予測を持つ。

## 6. 反対Model

各主要Modelには必ず反対Modelを置く。

「KDAが必要」なら「KDAは不要」、「MoEが必要」なら「Denseでも同責任が成立」を置く。

## 7. 摂動・反実仮想

以下を用いて、実装固有物と原理を分離する。

- component除去
- budget縮小/拡張
- context長変更
- routing制約
- state保持制約
- 異architecture比較
- 同一taskでの別モデル比較
- 外部Knowledge固定/変更

## 8. 水平引き算

複数実装を横に並べ、共通して残る作用のみを原理候補へ昇格する。

Layer-0段階で、KDA / MoE / Attention / Transformer等の固有語が残っている場合は解析未完了とする。

## 9. 原理候補の形式

原理候補は日本語で、次の形を満たす。

```text
対象:
条件:
状態:
作用:
関係:
変化:
境界:
停止:
反証条件:
```

## 10. 実装禁止関門

次を満たすまでコード実装を進めない。

- 原理質問が明記されている
- 複数Modelが存在する
- 反対Modelが存在する
- 摂動又は反実仮想がある
- 水平引き算の結果がある
- Layer-0責任へ縮約されている

## 11. Whole-Field Return

実装・評価結果は、最初の観測世界へ戻す。

結果が予測と異なれば、Model / Mechanism / Principle / Layer-0責任を再開放する。
