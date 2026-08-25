# MINIDORA ベンチ起動入口

GPQA Diamondの現行測定は `.benchmark/GPQA_REQUEST.txt` を更新して `main` へ反映すると自動起動する。

- workflow: `.github/workflows/gpqa_current_measure.yml`
- 実行: `tools/benchmark.py gpqa-diamond`
- 対象: GPQA Diamond 198問
- 出力: `gpqa_current_measurement.json`
- 保存: GitHub Actions artifact `minidora-gpqa-current-measurement`

`workflow_dispatch` も残すが、外部操作環境からdispatchできない場合の迂回は行わない。requestファイル更新を正式な常設起動経路として使用する。

通常の再構築CIは、このrequestファイルだけの変更では起動しない。
