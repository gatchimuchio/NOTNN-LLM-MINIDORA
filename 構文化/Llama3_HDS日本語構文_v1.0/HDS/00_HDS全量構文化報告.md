# Llama 3 HDS 日本語構文化報告 v1.0

## 0. この文書の位置

対象は **2024-04-18 公開の Meta Llama 3 8B / 70B（Pretrained / Instruct）**。
本処理は公開情報の **翻訳・意味分別・構文化** までで止める。

行わないもの:

- Layer-0 化
- 最小構成化
- P / 命令形への圧縮
- Adapter への分解
- ミニドラ実装への写像
- K3との比較評価

教師観測は 225 件。K3で用いた「教師固定→HDS意味分別→残差保持」の前半方式だけを継承した。

## 1. 認知世界の暫定形成

現時点では対象を次のように切り出す。

- 元Llama 3: 2024年4月の8B / 70B、各Pretrained / Instruct。
- Llama 3.1: 2024年7月の後発版。元版とは別対象。
- モデル本体: tokenizer、学習済みparameter、Transformer計算、生成規則、chat protocol。
- 形成過程: pretraining data形成、pretraining、post-training。
- 外部条件: GPU/分散/故障復帰、評価規則、安全guard。
- 未観測: 重みテンソル実値、生pretraining corpus、生human-preference data、内部評価全量等。

この切り出し自体も暫定であり、後段結果から再開放する。

## 2. 原理質問

中心質問は一つに固定しない。

> Llama 3として観測される入力・内部状態・出力・能力差・拒否・評価値は、何がどの関係によって、どの条件で成立し、何を変えると変化または崩壊するか。

局所質問:

1. 文字列はどう内部計算可能な状態へ接続されるか。
2. 既出文脈から次tokenが選ばれるまで、どの状態遷移があるか。
3. pretrainedとInstructの差はどの形成過程から生じるか。
4. データ量・品質・混合比・計算規模・architectureの寄与を同一原因へ潰さず保持できるか。
5. benchmark値はモデル単体の属性か、評価条件との関係値か。
6. 安全性はモデル内部で閉じるか、外部systemとの合成で成立するか。
7. 2024年4月版とLlama 3.1を混同せず、後発情報をどこまで遡及できるか。

## 3. 開放並列場

最初の「TransformerだからLlama 3が成立する」という説明へ収束しない。

保持した並列候補:

- architectureは能力成立の主因か、主に計算形式・効率条件か。
- 性能増分はarchitecture変更、データ品質、多様性、総量、training scale、post-trainingのどれにどの程度属するか。
- tokenizer改善は意味能力そのものか、同じ計算予算で読める文字量の増加か。
- GQA/KV cacheは能力機構か、主として推論効率機構か。
- Instructの「指示理解」は内部に役割概念が存在するのか、chat control tokenへの条件付けとして成立するのか。
- 正しいreasoningを「持つ」ことと、最終出力で「選ぶ」ことは同一か。
- safetyはモデルparameterに閉じるか、fine-tuning、guard、application policyまで含めた関係か。
- 8B/70B差はparameter数だけか、data freshness・training resource・後学習条件も関与するか。
- 後発Llama 3.1論文で明らかになった系列構造を、元Llama 3へどこまで遡及できるか。

棄却できないものは教師recordの `反対保持` / `未解残差` に残した。

## 4. 原理の分別

現時点で成立関係として分別できるのは、少なくとも次である。

### 4.1 外部記号から内部計算へ

文字列は直接Transformerへ入らない。

**文字列 → tokenizer/BPE → token ID列 → embedding**

会話の場合はさらに、system/user/assistant、header、turn終端を特殊tokenで系列へ埋め込む。
したがって会話の役割境界は、重みとは別に **入力系列の制御記号構成** にも依存する。

### 4.2 自己回帰遷移

公式実装上の中心遷移は、

**既出token列 → embedding → 反復Transformer block → vocab logits → decoding → 次token追加**

である。

Transformer block内は、

**x → x + Attention(Norm(x)) → h + FFN(Norm(h))**

として差分を残差累積する。
AttentionはQ/K/V、RoPE、causal mask、softmax参照配分、V合成の関係として観測できる。

ここから「attentionが意味理解そのもの」等へは昇格しない。
観測できるのは **系列状態間の参照配分を作る機構** までである。

### 4.3 状態と効率

自己回帰生成では、過去のK/Vをcacheへ保持し、新規位置だけを追加する。
GQAは多数のQuery headに対して少数KV headを共有する。

