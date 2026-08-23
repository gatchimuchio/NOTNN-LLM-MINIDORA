# MINIDORA 性能改善 v0.7 作業記録 — 2026-08-23

## 状態

```text
IMPLEMENTED
REGRESSION FIXTURES ADDED
BENCHMARK PENDING
```

本記録は `31 / 198 = 15.6565657%` のv0.6系実測で露出した候補識別失敗に対する一般能力改修を記録する。新しいGPQAスコアは、同一198問の再実測が完走するまで宣言しない。

## 観測した失敗

v0.6系実測では、APPROVEした128問中31問正解で、回答時正答率は24.21875%だった。GPQA Diamondは4択であり、候補識別が有効に働いているとは評価しにくい。

候補診断を再解析すると、正解候補の得点順位は1位から4位へほぼ均等に分布し、証拠得点とgraph得点の単純な重み変更だけでは改善しなかった。

実装経路を監査すると、候補ごとの検索queryで取得した資料にも `query_choice:*` / `query_kind:*` provenanceが付与される一方、Data→HDS-IR→K投入後は通常の資料と同じ強度で候補証拠へ利用されていた。

これは「候補を検索語へ含めたため取得できた」という選択条件と、「その資料が候補の真偽を独立に支持する」という証拠価値を分離できていない。

## v0.7 改修

対象: `src/minidora/hds_data_k.py`

- R側の `source confidence` と検索選択からの `retrieval independence` を分離した。
- `query_choice:*` を持ち、候補指定query (`choice` / `fallback_choice` / `fallback_choice_only`) からだけ取得された資料は補助証拠へ減衰する。
- 同一資料が `structured` / `focus` / `entity` 等の候補非依存queryからも取得されている場合は従来強度を維持する。
- Fact provenanceへ `retrieval_independence:*` を残し、監査可能にした。
- GPQA問題番号、gold、正答ラベル、設問固有文字列は参照しない。
- `NO_GUESS` / `SUSPEND` 境界は変更しない。

### なぜ完全除外ではなく補助証拠か

候補指定検索で得た資料にも、検索語を超える関係・状態・因果情報が存在し得るため、資料自体を無効化しない。一方、候補語と問い語の一致は検索条件によって事前選択されているため、独立検索資料と同格には扱わない。

## 回帰fixture

`tests/test_hds_source_confidence.py` に以下を追加した。

- 候補指定queryだけで発見した資料は `retrieval_independence = 0.25` となる。
- source confidenceとは別軸として保持する。
- 同一資料が候補非依存queryでも発見された場合は `retrieval_independence = 1.0` に戻る。
- 従来のR信頼係数×HDS値状態confidence契約を維持する。

## 測定

`.github/workflows/gpqa_current_measure.yml` をRuntime変更PRでも起動するよう復元した。

再測定では少なくとも次を比較する。

- correct / 198
- answered / SUSPEND
- answered accuracy
- candidate diagnostics
- retrieval / Data compile failure

性能改善と判断するには、単なる回答率増加ではなく、正答数または回答時正答率が実際に改善していることを確認する。
