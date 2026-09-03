# MINIDORA ベンチ入口

GPQA Diamond全数測定は重いため、通常pushでは自動起動しない。

現行の正式起動経路:

- workflow: `.github/workflows/gpqa_current_measure.yml`
- trigger: `workflow_dispatch`
- 実行: `python tools/benchmark_formal.py gpqa-diamond --controlled-ab --out gpqa_current_measurement.json`
- 対象: GPQA Diamond 198問
- 保存: GitHub Actions artifact `minidora-gpqa-current-measurement`

benchmarkはMINIDORA本体の汎用能力を観測するために使い、benchmark固有機能をcoreへ追加する入口にはしない。

現行セーブポイントの実測値は [`../評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](../評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md) を参照する。
