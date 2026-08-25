# 構文化

`構文化/` は、外部モデル・公開資料・MINIDORA自身をHDS日本語構文で観測・再構成した成果を保持する。

ここは**観測・再構成層**であり、現行Runtime実装や設計正本そのものではない。

## 現行MINIDORAとの関係

- [`MINIDORA_v0.4/`](MINIDORA_v0.4/) — 現行MINIDORA v0.4の再構成記録。
- [`MINIDORA_v0.3/`](MINIDORA_v0.3/) — 2026-08-22プロトタイプ完成を含むv0.3系履歴。
- [`MINIDORA_v0.2/`](MINIDORA_v0.2/) — Legacy。

v0.3以前を削除せず、v0.4へ無言統合しない。

## 主要観測基盤

- [`K3_HDS日本語構文_v2/`](K3_HDS日本語構文_v2/) — K3主基盤の構文化成果。
- [`Llama3_自己一貫性_HDS再構文化_v2/`](Llama3_自己一貫性_HDS再構文化_v2/) — 主体主幹へ接続した自己一貫性差分。
- [`Llama3_HDS日本語構文_v1.0/`](Llama3_HDS日本語構文_v1.0/) — Llama 3基礎観測。
- [`LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/`](LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/) — 複数LLMを同一HDS座標で相対化した観測資料。

これらは能力・構造の観測基盤であり、LLM成立条件の正本ではない。

## 上流LLM成立規定との境界

現行の論理上位正本は:
[gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)

- 版: `2026-08-26-成立規定-2`
- MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`

旧 `MINIDORA_v0.3/Layer0/` 等は当時の再構成履歴であり、現行上位正本ではない。

## 取り扱い規則

- 構文化成果を実装へ自動変換しない。
- 観測事実、解釈、原理候補、MINIDORAへの採用判断を混同しない。
- Legacy成果を削除せず、現行成果と明示的に分離する。
- HDSによる観測成果であることと、HDS自体がLLM成立条件であることを混同しない。
- 現行設計へ採用された内容は `../設計/` 側で契約として明示する。
