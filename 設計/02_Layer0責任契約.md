# Layer-0 v4責任契約

## 1. 論理上位正本

MINIDORAはLayer-0の意味を独自定義しない。

MINIDORAが参照するLayer-0の論理上位契約は、外部Repository:
[gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)
の `v4.0-provisional` とする。

2026-08-21時点のMINIDORA参照commit:

```text
4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc
```

このcommitは現行MINIDORA実装の再現用pinである。外部Layer-0の `main` が更新されても自動追従せず、意味差分・実装・試験を監査した後に明示更新する。

本書はLayer-0そのものの代替仕様ではなく、**Layer-0上位契約をMINIDORAへ写像する局所契約**である。

参照階層の全体は [`../REFERENCES.md`](../REFERENCES.md) を参照する。

MINIDORA内の旧8責任は `構文化/MINIDORA_v0.2/` の履歴として保持し、現行責任数へは使用しない。

## 2. Functional Core 5責任

1. `LINGUISTIC_ADDRESSABILITY` — **言語アドレス化**
2. `CONTEXT_BOUND_STATE` — **文脈束縛状態**
3. `TRANSFORMATION_OR_COMPOSITION_CORE` — **変換・合成中核**
4. `CONTEXT_DEPENDENT_RESULT_FORMATION` — **文脈依存結果形成**
5. `RESULT_SURFACE` — **結果表面**

重要:

```text
責任数 != 機構数
```

主体主幹、参照R、日本語命令形P、HDS-IR、Trinity J/C/M、Layer-0実行器、採否、Adapter等は、5責任を分担する実装機構であってLayer-0責任数そのものではない。

## 3. MINIDORA v0.3への写像

| Layer-0 v4責任 | MINIDORA v0.3で主に担う機構 |
|---|---|
| 言語アドレス化 | `要求.問合せ`、HDS-IRの原文/正規化文、参照R検索キー、日本語命令形P |
| 文脈束縛状態 | `Layer0`状態、`主体主幹`、Trinity記憶M、HDS文脈、参照R |
| 変換・合成中核 | `Layer0`命令適用、P、K3相当能力核、HDS構造処理 |
| 文脈依存結果形成 | J/採否、主体整合Gate、HDS実行Gate、Pによる結果形成 |
| 結果表面 | Runtime `結果`契約、`multilingual_surface`、Legacy `自然言語器.表面化` |

この表は責任の主担当を示すもので、一対一対応を宣言しない。

## 4. K3とLlama 3の位置

### K3 — 主基盤

K3はMINIDORAの主たる能力・状態関係の観測基盤である。
KDA / MLA / AttnRes / LatentMoE等の物理実装名そのものをLayer-0へ移植せず、HDSで抽出した作用・責任・状態関係をPとRuntimeへ再構成する。

公開MINIDORA RuntimeがK3ニューラルモデル推論を呼び出すことは、Runtime成立の必要条件ではない。

### Llama 3 — 自己一貫性の対抗基準

Llama 3はK3と同格の主基盤ではない。
Dense共通経路、逐次Residual、assistant住所、履歴再入力、preference選択等から観測された**自己一貫性の成立関係**を抽出し、主体主幹へ外在化する。

### その他LLM — 差分観測点

DeepSeek / Qwen / OLMo / Apertus / OpenAI / Claude / Gemini / Grok等は、K3とLlama 3の差分を精密化するための補助観測点として扱う。

## 5. 主体主幹は第6責任ではない

主体主幹はLayer-0 v4の新規責任ではない。

主に次を横断して担う。

```text
CONTEXT_BOUND_STATE
  ×
CONTEXT_DEPENDENT_RESULT_FORMATION
```

処理中の主体状態を全経路へ必須参照させ、専門処理・命令実行が返した差分を主体整合Gateで評価し、理由付き更新だけを次turnへ持ち越す。

## 6. Construction / Operational Wrapper

Layer-0 v4に従い、作られ方と実行責任を分離する。

- MINIDORA construction profile: `authored / compiled / retrieved / hybrid`
- operational profile: `interactive_chat / structured_output / text_api`

HDS構文化、K3/Llama 3からの抽出、手書きP、検索R等の由来は記録するが、Functional Coreの定義へ混入しない。

## 7. Negative controls

MINIDORAでは最低限、Layer-0 v4の8 negative controlを評価対象にする。

1. context除去/固定
2. transformation bypass/canned response
3. source material破損
4. result surface遮断
5. unknown input fallback
6. contradictory context resolution
7. exact retrieval と composition の区別
8. merged-role implementation の許容確認

主体主幹固有ではさらに次を追加する。

- 理由なし主体反転
- 理由付き自己訂正
- 専門処理からの主体主幹迂回
- turn間主体状態持続

## 8. 変更規則

Layer-0責任の意味・数・適合状態・negative controlを変更するときは、次を同時に確認する。

1. 外部Layer-0正本
2. 本書の局所写像
3. `src/minidora/layer0.py`
4. 関連Runtime実装
5. tests / CI
6. README / REFERENCES

下位実装だけを変更してLayer-0意味変更を既成事実化しない。
