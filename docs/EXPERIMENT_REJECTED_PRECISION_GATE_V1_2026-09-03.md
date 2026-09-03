# 参照証拠閉包Gate v1 — 破棄ログ

## 状態

**REJECTED / PRODUCT CODE REVERTED**

この実装は回答精度改善を目的に、弱い参照証拠だけでAPPROVEする経路を抑制した実験である。
実測の結果、回答精度はほぼ改善せず、回答能力を大幅に失ったため製品実装として破棄する。

## Gate前の正本

- 基準commit: `b1fd13ac3ff8bee01c4e74e6f62a9e827f00d4c0`
- GPQA Diamond: 24 / 198 = 12.12%
- 回答数: 119 / 198
- 回答精度: 20.17%
- 保留: 79

## Gate後実測

- 製品Gate commit: `9e90f73609eae4e883d6c874f1b19670465f6f93`
- GPQA run: `33526477159`
- GPQA Diamond: 8 / 198 = 4.04%
- 回答数: 39 / 198
- 回答精度: 20.51%
- 保留: 159
- 専門module起動: 0

Gate前比:

- 正答: -16
- 回答数: -80
- 回答精度: +0.34pt
- 保留: +80

## 結論

誤答の主因を「終端Gateが甘いこと」とした仮説は支持されなかった。
Gateを厳格化しても回答済み問題の精度はほぼ変わらず、回答可能数だけが大幅に減少した。
したがって、ボトルネックは終端Gateより前段の意味理解・Data照合・候補差形成側にあると判断する。

## 破棄対象

- `src/minidora/hds_model_projection.py` の参照証拠閉包Gate実装
- `tests/test_参照確定品質.py`

上記製品コードはGate前の正本へ復帰する。

## 保持する監査資産

- `gpqa_precision_gate_v1_measurement.json`
- `評価/GPQA_Diamond_参照証拠閉包Gate_v1_実測_2026-09-02.md`
- 本文書

これらは再採用候補ではなく、失敗仮説と実測結果の監査ログとしてのみ保持する。
