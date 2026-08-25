# 03 K3からMINIDORAへの作用射影候補

- 日付: 2026-08-26
- 根拠: K3 D4能力成立作用構文化 v1
- 状態: 実装前候補
- ライセンス: CC-BY-4.0

## 0. 結論

K3をそのままコピーする必要はない。

MINIDORAへ最も強く射影すべき差分は、**確定Gateと寄与Gateを分けること**である。

現行MINIDORAの確定K境界は、ハルシネーション防止のため維持する。

一方、その手前で、

```text
弱い
競合している
条件付き
まだ反証探索中
別Dataで再確認可能
```

な関係を即廃棄せず、寄与量つきのworking stateとして残す。

K3ではKDA / Gated MLA / AttnRes / MoEの複数箇所で、途中Gateが「真偽確定」ではなく「どの状態・経路をどれだけ使うか」に働く。

## P0 — 最優先

### 1. Gateを二種類へ分離

```text
確定Gate
- 確定Kへ入れてよいか
- 最終Jへ進めてよいか

寄与Gate
- working relationをどれだけ残すか
- どのcheckpointを再利用するか
- どの専門作用をどれだけ使うか
```

確定Gateは現行の安全性を守る。

寄与Gateは真偽を決めず、未確定状態の再利用順・寄与量だけを決める。

非ニューラル実装ではsoftmaxや確率分布を採用する必要はない。決定論的な整数 / 有理重み / 順序規則でよい。

### 2. Working Relation Storeを多層化

最低限、

```text
current_working_state
checkpoint_store
candidate_competition_state
```

を分ける。

working relationには、

- source
- relation
- polarity
- condition
- support state
- contradiction state
- reuse count
- last_reconciled_stage
- reopen condition

を持たせる。

確定Kとは物理的・型的に分離する。

### 3. depth checkpoint作用

AttnResの非ニューラル射影。

一定段数または意味変化時に、working state全体のsnapshotを保存する。

例:

```text
問題解析後
外部Data統合後
候補仮説形成後
反証探索後
```

後段で矛盾・残差が出たら、現在状態だけで継続せず、過去checkpointと現在状態を再照合する。

固定12段周期は採用しない。

### 4. 同一情報への複数回再作用

Dataを一回HDS化して一回K昇格判定して終了しない。

```text
Data
↓
局所relation化
↓
他Dataとの照合
↓
候補集合との照合
↓
反証との照合
↓
checkpointとの再照合
↓
確定可能ならK/J
```

同一Dataへ異なる責任の作用が複数回アクセス可能にする。

### 5. 候補集合を共同状態化

GPQAのA/B/C/Dだけでなく、一般の候補集合を共同状態として保持する。

必要な作用:

- 同一根拠が複数候補へ与える差を同時更新
- 一候補の成立が他候補へ与える反作用を記録
- 共通根拠と固有根拠を分離
- 例外候補を残り候補との比較で検出

一候補ずつ独立scoreして最後に最大を取るだけの構造から脱する。

## P1 — 高優先

### 6. 局所更新と大域再照合

K3の3 KDA + 1 MLAを固定模倣しない。

MINIDORAでは、

```text
局所Data / relationを数段処理
↓
大域問題状態と再照合
↓
必要ならraw Data / checkpointへ戻る
```

とする。

再照合trigger候補:

- contradiction発生
- candidate差が縮小
- 新Data追加
- unresolved relation残存
- condition境界変化

### 7. 共通作用 + 複数専門作用

Stable LatentMoEの非ニューラル射影。

共通作用:

- 否定
- 条件
- 因果
- 時系列
- 定義
- 比較
- 引用/出典

専門作用候補:

- 数量
- 物理関係
- 生物関係
- code構造
- 法規/規約
- 例外処理

ただしbenchmarkカテゴリごとの手書き正解ruleにはしない。

一入力へ専門作用を一つだけ選ぶのではなく、必要なら複数作用を並行適用し、結果を共同working stateへ戻す。

### 8. 形成工程

K3の能力はarchitectureだけではなく形成済みweightに宿る。

MINIDORAでも、Data / 実行履歴から、

- 再利用可能な関係
- 適用条件
- 反対条件
- 再照合順序
- failure signature

を形成する独立工程を持つ。

形成物は自動で確定Kへ昇格させず、出典・version・再開放条件を保持する。

## P2 — 補助

### 9. modality adapter

MoonViT-V2をコピーしない。

異種入力を、

```text
画像 / 音声 / 動画
↓
modality固有解析
↓
明示された共通内部言語状態
↓
既存模型関係
```

へ接続する責任分離だけを採る。

### 10. 外部agent harness分離

K3のagentic benchmark / coding完遂能力とweight coreを同一視しない。

MINIDORAでもtool orchestration、長期task state、GUI、外部memoryは模型核外に置き、別評価する。

## 新しく測るべき内部指標

P0実装後はGPQA正答率だけでは不足する。

追加計測:

- `working_relations_created`
- `working_relations_reused`
- `working_relations_promoted_to_K`
- `working_relations_discarded_after_recheck`
- `checkpoint_count`
- `checkpoint_reactivations`
- `global_reconciliations`
- `candidate_cross_updates`
- `specialist_actions_invoked`
- `suspend_after_exhaustion`

特に、

```text
working relationは増える
確定Kは無闇に増えない
再作用後に必要なものだけKへ昇格する
```

状態を狙う。

## GPQAでの検証

現行:

- 19 / 198 = 9.596%
- 回答118
- 回答時正答率16.102%
- SUSPEND 80
- K facts 101,554
- evidence facts 120,504

改善判定では、

1. 回答時正答率が上がる。
2. 総合正答率が上がる。
3. unknown / contradiction停止を壊さない。
4. retrieval / Data compileの既存安定性を壊さない。
5. working state増加を確定K水増しで代替しない。
6. GPQA以外の一般relation testでも再作用効果を確認する。

を同時に見る。

## 実装順

```text
1. 寄与Gate型
2. Working Relation Store
3. checkpoint_store
4. 候補共同状態
5. 再作用loop
6. 局所→大域再照合
7. 共通+専門作用
8. 関係形成工程
```

この順序なら、現行確定Kの安全境界を保持したまま、K3から得た最大差分だけを追加できる。

## 採用してはいけない短絡

K3が強いからといって、次を必須化しない。

- 93 layers
- 3:1 schedule
- KDA
- MLA
- AttnRes
- 12-layer checkpoint
- 896 experts
- 16 experts/token
- MoE
- neural network
- probability distribution
- sampling

必要なのは部品ではなく、**状態保持・再作用・再結合・確定遅延という作用**である。
