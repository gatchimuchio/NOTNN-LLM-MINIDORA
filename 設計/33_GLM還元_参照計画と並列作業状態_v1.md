# GLM還元 — 参照計画・並列作業状態・多時間尺度 v1

- 日付: 2026-09-02
- 対象: MINIDORA HDS能力経路 v3
- 根拠: `構文化/GLM_5_3_能力成立作用構文化_D4_v1/`
- 比較根拠: `構文化/K3_能力成立作用構文化_v1/`
- 状態: 実装契約
- ライセンス: CC-BY-4.0

## 1. 目的

GLM-5.2 / 5.3 / 5.3-Flashの公開構造およびD4全weight payload監査から得た作用を、neural部品名をコピーせずMINIDORAの非ニューラルHDS能力経路へ還元する。

K3ですでに得た作用は重複実装しない。

```text
K3で獲得済み
- 選択的状態更新
- 局所更新 ↔ 大域再照合
- checkpoint再作用
- 共通作用 + 専門作用
- effort制御
- 候補生成とJ/HDS採否権限の分離

GLMで追加・細分化
- 正本証拠 / 粗い検索索引 / 参照計画 の三分離
- 参照計画の有限再利用
- 索引だけのbucket圧縮
- 複数状態lane + 制約混合
- topologyと運用政策の責任分離
- blocker原因による参照計画失効
- 先行草案 → prefix検証 → rollback
- modality adapter後の共通入力表象境界
```

## 2. 記憶・参照責任の四分離

GLMのDSA / IndexPool / IndexShareをMINIDORAでは次へ射影する。

```text
M_ARCHIVE
  = 正確な参照Data・証拠本文
  = 圧縮しない

M_WORKING
  = request-local作業状態
  = 未確定差・候補共同状態・checkpoint

M_INDEX
  = M_ARCHIVEを探すためだけの粗い索引
  = 圧縮可
  = 証拠としては使わない

M_RETRIEVAL_PLAN
  = 現在選択されている参照ID集合
  = 有限lease
  = 問い・正本revision・証拠状態が変われば失効
```

実装:

- `src/minidora/hds参照計画.py`
- `HDS参照索引圧縮`
- `HDS参照計画作成`
- `HDS参照計画適用`
- `HDS参照計画再利用可能`
- `HDS参照計画消費`
- `HDS参照計画無効化`

### 不変条件

1. 索引bucketの内容を証拠としてJへ渡さない。
2. 索引圧縮で`参照記録.内容`を変更しない。
3. 参照計画はID pointerだけを持つ。
4. 正本revisionが変わった計画を再利用しない。
5. lease切れの計画を再利用しない。

## 3. 局所 / 大域の時間尺度分離

GLM-5.3-FlashのKDA/DSA hybridから、固定部品ではなく作用周期を抽出する。

```text
LOCAL_UPDATE
LOCAL_UPDATE
LOCAL_UPDATE
GLOBAL_RECONCILE / GLOBAL_RETRIEVE
```

MINIDORAでは3:1を成立条件にしない。標準政策として保持し、矛盾・証拠不足・高新規性・参照計画失効があれば周期前でも大域再照合を開く。

実装:

- `src/minidora/hds多時間尺度.py`
- `HDS多時間尺度政策`
- `HDS大域再照合判断`

## 4. 並列作業状態

GLM-5.3-FlashのmHCは、MINIDORAでは「4つの意味役割」として固定しない。

射影するのは次だけ。

```text
STATE_LANE[0..N-1]
↓
CONSTRAINED_READ_MIX
↓
作用
↓
CONSTRAINED_WRITE_MIX
```

実装:

- `src/minidora/hds並列作業状態.py`
- `HDS並列作業状態`
- `HDS制約混合行列`
- `HDS並列状態混合`
- `HDS並列状態読書混合`

標準`N=4`はGLM観測由来の運用初期値であり、意味論上の必須値ではない。

## 5. blocker recovery

GLM-5.2/5.3のlong-horizon post-trainingから、外界feedback後に同じ内部処理を盲目的に反復しない作用を持ち帰る。

MINIDORAでは失敗理由から次の処理を選ぶ。

```text
証拠 / 参照 / provenance / contradiction / observation変化
→ RETRIEVAL_PLANを無効化
→ 次回外界観測で再構築

探索深度 / budget / exhaustion
→ effort引上げ候補

分類不能
→ JへSUSPEND
```

これはGLM内部に同名moduleが存在するという主張ではない。公開post-training構造からMINIDORAへ射影した運用作用である。

## 6. 先行草案

MTPは能力成立の中心原理ではなく生成効率補助として分離する。

```text
DRAFT_AHEAD
↓
VERIFY_PREFIX
├─ 成立 → ACCEPT_PREFIX
└─ 不成立 → ROLLBACK
```

実装: `HDS先行草案検証`

J/HDSの最終採否を代替しない。

## 7. 異種入力境界

GLM-5.3-Flashのnative multimodal pathから、modality固有parserと中央言語処理を分離する。

```text
image / video / other modality
↓ modality adapter
形成済み表象
↓
HDS共通入力表象
↓
MINIDORA中央処理
```

`HDS異種入力射影`は画像・動画そのものを理解しない。外部adapterが形成した表象と出典IDを共通境界へ載せるだけである。

## 8. topology / operating policy分離

GLM-5.2→5.3ではpretrained baseを共有しながらpost-trainingで最終挙動が改善されるため、MINIDORAでも次を分ける。

```text
構造
- archive / index / retrieval plan
- working state / lane
- local/global action

運用政策
- 何回局所更新するか
- いつ大域再照合するか
- leaseを何回使うか
- effortをいつ上げるか
```

政策値を構造成立条件へ固定しない。

## 9. 実行経路

現行標準経路:

```text
HDS適応候補提案実行
↓
HDS能力経路V3候補提案実行
↓
参照正本
├─ HDS参照索引圧縮
├─ HDS参照計画作成
└─ 正本再読
↓
既存HDS能力経路V2
↓
既存の局所観測view / 状態差 / 専門作用
↓
候補PROPOSE
↓
HDS判断主体 J
```

V3はV2を破棄しない。V2の安全境界を内包し、参照計画層を前段追加する。

## 10. 受入条件

1. index bucket化後も正本参照本文が不変。
2. 計画lease切れで再利用不可。
3. 正本revision変化で再利用不可。
4. 4-lane制約混合が決定論的。
5. 混合行列の行列和が許容誤差内で1。
6. 先行草案は最初の不成立prefixでrollback。
7. 異種入力境界はadapter後表象だけを受ける。
8. K3 / GLM由来を同一台帳から比較できる。
9. J/HDSのCOMMIT権限を変更しない。
10. 既存全試験を維持する。
