# HDS相対化観測軸 更新記録 v0.1

これはHDS本体を固定版として凍結する文書ではない。今回のLLM横断構文化において、相対化で新しい差分が現れるたびに観測軸を更新した履歴である。各revは旧revを消さず、何が新たに分離されたかを保持する。

## R0
- 発火条件: 旧Llama3/OLMo3等の単体構文化
- 更新: 記号化・系列変換・形成・実行時選択・評価・安全を分離。

## R1
- 発火条件: 公開weight系と非公開frontier系を同一場へ置いた
- 更新: A0 観測深度を追加。未知を性能差として扱わない。

## R2
- 発火条件: OpenAI GPT-5.6 / Claude Fable-Mythos
- 更新: A1/A8。モデル本体・推論runtime・agent harness・classifier/fallbackを分離。

## R3
- 発火条件: OLMo3 vs Qwen3.6
- 更新: A2を「局所/全体」だけでなく「配置周期」と「局所作用子」に分解。window参照とrecurrent状態更新を別物化。

## R4
- 発火条件: DeepSeek V4 vs K3
- 更新: A3。系列方向と深さ方向の情報輸送を直交軸化。mHC/AttnResをattentionへ潰さない。

## R5
- 発火条件: Qwen/DeepSeek/K3 MoE比較
- 更新: A4。幅方向の専門経路選択を系列・深さ方向の選択から分離。

## R6
- 発火条件: Qwen MTP / OpenAI speculative draft
- 更新: A5。未来予測補助を主モデル因果列から分離し、training/servingの位置も保持。

## R7
- 発火条件: Apertus1.0→1.5、Gemini/Qwen multimodal
- 更新: A6。モダリティ前段の追加と中央decoder再設計を同一視しない。

## R8
- 発火条件: Grok4.6のmulti-harness SFT/RL、各社deployment差
- 更新: A7/A8。形成時に使ったharnessと展開時harnessを分離し、能力成立の因果を保持。

## 原則
- HDSは随時更新する。
- 同一性は局所再現性のために版として残す。
- 相対化で差分が見えたら、基準側も再開放する。
- 過去構文化は教師として新構文化へ流し込まず、最後の差分監査に使う。
- 未観測を一般論で埋めない。
