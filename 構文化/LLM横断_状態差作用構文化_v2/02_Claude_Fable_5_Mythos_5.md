# Claude Fable 5 / Mythos 5 — 状態差作用構文化 v2

- 観測深度: D2 / closed / deployment natural experiment
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `02_Claude_Fable_5_Mythos_5.md`。同一underlying modelと外部classifier/safeguard/fallback差を観測。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

core内部stateは未観測。外部分類結果・routing条件はsystem stateとして観測可能。Anthropic一次資料では、persistent file-based memoryを与えた長期task評価でFable 5の性能改善も報告されており、外部memory stateがsystem-level能力へ寄与する自然実験として扱える。

## A — 作用

外部classifier/safeguardが入力を評価し、core通過またはfallback/rerouteを選ぶ。

## Δ — 状態差

classifier判断によってsystem execution stateが変化する。これはmodel hidden state差ではない。

## D — 後続依存

外部分類結果が後続実行経路を直接変えるため、SYSTEM-level後続依存は強い。

## P — 状態依存の経路変化

EXTERNAL_BRANCH_SELECTIONを直接観測。同一coreでも外部Gate差で可観測挙動が変わる。

## R — 再参照・再利用の尺度

明示core recursionは未観測。fallbackはbranchであり、保存state再活性とは異なる。persistent file memoryの再利用も外部memory loopでありcore内部stateの証拠ではない。

## C — 再結合

fallback結果とcore結果の統合条件全量は未観測。

## F — 形成循環

Fable/Mythos差を形成差へ帰属できない。deployment自然実験として扱う。

## v1からの訂正・保持

v1の「答えない≠知らない」は維持。新たに、Gateによるbranchは動的経路選択の実例だが模型外であると明示する。

## 未観測

underlying architecture、internal state retention、hypothesis competition、classifier/fallback全条件。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
