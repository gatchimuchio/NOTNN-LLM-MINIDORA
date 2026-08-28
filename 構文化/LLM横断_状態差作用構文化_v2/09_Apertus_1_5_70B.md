# Apertus 1.5 70B — 状態差作用構文化 v2

- 観測深度: D3相当 / dense multimodal natural experiment
- K3: 対象外
- 状態: 再構文化。構成定義・MINIDORA仕様へ自動昇格しない。
- ライセンス: CC-BY-4.0

## 0. 根拠境界

旧v1 `09_Apertus_1_5_70B.md`。同系decoder geometry、continued pretraining、multimodal mix、vision/audio tokenizer別artifact、posttraining。

本v2では、公開資料が支持しない内部意味や循環を補わない。

## S — 状態担体

中央decoder residual hidden state。異なるmodality前段から中央表象へ接続されるが全topologyは未観測。

## A — 作用

中央Dense/global-attention系変換。modality前処理・thinking/tool modeは境界を分ける。

## Δ — 状態差

decoder層間表象差は後段へ伝播。modality導入による能力差を中央architecture変更へ単独帰属しない。

## D — 後続依存

central decoderでDEPTH_DOWNSTREAM_DEPENDENCY。modal integrationの具体依存は未観測。

## P — 状態依存の経路変化

Dense central path。thinking mode内部path selectionは未観測。

## R — 再参照・再利用の尺度

global attention系のcontext referenceは観測対象だがruntime recurrenceは断定しない。

## C — 再結合

modal frontend→central decoder接続は存在するが具体topology未観測。

## F — 形成循環

continued pretraining + multimodal mix + posttrainingが同系geometryへ能力を追加する自然実験。

## v1からの訂正・保持

v1の形成観測を維持。thinking modeを内部再作用の証拠へしない。

## 未観測

全weight意味、modal integration topology、thinking内部機構。

## 判定

- `STATE_EXISTS` と `STATE_HAS_DOWNSTREAM_EFFECT` を分離する。
- `DOWNSTREAM_EFFECT` と `DYNAMIC_PATH_SELECTION` を分離する。
- `DEPTH_REUSE` / `POSITION_RECURRENCE` / `TURN_HISTORY` / `HARNESS_LOOP` / `FORMATION_LOOP` を同一の再帰へ潰さない。

## 一次資料再照合

現行公開資料との照合は `13_一次資料再照合.md` を参照。
