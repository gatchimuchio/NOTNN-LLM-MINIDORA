# GLM-5.3 系 能力成立作用構文化 D4 v1

- 実施日: 2026-09-02
- 観測深度: D4
- 対象: GLM-5.3 / GLM-5.3-BF16 / GLM-5.3-Flash / GLM-5.3-Flash-BF16 / GLM-5.2 / GLM-5.2-FP8
- 目的: 公開構造と全weight payloadをHDSで作用へ再構成し、MINIDORAへ非ニューラル射影する

## 読む順番

1. `00_統合報告.md` — 結論とD4観測境界
2. `01_GLM作用構文.md` — GLM構造を作用列へ落とした正本
3. `02_K3との差分.md` — K3で既取得の作用とGLMで新規に得た作用を分離
4. `03_MINIDORA還元対応.md` — 現行コードへの還元先
5. `D4_WEIGHT_AUDIT_SUMMARY.json` — 全weight実読監査の機械可読要約

横並び比較は一階層上の `../K3_GLM_作用比較索引_v1.md` を参照する。

## D4監査結果

```text
shard      1028 / 1028
payload    5,495,588,402,008 byte
tensor     471,306
missing    0
failed     0
sha mismatch 0
gap        0
overlap    0
```

GitHub Actions run: `33560618298`

最終aggregateはsuccess。

## 責任境界

D4全payloadを実読したことと、weight内部の各数値に人間可読な意味ラベルを一意に付けたことは同義ではない。

この構文化では、

- weight/config/公開implementationから確定できる構造
- そこから抽出できる作用
- MINIDORAへの構造類似射影
- post-training記述からの運用推定

を分離して記述する。
