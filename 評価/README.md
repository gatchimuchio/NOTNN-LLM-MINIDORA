# MINIDORA 評価案内

`評価/` は**現行正本と、現行能力に直接対応する受入証拠**を保持する。
過去の作業ログ・旧ベンチ個票・旧セーブポイントはGit履歴へ委ね、default treeへ重複保存しない。

## 現行正本

| 系列 | 正本 | 値 / 位置づけ |
|---|---|---|
| MINIDORA30 | [GPQA E2E正本](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md) | **30 / 198 (15.15%)** |
| MINIDORA80 | [能力モジュール込みE2E正本](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md) | **80 / 198 (40.40%)** |
| HDS-MINIDORA | [受入正本](HDS_MINIDORA_受入正本_2026-09-17.md) | MINIDORA30 / 80とは別系列 |

機械可読正本:
- [MINIDORA30 JSON](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [MINIDORA80 JSON](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json)
- [HDS非退行受入 JSON](GPQA_Diamond_HDSv3_MINIDORA30非退行受入_2026-09-17.json)

評価条件:
- [評価契約 v2](評価契約_v2.md)
- [旧英字名互換](BENCHMARK_CONTRACT_v2.md)

## 履歴

採用された開発正本の節目と過去コードの復元commitは [開発正本履歴](../開発正本履歴.md) を正とする。

過去runの個票、旧Replay、旧失敗実験、開発途中の性能記録はdefault treeへ残さない。必要な場合は対応commitから復元する。

## 現行能力の受入証拠

各現行能力の局所受入記録は、対応する `設計/` と `tests/` の補助証拠として保持する。
これらを模型核全体の性能正本へ読み替えない。
