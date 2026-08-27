# MINIDORA v0.5 再構成記録

日付: 2026-08-28

## 上位基準

- Repository: https://github.com/gatchimuchio/LLM-Constitutive-Specification
- 版: `2026-08-28-成立規定-7`
- commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`

## v0.4からの変更

v0.4は候補・関係・証拠の成立差を「模型核」としていた。v7再監査により、これは推論/knowledge choice能力核であり、厳密Language Model法則そのものではないと再分類した。

v0.5では新規に `src/minidora/言語確率法則.py` を追加する。

```text
厳密LM核
完全言語状態
→ 条件分布
→ chain rule
→ EOS終端
→ 完全系列確率

能力核
Question / Candidate / Data
→ 関係・証拠
→ 候補差
```

## 厳密LM成立形

- 有限n-gram / finite-state。
- Unicode文字を模型記号へ写像。
- 未観測文字はUNK。
- exact `Fraction`。
- additive smoothing。
- EOS確率正。
- 保存・復元可能な持続模型状態。
- sampling非依存。

この方式をLM一般の普遍方式へは昇格しない。

## 旧資産

v0.4構成再現v3、三面規模測定、GPQA実測、HDS接続は削除しない。能力・履歴資料として保持する。

## 現行判定

```text
厳密LM法則             = PASS対象
能力模型                = v0.4互換維持
Large                   = v7で再監査要
現代LLM呼称             = 再監査要
GPQA                     = 能力評価
```
