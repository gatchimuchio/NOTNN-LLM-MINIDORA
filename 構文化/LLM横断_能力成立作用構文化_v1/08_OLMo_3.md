# 08 OLMo 3 — 能力成立作用構文化

- 観測深度: D3
- 区分: dense hybrid-attention anchor
- ライセンス: CC-BY-4.0

## B0 観測境界

公開config/code/checkpoint構造を観測。7B / 32B系列の中央scheduleを確認。weight全量意味解析とvariant間posttraining因果の完全分解は未実施。

## 観測事実

- 3×sliding attention + 1×full attentionを反復。
- sliding window = 4096。
- context = 65536。
- standard residual系。
- Dense FFN。
- text model。

## B1 状態保持

各層のhidden/residual状態を後段へ渡しつつ、sliding attentionで近傍の高解像度情報を再利用する。

## B2 局所更新・参照

3層のsliding attentionは直近window内のtoken表象を明示参照する。

### 直接作用

- 近傍関係をrawに近い粒度で繰り返し再照合できる。
- global全体を毎層参照する計算を避けながら、局所構成を複数段積み上げられる。

Qwenのrecurrent state updateとは作用が異なる。OLMoは**window内の過去状態を再参照**する。

## B3 大域再照合

4層ごとのfull attentionが、局所windowを越えて広域contextを再接続する。

```text
局所再照合
→ 局所再照合
→ 局所再照合
→ 全体再照合
```

### 作用上の意味

局所で形成した差を、一定間隔で問題全体・長距離文脈へ戻して位置づけ直せる。

## B4 深さ輸送

standard residual系。前状態と各層変換差を累積して後段へ運ぶ。

## B5 幅選択

Dense FFN。tokenごとのexpert routingはない。

## B6 未確定差の共存

局所層で形成された内部差はfull attention層へ到達するまで保持され、そこでより広いcontextと再照合される。局所段階で最終回答へ離散確定する必要はない。

具体的な仮説表象はweight意味未読のため未観測。

## B7 未来補助

variantごとのtraining/posttraining差と分離し、主architecture上の普遍機構として追加しない。

## B8 形成作用

Base / Instruct / Think等のvariantは中央scheduleが近くても形成履歴が異なる。能力差を3:1 scheduleだけへ帰属しない。

## B9 展開後制御

open code/checkpoint。serving engineやproduct harnessはcore外。

## MINIDORAへの作用射影候補

- **局所作業域**を持ち、近傍関係を数段繰り返し構成する。
- 局所作業域の結果を定期的または条件付きで**大域関係へ再接続**する。
- 大域照合で不一致が出ても局所情報を即破棄せず、再検討可能にする。
- sliding attentionそのものではなく、`局所累積 → 大域再照合` の作用を抽出する。

## 未観測

- weight全量意味分布
- local/global layer間の具体的意味分業
- variant間形成差の全因果

## 出典

- AllenAI OLMo 3 public configs/checkpoints
- 第一巡HDS固定観測
