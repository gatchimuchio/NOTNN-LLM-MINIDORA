# OLMo 3 — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: dense hybrid-attention anchor
- 観測深度: D3 — 公開weight/config/codeがあり、今回config/構造を直接観測。weight全量実読は未実施

## 観測境界
7B: hidden4096/32 layers/Q32-KV32。32B: hidden5120/64 layers（公開config）。

## 日本語構文化
- 系列方向: 3×sliding_attention + 1×full_attentionを反復。sliding window=4096、context=65536。
- 深さ方向: 標準residual系。
- 幅方向: dense FFN。
- 未来方向/予測補助: model variantごとのtraining/posttrainingと分ける。
- 入力表象・モダリティ: text。
- 形成過程: Base/Instruct/Thinkで形成差を持つがcore layer scheduleは共通に近い。
- 展開後制御: open code/checkpoint。

## 相対化上の意味
Qwen3.6との相対化により「3:1の周期」という見た目の同型と「局所作用子」の非同型を分離できた。

## 未解残差
- weight全量意味解析
- variant間posttraining因果の完全分解

## 出典
- https://huggingface.co/allenai/Olmo-3-7B-Instruct/blob/main/config.json
- https://huggingface.co/allenai/Olmo-3-1125-32B/blob/main/config.json
