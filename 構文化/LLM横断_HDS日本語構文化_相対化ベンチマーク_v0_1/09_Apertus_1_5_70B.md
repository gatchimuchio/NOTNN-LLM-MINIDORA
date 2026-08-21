# Apertus 1.5 70B — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: dense multimodal natural experiment
- 観測深度: D3 — 公開weight/config/codeがあり、今回config/構造を直接観測。weight全量実読は未実施

## 観測境界
1.0からcontinued pretraining。公式に同じdecoder-only transformer architecture（xIELU）を維持すると説明。元70Bはhidden8192/80 layers/Q64-KV8。

## 日本語構文化
- 系列方向: 中央text decoderはdense global attention系。
- 深さ方向: 標準residual系。
- 幅方向: dense FFN。
- 未来方向/予測補助: thinking modeはposttraining/serving modeとして中央decoder geometryと分離。
- 入力表象・モダリティ: 1.5はimage/audio/text input。repoにはcore model 3 shardsに加えvision_tokenizerとwavtokenizerのweightが別ファイルで存在。
- 形成過程: continued pretraining（multimodal mix）＋posttraining改善。
- 展開後制御: tool callingとthinking modeは同時利用制約もあり、runtime mode境界を持つ。

## 相対化上の意味
中央decoderを維持したままモダリティとreasoning/tool capabilityが拡張。能力追加＝中央architecture刷新、ではない自然実験。

## 未解残差
- 1.5全weight意味解析
- 前段tokenizer→decoder接続の全詳細

## 出典
