# NOTNN-LLM-MINIDORA

## 非ニューラルネットワークLLM研究統合リポジトリ

**基準日：2026-08-18**  
**主要言語：日本語**  
**現行状態：`LOCAL_MECHANISM / PRINCIPLE_CANDIDATE`**

このリポジトリは、Layer-0、HDS、LLM不可約機能論を基盤に、Kimi K3、Llama 3、DeepSeek V3.2、Qwen3.6の公開構造を分解・相対化し、非ニューラル計算へ再投影した成果を統合する。

## 中核命題

```text
LLMの本体
≠ Transformer
≠ Attention
≠ MoE
≠ Neural Network

LLM的機能
= 言語を扱う
+ 文脈状態を持つ
+ 内容依存に参照する
+ 変換・合成する
+ 状態依存に結果を形成する
+ 宣言境界へ言語結果を出す
```

Layer-0 v4では次の形で扱う。

```text
C = Execute(L₀, P, request, state, references)
```

- `L₀`：実行機構
- `P`：規則、知識、関係、状態遷移、変換手続、失敗条件を保持する命令形保持体

`P`はneural weightsに限定しない。

## 主要成果

1. **Layer-0 v3の独立監査とv4再設計**
2. **HDSによる生成・採否・未知・矛盾・権限の分離**
3. **K3公開構造の全体解析と非ニューラル参照実装**
4. **Llama 3 Dense構造の解析とK3差分**
5. **DeepSeek V3.2／Qwen3.6によるK3の普遍・共通・局所の相対化**
6. **K3型、Llama 3型、DeepSeek型、Qwen MoE／Dense型の同一課題比較**
7. **非ニューラル統合アーキテクチャ候補の抽出**

## K3相対化後の結論

```text
K3の上位原理
= 多軸選択的情報流
```

K3は、時間・文脈・深さ・幅・計算予算を独立した選択軸として重ねる。

- 普遍候補：入力依存で情報・状態・処理・計算量の寄与を変える
- K3／Qwen共通：Gated Delta系有限状態＋周期的global attention
- K3／DeepSeek／Qwen MoE共通：routed expert＋shared expert
- K3で最も固有性が強い：**Attention Residuals**

## 暫定統合案

```text
Dense constitutional core
+ sparse peripheral specialists
+ multi-axis selective memory/context
+ independent HDS authority gate
```

## 検証済み範囲

```text
K3完全版                       20/20
Llama 3完全版                  23/23
DeepSeek V3.2参照版             7/7
Qwen3.6 MoE／Dense参照版       10/10
Layer-0責任                    5/5
negative controls              8/8
5モデル同一toy課題             5/5一致
```

## 読む順番

1. [`研究総括.md`](研究総括.md)
2. [`成果物一覧.md`](成果物一覧.md)
3. [`成果バンドル/README.md`](成果バンドル/README.md)
4. `python 成果バンドル/復元.py`
5. 復元したZIP内の `解析/`、`設計/`、`実装/`、`結果/`、`資料/`

## 重要な境界

確認したのは、異なる公開architectureを同じ機能座標へ写像し、特徴を保ったまま非ニューラル計算へ再構成できること。

次は未成立・未主張。

- 実モデルweight、知識量、性能、速度の再現
- frontier benchmark同等性
- open-domain汎用LLM完成
- multimodal semantics
- 唯一最小構成または普遍原理の確定