したがって、

- 過去文脈の論理保持
- 過去K/V再計算の省略
- KV cache物理量の削減

は区別して保持する。
GQAを能力そのものへ直結させる根拠は現資料だけでは不足する。

### 4.4 pretrained形成

公開情報から観測できる形成経路は、

**公開源 → 抽出/除重/品質/安全/領域filter → data mix → next-token prediction → pretrained parameter**

である。

Llama 3では15T超、Llama 2比7倍、code量4倍、5%超の非英語などが公開される。
Meta自身が後発論文でarchitecture差よりdata quality/diversity/training scaleを主要性能増分として説明している。ただし後発論文はLlama 3.1結果を扱うため、これは系列証拠として保持する。

### 4.5 Instruct形成

2024年4月資料ではSFT、rejection sampling、PPO、DPO、人間選好が明示される。
重要なのはMeta自身の観測として、

**正しいreasoning traceを生成可能でも、それを選択できない場合がある**

とされ、preference trainingが選択を改善した点である。

したがって少なくとも公開観測上は、

**生成可能集合の形成** と **その集合から何を選びやすくするか**

を同一状態として扱えない。

後発3.1論文ではSFT+RS+DPOを中心にし、PPOよりDPOを選んだとされる。これは元版の記述を否定せず、recipeが版ごとに変化した可能性として保持する。

### 4.6 実行時選択

同じ学習済みparameterと文脈でも、

- temperature=0 → argmax
- temperature>0 → softmax(logits/T)
- top-p → 候補集合制限後sampling

で出力経路が分岐する。

よって単発出力は、学習済み状態だけでなく **decoding ruleとの合成結果** である。

### 4.7 評価

benchmark値は、

**model × prompt format × shot数 × decoding × scoring × aggregation**

の関係値である。

MMLUだけでもbaseとInstructで回答手順が異なり、macro/microで値も異なる。
したがってbenchmark scoreを条件無しの固定能力実体へ昇格しない。

### 4.8 安全

Metaの公開設計自体がsystem-level safetyを採る。

**pretraining filtering + safety fine-tuning + red-team/evaluation + runtime guard + application policy**

の合成で配備安全を作る。
Llama Guard 2 / Code Shieldはモデル外部の実行時層であり、モデル単体の挙動と分離する。

またfalse refusal低減を独立品質として扱っているため、helpfulnessとsafety/alignmentを単一軸化しない。

## 5. 局所適用

今回の目的は実装ではなく構文化であるため、原理候補の局所適用先は **教師データの保存構造** とする。

各観測を、

- 公開観測
- 出典
- 証拠型
- 適用範囲
- HDS意味分別
- 成立関係
- 日本語構文
- 未解残差
- 原理質問
- 反対保持
- 再開放条件

として保存した。

これにより、後段でK3との比較、P形成、最小化等を行う場合でも、今回の観測・反対候補・版境界を不可逆に失わない。

## 6. 結果帰還と総再開放

構文化の結果、最初の対象切り出しを次の点で再開放した。

1. **「Llama 3」名称は単一対象ではない。**
   2024年4月版とLlama 3.1を時間で分けないと、128K、tool use、多言語Instruct等が逆流する。

2. **「128K vocabulary」は厳密ID数と同一ではない。**
   公式表現は128K/128,000、tokenizer実装は特殊token予約を持つ。ゲート内一次config本文を未観測のため、厳密runtime値は保留した。

3. **post-training recipeは版で変化する。**
   元版記事はPPOを含み、3.1論文はDPO中心。どちらかで他方を訂正せず版差として保持する。

4. **公開情報全体にも非公開境界がある。**
   重みテンソル実値、学習文書実体、人間選好生データ、内部red-team全量は観測できない。ここを一般論で補完しない。

このため本構文化は「全公開意味情報を観測可能範囲で固定した」ものであり、「非公開内部状態まで復元した」とは判定しない。

## 7. 現時点の構文化結論

Llama 3は一個の説明語で閉じない。
公開観測上、少なくとも以下の相互依存した状態群として切り出す必要がある。

**記号化 / 会話制御 / 自己回帰変換 / 文脈状態保持 / 実行時選択 / 事前学習データ形成 / 大規模学習 / 後学習による選択傾向形成 / 評価規則 / 外部安全系 / 物理運用**

これは最小構成ではない。
何を残し何を捨てられるかの判断もまだしていない。

**ここで構文化を止める。**
