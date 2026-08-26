# MINIDORA v0.4 再作用P0 GPQA実測 — 2026-08-26

## 1. 測定

- benchmark: GPQA Diamond 198問
- workflow run: `32912122831`
- job: `98008228397`
- artifact: `9587195383`
- artifact digest: `sha256:dcdb28cd33729e508d44fad4164482284f18c42e2f422b7b43a0874ea7988563`
- target commit: `284a48870593c9bf55d577098cb9741fd86f0a98`
- OpenAlex: disabled

## 2. 数値

| 指標 | 実測 |
|---|---:|
| 正答 | 22 / 198 |
| 正答率 | 11.1111111% |
| 回答 | 122 / 198 |
| 回答率 | 61.6162% |
| 回答時正答率 | 18.0328% |
| SUSPEND | 76 |
| retrieval empty | 0 |
| 取得文書 | 2,714 |
| Data compile | 2,714 |
| Data compile fail | 0 |
| K facts added | 97,972 |
| evidence facts | 115,421 |
| blocked evidence | 0 |

P0内部指標:

| 指標 | 実測 |
|---|---:|
| working relations created | 114,443 |
| working relations reused | 0 |
| working relations promoted to K | 0 |
| checkpoint count | 594 |
| checkpoint reactivations | 0 |
| global reconciliations | 0 |
| candidate cross updates | 792 |
| temporary working evidence | 0 |

## 3. 旧19/198との差の扱い

直前の現行v0.4実測は19/198 = 9.596%だった。本runは22/198 = 11.111%で+3問だが、**P0改善とは扱わない**。

理由:

- working relations reused = 0
- temporary working evidence = 0
- checkpoint reactivations = 0
- global reconciliations = 0

つまりP0の再作用経路は実GPQAで一度も発火していない。

一方、外部Rの取得文書数・source分布はrun間で変動する。従って+3問はlive retrieval差を含み、P0因果へ帰属できない。

## 4. P0から確定したこと

### 成立

- Working Relation Storeは全問で形成できた。
- persistent canonical Kへ作業関係を自動昇格しなかった。
- checkpointを監査記録として形成できた。
- 既存unknown / contradiction / direct relation等の境界を壊さなかった。

### 未成立

P0の再利用条件を、

> 阻害された同一無修飾正極性有向関係が二独立出典で完全一致

へ限定したため、実GPQAでは再利用0だった。

さらにblocked evidence自体が0だったため、主要損失地点はHDS Data投入時のblockingではない。

## 5. 候補識別診断

artifactの198問candidate diagnosticsを再集計すると、正解候補の合計得点順位は次だった。

- 1位: 44 / 198
- 2位: 52 / 198
- 3位: 53 / 198
- 4位: 49 / 198

また、

- 全候補 evidence score = 0: 62問
- 全候補 graph score = 0: 124問
- top score tie: 64問

だった。

従って主要不足は、単純な「弱い証拠の廃棄」だけではない。

**取得Dataから問題・候補間の識別可能な意味関係を形成し、候補差へ接続する作用そのものが不足している。**

## 6. 次段

P0の安全境界は残す。

次のP1では、K3 / OLMo / Qwen / DeepSeekの第二巡作用構文化から、

```text
全文処理
↓
局所作業域
↓
局所関係の再構文化
↓
大域候補状態へ再接続
```

を実装する。

また、今後のGPQAは異なるrun間のlive R値だけで改善判定せず、同一取得資料をbaseline/currentへ同時に流すcontrolled A/Bを標準とする。
