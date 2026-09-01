# 03 MINIDORA還元対応

## 1. 還元先一覧

| GLM側 | 作用 | MINIDORA還元先 | 状態 |
|---|---|---|---|
| KDA | 局所状態更新 | `k3_functional.MemorySystem.selective_update` / 作業状態 | 既存 |
| 3 KDA + 1 DSA | 多時間尺度 | `hds多時間尺度.py` | 追加 |
| DSA indexer | 粗索引→参照ID選択 | `hds参照計画.py` | 追加 |
| IndexPool | 索引のみbucket圧縮 | `HDS参照索引圧縮` | 追加 |
| IndexShare | 参照計画有限再利用 | `HDS参照計画` | 追加 |
| mHC | 並列lane保持 | `hds並列作業状態.py` | 追加 |
| Sinkhorn mix | 制約付きread/write混合 | `HDS制約混合行列` | 追加 |
| dense→MoE | 共通処理→専門分岐 | 既存能力作用経路 | 既存再利用 |
| shared+routed experts | 共通+専門作用 | 既存専門作用routing | 既存再利用 |
| effort | 予算選択 | `hds_effort.py` | 既存再利用 |
| MTP | 草案先行→検証→rollback | `HDS先行草案検証` | 追加・任意 |
| multimodal path | adapter後共通表象 | `HDS異種入力射影` | 追加・境界 |
| long-horizon feedback | blocker別再作用 | `HDS阻害回復方針` | 追加 |
| 5.2→5.3 post-training | topology/policy分離 | `HDS多時間尺度政策`を構造から分離 | 追加設計 |

## 2. 現行実行経路への接続

```text
HDS駆動選択実行
↓
HDS適応候補提案実行
↓
HDS能力経路V3候補提案実行
↓
HDS参照索引圧縮
↓
HDS参照計画作成
↓
HDS参照計画適用
↓
HDS能力経路V2候補提案実行
↓
既存の局所観測view / 状態差 / 専門作用
↓
候補PROPOSE
↓
J/HDS COMMIT or SUSPEND
```

V3はV2を削除しない。V2をworkerとして内包し、参照計画層を追加した。

## 3. 実行系へ直結したもの

現在の標準適応候補経路で実際に通るもの:

- `HDS参照索引圧縮`
- `HDS参照計画作成`
- `HDS参照計画適用`
- `HDS参照計画消費`
- blocker時の`HDS阻害回復方針`
- evidence系blocker時の`HDS参照計画無効化`

## 4. 実装済みだが既定挙動へ強制していないもの

次は作用部品として実装済みだが、現行候補得点を無監査に変えないため標準評価へ強制注入していない。

- `HDS並列作業状態`
- `HDS制約混合行列`
- `HDS並列状態読書混合`
- `HDS先行草案検証`
- `HDS異種入力射影`
- `HDS大域再照合判断`の周期値による強制再取得

理由:

1. mHCの4 laneにMINIDORA意味役割を勝手に割り当てる根拠はない。
2. MTPは生成効率補助であり、候補判断の意味作用へ強制混入させない。
3. multimodalはadapter実装が別責任。
4. 3:1周期は観測由来初期値でありMINIDORA成立条件ではない。

## 5. K3由来と統合されたもの

GLMで再観測されたがK3由来実装を正本として維持するもの:

- selective state update
- local/global separation
- checkpoint/re-entry
- shared/common action
- specialist routing
- effort control
- candidate generation / J authority separation

これらは`src/minidora/構文化由来.py`でK3/GLM双方から同じMINIDORA作用へ到達する形で記録する。

## 6. 参照しやすさ

### 人間向け

- `../K3_GLM_作用比較索引_v1.md`

### 機械向け

- `../../src/minidora/構文化由来.py`
- `構文化還元一覧`
- `構文化還元検索(模型="K3")`
- `構文化還元検索(模型="GLM")`

## 7. 非主張

この還元は次を主張しない。

- GLMとMINIDORAが内部数値計算として同一。
- GLM weight各値の意味を完全に復号した。
- GLM mHCの4 streamがMINIDORAの特定4意味状態に対応する。
- GLMのpost-training moduleがMINIDORAの`HDS阻害回復方針`とliteralに同一。
- MTPが知能成立の中心作用である。

還元対象は公開構造から抽出した機能的・因果的作用である。
