# OpenAI GPT-5.6 Sol — 状態差作用構文化 v2

- 観測深度: D2 / closed
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `01_OpenAI_GPT-5_6_Sol.md`。公式公開情報としてmodel / inference / agentic harness分離、task success + efficiency training圧力、cache/routing/speculative decoding/tool/context管理を記録。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

core内部状態担体は未観測。展開側では長期task state、context、cache等の外部状態を観測。

## A — 作用

core内部作用は未観測。inference層のcache/routing/scheduling/speculationとagent harnessのtool/context操作は模型外作用として観測。OpenAI一次資料は、単一user turn内でも多数のmodel requestとtool callが反復し得ること、model-visible historyをappend-onlyにして次requestへ渡すことを明示する。

## Δ — 状態差

外部task stateやcontextは各tool/action後に変化するが、その差をcore内部hidden stateの機構へ逆投影しない。

## D — 後続依存

外部harnessでは更新されたtask/context stateが次のtool/model call条件へ使われるため、system-level後続依存は観測できる。core-levelは未観測。

## P — 状態依存の経路変化

routing/tool orchestrationで外部経路は変わる。core内部のstate-dependent routingは未観測。

## R — 再参照・再利用の尺度

agentic harnessの反復・context再投入はSYSTEM/HARNESS_LOOPとして直接観測できる。cache再利用は既計算prefixの再利用であり、意味的state再作用と同一視しない。

## C — 再結合

tool結果・context・model出力をharnessが次callへ接続できる。core内部再結合は未観測。

## F — 形成循環

task successとefficiencyを形成圧力として観測するが、個々のruntime状態差がどのweight更新へ帰属するかは未観測。

## v1からの訂正・保持

v1の「長期task stateを外部状態として整理」は維持。ただし、外部loopをcore再作用の証拠として使わない。

## 未観測

internal sequence/depth/width、latent hypothesis、weak-signal retention、core内dynamic routing。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
