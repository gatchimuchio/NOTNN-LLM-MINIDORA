# NOTNN-LLM-MINIDORA

## 非ニューラルネットワークLLM研究統合リポジトリ

**基準日：2026-08-18**  
**主要言語：日本語**  
**現行状態：`LOCAL_MECHANISM / PRINCIPLE_CANDIDATE`**

このリポジトリは、Layer-0、HDS、LLM不可約機能論を基盤に、Kimi K3、Llama 3、DeepSeek V3.2、Qwen3.6の公開構造を分解・相対化し、非ニューラル計算へ再投影した成果を統合する。

## 核心

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
+ 宣言境界へ言語結果を返す
```

Layer-0 v4では次の形で扱う。

```text
C = Execute(L₀, P, request, state, references)
```

- `L₀`：実行機構
- `P`：命令形保持体

`P`はneural weightsだけでなく、規則、program、state machine、graph、table、decision forest、hybridでよい。

## 主要成果

1. **Layer-0 v3の完全独立監査**
   - 定義域内含意と普遍主張を分離
   - 自己証明型audit・manifest欠陥を再現
   - v4暫定機能核へ再設計

2. **K3の全公開構造解析**
   - KDA：時間状態
   - AttnRes：深さ選択
   - Stable LatentMoE：幅選択
   - Gated MLA：全体照合
   - MOPD：計算予算
   - HDS：採否権限

3. **Llama 3対照解析**
   - Dense shared body
   - 一つのresidual stream
   - 全入力・全block通過
   - K3の選択制御型との構造差

4. **DeepSeek / QwenによるK3相対化**
   - DeepSeek：文脈位置top-kという別解
   - Qwen：Gated Delta＋周期的Attentionの3:1構造
   - Qwen Dense/MoE対照により、hybrid attentionとMoEが独立軸だと確認

5. **K3の普遍と局所を分離**

```text
普遍候補：入力依存で情報・処理・計算量の寄与を変える
K3局所  ：選択を時間・文脈・深さ・幅・予算の5軸へ重ねる
最固有   ：Attention Residualsによる深さ方向選択
```

6. **非ニューラル参照実装**
   - K3型
   - Llama 3型
   - DeepSeek V3.2型
   - Qwen3.6 MoE型
   - Qwen3.6 Dense型

## 構造比較

| 系統 | 最上位の構造 |
|---|---|
| K3 | 多軸選択的情報流 |
| Llama 3 | Dense連続構成 |
| DeepSeek V3.2 | 文脈位置選択＋MoE |
| Qwen3.6 | 有限状態＋周期的全体照合。FFNはDense/MoE交換可能 |
| OpenAI公開system | router型effort制御 |
| Anthropic公開system | 統合model内adaptive thinking |

## 実行

```bash
make test-all
```

個別実行：

```bash
cd 実装
python k3_reference.py --self-test
python llama3_reference.py --self-test
python deepseek_v32_non_neural.py --self-test
python qwen36_non_neural.py --self-test
python compare_all.py
```

## 検証済み範囲

```text
K3完全版                       20/20
Llama 3完全版                  23/23
DeepSeek V3.2参照版             7/7
Qwen3.6 MoE/Dense参照版        10/10
Layer-0責任                    5/5
negative controls              8/8
5モデル同一toy課題             5/5一致
```

## 重要な境界

このリポジトリは次を主張しない。

- 各実モデルと同等の性能・weight・知識量
- frontier benchmark同等性
- open-domain汎用LLM完成
- multimodal理解
- Dense構造が主体性を生むという因果確定
- 唯一の最小構成・普遍原理の確定

## 読む順番

1. [`解析/01_Layer0_HDS_統合理論.md`](解析/01_Layer0_HDS_統合理論.md)
2. [`解析/02_K3_全公開構造解析.md`](解析/02_K3_全公開構造解析.md)
3. [`解析/03_Llama3_全公開構造解析.md`](解析/03_Llama3_全公開構造解析.md)
4. [`解析/04_K3_vs_Llama3_差分.md`](解析/04_K3_vs_Llama3_差分.md)
5. [`解析/05_K3普遍性と局所性_完全相対化.md`](解析/05_K3普遍性と局所性_完全相対化.md)
6. [`設計/01_統合アーキテクチャと主張境界.md`](設計/01_統合アーキテクチャと主張境界.md)
7. [`資料/出典固定台帳.md`](資料/出典固定台帳.md)
