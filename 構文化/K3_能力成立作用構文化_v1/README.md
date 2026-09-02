# K3 能力成立作用構文化 v1

- 実施日: 2026-08-26
- 対象: `moonshotai/Kimi-K3`
- 固定revision: `c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721`
- 観測深度: D4
- ライセンス: CC-BY-4.0

## 目的

既存の `K3_HDS日本語構文_v2` は96 shard / 497,220 tensor / 1,560,860,324,864 byteを全数実読して、K3の物理構造と意味構造を固定した。

本第二巡ではその正本を壊さず、同じ観測を **能力が成立するまでの情報作用** として再構文化する。

第一巡:

```text
何が存在するか
どこに配置されるか
系列 / 深さ / 幅のどの軸か
```

第二巡:

```text
何を保持するか
何へ再作用できるか
何を選択するか
何と再結合するか
いつまで未確定差を残せるか
```

## 正本

- `00_統合報告.md` — K3単体の作用構文化結論
- `01_K3作用構文.md` — B0〜B9の詳細
- `02_10モデル第二巡との差分.md` — K3以外10モデルとの比較
- `03_MINIDORA射影候補.md` — MINIDORAへ移すべき作用候補
- `作用相対座標_v1.json` — 機械可読座標
- `MANIFEST.json` — 範囲・由来・禁止事項

## 観測正本

既存D4:

- `../K3_HDS日本語構文_v2/README_成果物一式.md`
- `../K3_HDS日本語構文_v2/最終全数監査.json`
- `../K3_HDS日本語構文_v2/K3_HDS日本語構文化_v2_成果物一式.zip`

横断第一巡:

- `../LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/11_K3_v2_full-weight.md`

比較対象:

- `../LLM横断_能力成立作用構文化_v1/`

外部一次資料:

- https://huggingface.co/moonshotai/Kimi-K3/blob/c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721/config.json
- https://huggingface.co/moonshotai/Kimi-K3/blob/c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721/configuration_kimi_k3.py
- https://huggingface.co/moonshotai/Kimi-K3/blob/c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721/modeling_kimi_linear.py
- https://huggingface.co/moonshotai/Kimi-K3/blob/c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721/modeling_kimi_k3.py
- https://huggingface.co/moonshotai/Kimi-K3/blob/c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721/README.md

## 状態

`K3_能力成立作用構文化_v1 = 第二巡完了`

本成果はMINIDORA実装仕様ではない。実装候補は `03_MINIDORA射影候補.md` に隔離し、既存の模型核・確定K・HDS Compilerへ自動昇格しない。
