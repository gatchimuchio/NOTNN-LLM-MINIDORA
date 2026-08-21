# 構文化

`構文化/` は、外部モデル・公開資料・MINIDORA自身をHDS日本語構文で観測・再構成した成果を保持する。

ここは**観測・再構成層**であり、現行Runtime実装や設計正本そのものではない。

## 現行MINIDORAとの関係

- [`MINIDORA_v0.3/`](MINIDORA_v0.3/) — 現行MINIDORA v0.3へ対応する公開再構成成果。
- [`MINIDORA_v0.2/`](MINIDORA_v0.2/) — Legacy。履歴として保持し、現行Layer-0責任数等へ復帰させない。

## 主要観測基盤

- [`K3_HDS日本語構文_v2/`](K3_HDS日本語構文_v2/) — K3主基盤の構文化成果。
- [`Llama3_自己一貫性_HDS再構文化_v2/`](Llama3_自己一貫性_HDS再構文化_v2/) — 主体主幹へ接続した自己一貫性差分の現行観測成果。
- [`Llama3_HDS日本語構文_v1.0/`](Llama3_HDS日本語構文_v1.0/) — Llama 3の旧・基礎観測成果。
- [`LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/`](LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/) — 複数LLMを相対化する補助観測。
- `OLMo3_HDS日本語構文_v1.0/` 等のモデル別ディレクトリ — 差分観測点。K3 / Llama 3と同格のMINIDORA正本ではない。

## Layer-0との境界

Layer-0の論理正本は `構文化/MINIDORA_v0.3/Layer0/` ではない。

正本は外部Repository:
[gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)

現行MINIDORAが参照する仕様は `v4.0-provisional`、参照commitは `4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc` である。

`MINIDORA_v0.3/Layer0/` は、その上位契約と構文化成果をMINIDORA側から再構成・保持した成果として扱う。

## 取り扱い規則

- 構文化成果を実装へ自動変換しない。
- 観測事実、解釈、原理候補、MINIDORAへの採用判断を混同しない。
- Legacy成果を削除せず、現行成果と明示的に分離する。
- 上流HDSの内部解析方法そのものは公開対象外とする。
- 現行設計へ採用された内容は `../設計/` 側で契約として明示する。
