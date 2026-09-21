# MINIDORA 評価案内

`評価/` は適合・性能・回帰・失敗実測を保持する。履歴ファイルを現在の値で上書きせず、評価系列ごとに正本を分ける。

## 現行正本

| 系列 | 正本 | 値 / 位置づけ |
|---|---|---|
| MINIDORA30 | [GPQA E2E正本](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md) | **30 / 198 (15.15%)** |
| MINIDORA80 | [能力モジュール込みE2E正本](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md) | **80 / 198 (40.40%)** |
| HDS-MINIDORA | [受入正本](HDS_MINIDORA_受入正本_2026-09-17.md) | MINIDORA30 / 80とは別系列 |

全体案内:
- [現行正本群](../現行正本.md)
- [正本系統](../正本系統.md)
- [評価契約 v2](評価契約_v2.md)

## MINIDORA30

```text
GPQA-E2E-LIVE
30 / 198
15.151515151515152%
回答 130 / 198
```

正本資産:
- [Markdown](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [JSON](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.json)
- [SAVEPOINT](../docs/SAVEPOINT_2026-09-09_MINIDORA30.md)

## MINIDORA80

```text
能力モジュール OFF = 29 / 198
能力モジュール ON  = 80 / 198
正答純増           = +51
能力モジュール発火 = 55
退行               = 0
```

正本資産:
- [Markdown](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [JSON](GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.json)
- [SAVEPOINT](../docs/SAVEPOINT_2026-09-09_MINIDORA80.md)

これは模型核単体性能ではなく、能力モジュール込みシステム性能である。

## HDS-MINIDORA

[HDS_MINIDORA_受入正本_2026-09-17.md](HDS_MINIDORA_受入正本_2026-09-17.md) を別系列として保持する。MINIDORA30の30/198、MINIDORA80の80/198をHDS-MINIDORA固有性能へ転記しない。

## GPQA正本運用

2026-09-09以後、正本GPQAでは固定参照資料を禁止する。

禁止:
- 保存済み検索結果
- 問題別固定参照資料束
- 過去run参照の再投入
- 正解情報で選別した参照資料

許可:
- 公式問題集合の同一性確認用キャッシュ
- 同一run内で新規取得した同一参照を共有するcontrolled A/B

全数実測の個票JSONはdefault treeへ固定せず、GitHub Actions artifactへ分離する。

## 履歴

過去の評価・失敗実測は履歴証拠として残すが、現行正本へ無言昇格しない。

代表:
- [prototype baseline](GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json)
- [v0.4再構成受入](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md)
- [能力状態差循環](MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md)
- [最小汎用Core](GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)
- [科学専門能力 Replay](GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)
- [モジュール拡張成立実証](MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [HDS Compiler Pipeline v1.3受入](HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md)

## 区別

```text
言語模型成立
!= 推論機構成立
!= GPQA得点
!= 能力モジュール込み性能
!= 製品完成度
```

評価条件・値・比較可能範囲は各正本ファイルと [評価契約 v2](評価契約_v2.md) を正とする。
