# K3 HDS日本語全公開データコンパイル v6.0 — 固定スナップショット保存

このディレクトリは、ミニドラ開発用に実施したK3 HDS日本語コンパイル成果 v6.0 の恒久アーカイブ台帳である。

## 完了済み範囲

- HF: `moonshotai/Kimi-K3`
- 固定revision: `c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721`
- HF files: 114
- 公式GitHub/Tech Blog等を加えた公開source item: 126 / 126
- 公開source byte: 1,561,002,449,957 / 1,561,002,449,957
- weight shard: 96 / 96
- tensor: 497,220 / 497,220
- tensor HDS日本語意味構文: 497,220 / 497,220
- 未処理item: 0
- 未処理byte: 0
- weight identity mismatch: 0
- 当該固定母集合の最終判定: PASS

## 重要な境界

これは上記HF revisionを固定母集合とした完全成果であり、Hugging Faceの可変`main`を永久に代表するものではない。
v6.0作成後にHF側へ追加されたcommit・評価資料等は、このv6.0には含まれない。
したがって名称上の「全公開データ」は**固定した母集合に対する全数完遂**を意味する。

## 成果物

大容量の正本ZIPはgit履歴へ直置きせず、同一GitHubリポジトリのRelease
`k3-hds-v6.0-c5d1dd4` に恒久保存する。

- `audit.json`: 最終全数監査
- `mother-set.json`: 母集合正本
- `K3_HDS日本語全公開データコンパイル_v6_0.zip.sha256`: 正本ZIP SHA-256
- Release asset `K3_HDS日本語全公開データコンパイル_v6_0.zip`: HDS日本語意味構文を含む成果正本

ZIP SHA-256:
`0473757f3d1de7bee7798b81e43356a9c245422bf8a3afaba3178c20ea997fab`
