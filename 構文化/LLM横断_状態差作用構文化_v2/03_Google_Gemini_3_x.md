# Google Gemini 3.x — 状態差作用構文化 v2

- 観測深度: D2 / closed multimodal
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `03_Google_Gemini_3_x.md`。multimodal、long context、thinking level/config、tool capabilityを公開面から観測。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

core内部stateとmodal統合stateは未観測。外部から渡す入力modal・context・thinking設定は観測。

## A — 作用

公開thinking仕様では、Gemini 3系はrequest complexityに応じてreasoning effortを動的調整し、`thinking_level` で外部からも条件指定できる。tool/function callingはproduct/runtime作用。内部operatorは未観測。

## Δ — 状態差

入力の複雑さまたはthinking設定差により可観測な計算努力条件が変わり得る。ただし内部で何のstate差を検出し、どの機構で計算量を変えるかは未観測。

## D — 後続依存

request condition / thinking levelがreasoning effortへ影響するというAPI-level依存は観測できる。内部state→次operatorの依存は未観測。

## P — 状態依存の経路変化

compute effortが入力複雑性と設定に応じて変化することは公開仕様にあるが、内部path topology/選択規則は未観測。これをlatent loopや明示checkpoint再活性の証拠にしない。

## R — 再参照・再利用の尺度

長contextの再利用能力は可観測だが、内部でexplicit re-reference/recurrent loopがあるとは断定しない。

## C — 再結合

multimodal integration topologyは未観測。tool結果統合はruntime/product層。

## F — 形成循環

版依存/posttrainingは観測、recipe全量は未観測。

## v1からの訂正・保持

v1の「reasoning effort=同じ関係へ何回再作用するか」は強すぎるので撤回。公開情報から言えるのは、request complexityとthinking_levelに応じたtest-time reasoning effort調整まで。内部で何回・何を再作用するかは未観測。

## 未観測

modality integration topology、internal thinking、latent recurrence、sequence/depth/width。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
