# K3 HDS日本語全公開データコンパイル v6.1 — 現行HF残差完遂

## 判定

**PASS**

- 基底v6.0: `c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721`
- 現行HF固定HEAD: `9f62e4e9fffbd0a83ddd60e1c209d828994b3569`
- 現行HF files: 118
- identity不変・v6再利用: 113
- 今回全数翻訳artifact: 5
- 今回処理byte: 45865 / 45865
- 未処理item: 0
- 未処理byte: 0
- HDS gap: 0
- 現行公開overlay source item: 130
- 現行公開overlay source byte: 1561002450726

## 差分

追加: `['.eval_results/apex-agents.yaml', '.eval_results/deep-swe.yaml', '.eval_results/gpqa.yaml', '.eval_results/hle.yaml']`

変更: `['README.md']`

削除: `[]`

不変artifactはv6.0で処理済みの同一内容をidentity一致によって再利用し、追加・変更artifactは現行内容を全文・全byte実読してHDS日本語意味構文化した。
