# DeepSeek V4 — HDS日本語構文化 第一巡

- 日付: 2026-08-21
- 区分: frontier architecture-public
- 観測深度: D3 — 公開weight/config/codeがあり、今回config/構造を直接観測。weight全量実読は未実施

## 観測境界
V4はV3のMLAをhybrid local + long-range attentionへ置換し、residualをmHCへ置換する公開実装仕様。

## 日本語構文化
- 系列方向: 三系統: sliding-window、CSA（低圧縮＋indexer top-k）、HCA（高圧縮＋全compressed entry参照）。さらにlong-range branchとlocal sliding branchを併置。
- 深さ方向: Manifold-Constrained Hyper-Connections (mHC)。系列attentionとは別軸。
- 幅方向: MoE。詳細はV4系config/implementationに依存し、今回weight全量は未実読。
- 未来方向/予測補助: V4 paper系列の補助機構は別軸で扱う。今回、未確認部分を一般論で埋めない。
- 入力表象・モダリティ: 本稿対象はlanguage model core。
- 形成過程: advanced optimization techniquesをpaperが報告。
- 展開後制御: Transformers実装まで観測。production harnessは別。

## 相対化上の意味
K3のAttnResと並べることで「系列方向の参照」と「深さ方向の輸送」が直交することを強く相対化。CSA/HCAはさらに圧縮率・選択有無を別軸化。

## 未解残差
- 全weight意味分布
- expert固有意味
- production routing/harness

## 出典
- https://huggingface.co/papers/2606.19348
- https://huggingface.co/docs/transformers/en/model_doc/deepseek_v4
