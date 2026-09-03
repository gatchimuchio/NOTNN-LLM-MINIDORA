# K3 / GLM 作用比較索引 v1

- 日付: 2026-09-02
- 目的: K3構文化とGLM構文化を同じ作用座標で横並び参照する
- K3正本: `K3_能力成立作用構文化_v1/`
- GLM正本: `GLM_5_3_能力成立作用構文化_D4_v1/`
- 現行実装契約: `../設計/33_GLM還元_参照計画と並列作業状態_v1.md`

## 1. 最短索引

| 作用 | K3 | GLM | MINIDORA |
|---|---|---|---|
| 局所状態更新 | KDA recurrent state | KDA linear/state layers | `selective_update` / 作業状態 |
| 局所↔大域 | 3 KDA + 1 Gated MLA | 3 KDA + 1 DSA | `HDS多時間尺度政策` + 局所再照合 |
| 過去処理の再利用 | AttnRes depth checkpoint | IndexShareは参照選択を再利用 | checkpoint + `HDS参照計画` |
| 粗い索引 | 明示分離なし | DSA indexer | `HDS参照索引` |
| 索引圧縮 | 明示分離なし | IndexPool 4→1 | `HDS参照索引圧縮(bucket幅=4)` |
| 正確な証拠本文 | MLA context | sparse selected context | `参照記録`正本を再読 |
| 並列状態 | 系列/深さ/幅の三軸 | mHC 4 streams | `HDS並列作業状態` |
| 混合Gate | KDA/MLA/AttnRes/MoE別Gate | mHC Sinkhorn constrained mix | `HDS制約混合行列` |
| 共通作用 | shared experts | shared expert / dense prefix | 既存共通作用 |
| 専門作用 | top-16 routed experts | top-k routed experts | 既存専門作用routing |
| effort | MOPD | reasoning effort | `hds_effort` |
| 最終採否分離 | GRM構造類似 | training/eval criticは外部境界 | `J/HDS`既存境界 |
| 生成先読み | 直接中心成果ではない | MTP | `HDS先行草案検証` |
| blocker後の再作用 | checkpoint/re-entry | long-horizon feedback training | `HDS阻害回復方針` |
| multimodal | modality adapter→text hidden | native multimodal path | `HDS異種入力射影` |
| topology/政策分離 | 構造観測中心 | 5.2→5.3でpost-training差が顕在 | 構造moduleと`HDS多時間尺度政策`を分離 |

## 2. K3が先に与えたもの

K3のD4構文化からMINIDORAが先に持ち帰った本体は次。

1. 確定前状態を捨てず保持する。
2. 局所更新と大域再照合を別作用にする。
3. 過去checkpointへ戻る。
4. 共通作用と複数専門作用を併存させる。
5. Gateを早期採否ではなく寄与調整にも使う。
6. effortを同一核の運用政策として切り替える。
7. 最終採否をJ/HDSへ分離する。

GLM還元ではこれを別名で重複実装しない。

## 3. GLMで新しく細分化できたもの

### 3.1 「記憶」を一括りにしない

GLMのDSA / IndexPool / IndexShareを通すと、参照系は少なくとも次へ分けた方がよい。

```text
正本証拠 M_ARCHIVE
!=
request-local作業 M_WORKING
!=
粗い検索索引 M_INDEX
!=
現在の参照選択 M_RETRIEVAL_PLAN
```

K3で得た「状態を残して再作用する」を、GLMは**何を圧縮してよく、何を正確に保持するか**まで細分化した。

### 3.2 参照選択にも寿命がある

IndexShareから持ち帰る本体は「4層」という数字ではなく、

> 一度選んだ参照対象を毎段再計算せず、条件が変わらない有限期間だけ再利用する。

MINIDORAでは`HDS参照計画`のleaseとして実装する。

### 3.3 並列状態を一つへ早期上書きしない

mHCから持ち帰るのは4つの意味役割ではない。

```text
複数lane保持
→ 制約付きread mix
→ 作用
→ 制約付きwrite mix
```

という状態伝達様式だけを持ち帰る。

### 3.4 topologyとpolicyを分ける

GLM-5.2と5.3の関係から、同じpretrained base/構造だけでは最終挙動を説明できないことが見える。

MINIDORAでは、

- 何を保持できるか = 構造
- いつ何回使うか = 運用政策

を別責任にする。

## 4. 重複判定

| GLM観測 | 判定 | 理由 |
|---|---|---|
| KDA selective update | 既存 | K3で取得済み |
| 3:1 local/global | 一般化 | K3でも取得済み、GLMで再確認 |
| shared+routed MoE | 既存 | K3の方が明瞭に取得済み |
| effort | 既存 | K3 MOPD由来実装あり |
| DSA sparse retrieval | 追加 | index→ID選択→正本再読を独立化 |
| IndexPool | 追加 | indexだけの圧縮責任を新設 |
| IndexShare | 追加 | retrieval plan leaseを新設 |
| mHC | 追加 | 独立状態lane + constrained mixingを新設 |
| MTP | 追加・任意 | 生成効率補助として分離 |
| multimodal native path | 境界追加 | adapter後共通表象の契約 |
| long-horizon feedback | 運用追加 | blocker原因別recovery |
| 5.2→5.3 post-training差 | 設計追加 | topology/policy責任分離 |

## 5. コードから見る場合

機械可読の横断台帳:

- `../src/minidora/構文化由来.py`

GLM追加実装:

- `../src/minidora/hds参照計画.py`
- `../src/minidora/hds並列作業状態.py`
- `../src/minidora/hds多時間尺度.py`
- `../src/minidora/hds能力経路_v3.py`

K3既存実装:

- `../src/minidora/k3_functional.py`
- `../src/minidora/k3_hds_native.py`
- `../src/minidora/能力状態差循環.py`
- `../src/minidora/hds局所再照合.py`

## 6. 観測と実装を混同しない

- K3/GLMの公開weight・config・implementationから直接見えるものは観測。
- MINIDORA命令へ置き換えたものは作用射影。
- GLM post-trainingから`BLOCKER_RECOVERY`等へ落としたものはruntime設計推定。
- GLM内部にMINIDORAと同名moduleが存在するとは主張しない。
- GLMの4-laneへMINIDORA独自の意味役割を割り当てたとは主張しない。
