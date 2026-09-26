# MINIDORA ベンチ入口

GPQA Diamond全数測定は重いため、通常pushでは自動起動しない。

現行の正本起動経路:

- workflow: `.github/workflows/GPQA現行測定.yml`
- trigger: `workflow_dispatch`
- 実行: `python tools/正本評価.py gpqa-e2e --out gpqa_e2e.json`
- 対象: GPQA Diamond 198問
- 中核入口: `HDS駆動コア.選択実行`
- 保存: GitHub Actions artifact `minidora-gpqa-e2e-canonical`

実測の巨大JSONや分割参照束はdefault treeへ固定しない。現行正本値・再現条件は`評価/`の正本資料に保持し、個票はActions artifactへ分離する。

benchmarkはMINIDORA本体の汎用能力を観測するために使い、問題固有機能を中核へ追加する入口にはしない。

現行評価系列は [`../現行正本.md`](../現行正本.md) と [`../評価/評価契約_v3.md`](../評価/評価契約_v3.md) を正とする。
