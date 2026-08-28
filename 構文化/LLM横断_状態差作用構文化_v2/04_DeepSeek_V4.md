# DeepSeek V4 — 状態差作用構文化 v2

- 観測深度: D3相当 / public architecture
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `04_DeepSeek_V4.md`。public paper / Transformers実装 / configに基づく中央構造。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

local high-resolution representation、compressed long-range representation、mHC multiple residual streams。意味役割は未読。

## A — 作用

sliding local branch、CSA/HCA long-range reference、mHC stream mixing、MoE transformation。

## Δ — 状態差

各branch/streamの変換により後段へ渡る表象が変化する。意味的仮説差とは断定しない。

## D — 後続依存

各変換結果が後続層入力となるためDEPTH_DOWNSTREAM_DEPENDENCYを観測。

## P — 状態依存の経路変化

CSA indexer top-kとMoE routingは状態依存のreference/path selectionとして扱える。fixed branch topology自体とは分離する。

## R — 再参照・再利用の尺度

long-range compressed representationの再参照経路を観測。mHCはdepth transportであって時間的runtime loopとは呼ばない。

## C — 再結合

local/long-range branch、multi residual streams、MoE outputが後段stateへ統合される。

## F — 形成循環

pretraining/posttrainingが具体的なweight関係を形成。architectureだけでは意味役割は決まらない。

## v1からの訂正・保持

v1の「複数working track」をMINIDORAへ直射しない。構造上multi-streamがあることと明示仮説trackは別。

## 未観測

weight意味分布、expert意味、stream意味分業、production harness。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
