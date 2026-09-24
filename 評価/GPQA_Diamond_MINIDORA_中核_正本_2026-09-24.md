# GPQA Diamond 現行MINIDORA中核 正本 — 2026-09-24

## 結論

**現行MINIDORA中核のGPQA Diamond汎用E2E性能正本を 39 / 198 として固定する。**

```text
GPQA-E2E-LIVE
39 / 198
19.696969696969695%
```

本値は、HDS Compiler KernelをMINIDORAの単一意味正本とし、既存MINIDORA能力、再観測、再評価、非退行、学習循環を内包した現行中核を `HDS駆動コア.選択実行` から直接実測した値である。

## 1. 実測由来

- GitHub Actions run: `36006316365`
- workflow: `HDS Compiler Kernel GPQA A/B 一時実行`
- conclusion: `success`
- benchmark head: `613fefedaa38b10756cd50492735c8cee9bb1260`
- 現行中核実装復元点: `8843695c2d4e498009340cadd68814d6cebee819`
- 比較旧資産復元点: `3d4d1052eb2034a8c23c070631e91d7c56d65bd3`
- aggregate artifact ID: `10813391158`
- aggregate ZIP SHA256: `cb3a925d2605f1c85cbcdac1dce7e2734463d58e63229a80abee02094277f68d`
- aggregate JSON SHA256: `32d6eba000bb36dd6878012b0a0f9fba63aded5d80bc8284863934b5ed0f9b8a`

benchmark headには測定用一時workflowが含まれる。測定後に一時workflowは撤去済みで、実装本体は `8843695...` 復元点と同一である。

## 2. 評価条件

```text
benchmark                 = GPQA Diamond
full total                = 198
selected                  = 0..197
GPQA CSV SHA256           = 41d1213cd7a4998605a26c2798500652572007161b3a92817ba46b35befcd305
choice shuffle seed       = 0
OpenAlex                  = disabled
Europe PMC                = enabled
Crossref                  = enabled
Wikipedia                 = en
reference                 = LIVE_ONLY
fixed reference data      = none
Core entry                = HDS駆動コア.選択実行
existing capability       = enabled
learning cycle            = 中核内包
capability modules        = disabled
scientific specialist     = disabled
legacy HDS supervisor     = disabled
gold                      = 中核実行後の採点のみ
```

40 shardを集計し、`0..197` の198件が一度ずつ揃うことを集計jobで検証している。

## 3. 現行実測結果

| 指標 | 値 |
|---|---:|
| 正答 | **39 / 198** |
| 正答率 | **19.696969696969695%** |
| 回答 | **149 / 198** |
| 回答率 | **75.25252525252525%** |
| COMMIT | 149 |
| SUSPEND | 49 |
| FAIL | 0 |
| 初期継承正答 | 32 |
| 初期継承回答 | 124 |
| 実行内改善 | **7** |
| 実行内退行 | **0** |
| 新規回答 | **25** |
| 基準回答変更 | **0** |
| 追加参照実行 | 73 |
| 拡張採用 | 25 |
| Kernel形成回数 | **198 / 198問** |

## 4. Kernel単一正本の観測

現行側198問すべてで `問題コンパイル束` の形成回数を1回に固定し、初期Rと中核実行が同じKernel束を再利用した。

```text
198問
× 1 Kernel形成
= 198回
```

同一問題の意味を下流で再コンパイルして成立させた値ではない。

## 5. 実行内状態遷移

```text
32正答 / 124回答
↓ 中核内包の再観測・再評価・学習循環
39正答 / 149回答
```

観測差:

```text
改善       = +7
退行       = 0
新規回答   = +25
基準回答変更 = 0
```

これは同一run・同一現行側の状態遷移実測である。

## 6. paired旧資産比較

同じworkflow内で旧資産 `3d4d1052...` と現行実装 `8843695c...` を問題単位で交互順にLIVE実行した。

| 指標 | 旧資産 | 現行中核 | 差 |
|---|---:|---:|---:|
| 正答 | 21 | **39** | **+18** |
| 回答 | 141 | **149** | +8 |
| 初期全候補被覆 | 190 | **195** | +5 |
| 最終全候補被覆 | 191 | **197** | +6 |
| 初期取得資料 | 2560 | 2381 | -179 |

問題別では、旧不正答→現行正答が26件、旧正答→現行不正答が8件、正答純増は18件だった。

両側の参照取得は独立LIVEであり、固定参照A/Bではない。この比較は同一workflow内のpaired性能スナップショットであって、コード変更だけの純粋因果差とは扱わない。

## 7. 正本採用

現行正本表記:

```text
現行MINIDORA中核 / GPQA-E2E-LIVE / 39/198 / 19.696969696969695%
```

`MINIDORA30` と `MINIDORA80` は削除せず、過去の採用セーブポイントとして履歴へ保持する。

評価条件は `評価契約_v3.md` を正とする。
