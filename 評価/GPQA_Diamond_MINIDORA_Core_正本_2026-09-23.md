# GPQA Diamond 現行MINIDORA Core 正本 — 2026-09-23

## 結論

**現行MINIDORA CoreのGPQA Diamond汎用E2E性能正本を 29 / 198 として固定する。**

```text
GPQA-E2E-LIVE
29 / 198
14.646464646464647%
```

本値は、HDS-first統合Coreへ既存MINIDORA能力、再観測、再評価、非退行、学習循環を内包した現行Coreを `HDS駆動コア.選択実行` から直接実測した値である。

## 1. 実測由来

- GitHub Actions run: `35825892895`
- workflow: `現行MINIDORA Core GPQA全数・一時実行`
- conclusion: `success`
- benchmark head: `e673e3a6e467d09e6b87c7d151bef72ad9f7fb59`
- Core実装復元点: `7c7abed6f949b9c642e8bc0f490607dd1f67149d`
- aggregate artifact ID: `10736541284`
- aggregate ZIP SHA256: `36a293e399322811511b82d4f67163e9a1835d51f4963b025a41753762e35e3e`
- aggregate JSON SHA256: `953ca65797832366ccac0d49dbf12d65e053008c898ae2a37baee58f9ba4893a`

benchmark headには測定用一時workflowが含まれる。測定後に一時workflowは撤去済みで、実装本体は `7c7abed...` 復元点と同一である。

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
learning cycle            = Core内包
capability modules        = disabled
scientific specialist     = disabled
legacy HDS supervisor     = disabled
gold                      = Core実行後の採点のみ
```

40 shardを集計し、`0..197` の198件が一度ずつ揃うことを集計jobで検証している。

## 3. 実測結果

| 指標 | 値 |
|---|---:|
| 正答 | **29 / 198** |
| 正答率 | **14.646464646464647%** |
| 回答 | **141 / 198** |
| 回答率 | **71.21212121212122%** |
| COMMIT | 141 |
| SUSPEND | 57 |
| FAIL | 0 |
| 初期継承正答 | 22 |
| 初期継承回答 | 119 |
| 実行内改善 | **7** |
| 実行内退行 | **0** |
| 新規回答 | 22 |
| 基準回答変更 | 0 |
| 追加参照実行 | 78 |
| 拡張採用 | 22 |

## 4. 学習循環の観測

同一run内で、初期継承状態と最終Core状態を記録した。

```text
22正答 / 119回答
↓ Core内包の再観測・再評価・学習循環
29正答 / 141回答
```

観測差:

```text
改善       = +7
退行       = 0
新規回答   = +22
```

これは実行内状態遷移の実測であり、別run間のコード因果差ではない。

## 5. 正本採用

現行正本表記:

```text
現行MINIDORA Core / GPQA-E2E-LIVE / 29/198 / 14.646464646464647%
```

`MINIDORA30` と `MINIDORA80` は削除せず、過去の採用セーブポイントとして履歴へ保持する。

評価条件は [`評価契約_v3.md`](評価契約_v3.md) を正とする。
