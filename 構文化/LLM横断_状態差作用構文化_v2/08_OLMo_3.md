# OLMo 3 — 状態差作用構文化 v2

- 観測深度: D3 / dense hybrid-attention anchor
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `08_OLMo_3.md`。3×sliding attention + 1×full attention、window 4096、context 65536、residual、Dense。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

residual hidden state + window内過去token表象。

## A — 作用

3 sliding-attention blocksでlocal reference、4層目full attentionでglobal reference。

## Δ — 状態差

各block出力が後段residual stateを変える。localで形成された表象差がfull layer入力へ届く。

## D — 後続依存

DEPTH_DOWNSTREAM_DEPENDENCYとattention state-dependent weightingを観測。

## P — 状態依存の経路変化

3:1 layer scheduleは固定。状態差がglobal再照合を「発火」するとは言わない。Dense FFNでexpert routingなし。

## R — 再参照・再利用の尺度

window内明示referenceと周期的full-context reference。runtime recursionではなくconfigured depth pattern。

## C — 再結合

local block outputがresidualを通じてglobal layerへ入り、global context情報と統合。

## F — 形成循環

Base/Instruct/Think等は同じ中央scheduleでも形成履歴差を持つ。

## v1からの訂正・保持

v1の「局所→大域再照合loop」を、実装観測としてはfixed depth scheduleへ修正。MINIDORAで条件付きloopへ射影するなら別仮説であり直接再現ではない。

## 未観測

weight意味、local/global semantic division、variant形成差の全因果。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
