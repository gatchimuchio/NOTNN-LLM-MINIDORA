# 01 OpenAI GPT-5.6 Sol — 能力成立作用構文化

- 観測深度: D2
- 区分: frontier closed
- ライセンス: CC-BY-4.0

## B0 観測境界

内部weight/config/architectureは非公開。core内部の系列・深さ・幅機構は推定しない。

公式に確認できるのは、GPT-5.6の成立物が少なくとも **model / inference / agentic harness** に分離され、さらにtrainingでtask successとefficiencyを同時に最適化していること。

## 観測事実

- GPT-5.6 Solはfrontier modelとして公開され、長いcontextと複数reasoning effortを持つ。
- 公式engineering説明は、modelそのものに加えてload balancing、routing、kernel optimization、caching、speculative decoding等のinference層を分離する。
- ChatGPT Work / Codex等ではagentic harnessがtool use、context管理、反復作業を別責任として処理する。
- trainingではtask successだけでなく、より少ないtokenで直接的に仕事を進めるefficiencyも最適化対象とされる。

## B1〜B7 core内部作用

**未観測。**

外部から見える長文脈・reasoning・coding能力を、特定のattention、MoE、memory構造へ逆投影しない。

## B8 形成作用

### 直接作用

training objectiveがtask successとefficiencyを同時に圧力として持つため、形成後modelには「同じ仕事をより直接的に完遂する」選択傾向が残る。

これはruntimeの高速化とは別である。runtime最適化は同じmodel計算を安く速く実行する作用、training最適化はmodel側の出力経路自体を変える作用として分離する。

## B9 展開後制御

### inference

- load balancing / scheduling: 計算資源の配分。
- cache: 既計算状態の再利用。
- speculative decoding: 主modelの意味能力を増やすのではなく、候補先読みでservingを高速化する。
- kernel optimization: 同じ演算を効率化する。

### agentic harness

- toolとmodelを接続する。
- 長期作業で増えたcontextを整理し、不要な再処理を抑える。
- prompt cacheのため完全一致prefixを保持する。
- repeated workを外部状態として管理する。

### 作用上の意味

観測される「長い仕事を終える能力」は、weight単体だけでなく、**外部状態保持・tool接続・context整理**によって増幅される。

## 比較推定

GPT-5.6 Solの高いagentic性能からcore内部作用を特定することはできない。一方、公式に三層分離されているため、MINIDORAでも次を混ぜない根拠になる。

```text
模型中核
!= inference効率化
!= agent harness
```

## MINIDORAへの作用射影候補

- 長期task stateは模型中核へ無制限に詰めず、外部状態として整理する。
- cache / tool / orchestrationは模型能力へ加算しない。
- ただし外部状態管理が完遂能力を増幅することは別軸で評価する。
- efficiencyを「意味を削ること」と同一視しない。必要な差を保持したまま重複処理を減らす。

## 未観測

- internal sequence operator
- depth transport
- width routing
- latent hypothesis representation
- weak-signal retention mechanism

## 出典

- OpenAI, `How GPT-5.6 fuses frontier intelligence with frontier efficiency`, 2026-07-29.
- OpenAI, `Previewing GPT-5.6 Sol`, 2026-06-26.
- OpenAI API model documentation, `GPT-5.6 Sol`.
