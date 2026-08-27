# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定言語とする非ニューラルネットワーク型Language Model / LLM研究実装である。

現行版は **v0.5.0**。上位正本 [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification) `2026-08-28-成立規定-7` / commit `debb83e091a705a5eac09ef4fb97a5b36305db6d` を参照する。

## v0.5の核心

v7に合わせ、**厳密LM性と推論能力を分離**した。

```text
[厳密LM核]
完全言語状態空間
+ 持続模型状態
→ exactに正規化された条件分布
→ chain rule + EOS
→ 完全系列確率

[能力模型核]
Question / Candidate / Data
→ 関係・証拠・候補差
→ knowledge choice
```

既存の候補scoreをsoftmax等で確率へ変換してLMを名乗る方式は採らない。

## 厳密LM核

`src/minidora/言語確率法則.py` に非ニューラル・決定論的な有限n-gram / finite-state成立形を実装する。

特徴:

- Python標準ライブラリのみ。
- `Fraction` によるexact rational probability。
- NFKC Unicode文字 + `UNK/BOS/EOS`。
- additive smoothing。
- 各prefix条件分布は厳密に1へ正規化。
- 系列確率はchain ruleとEOSで計算。
- 全文脈でEOS確率に正の下限を持ち、可変長の確率質量を閉じる。
- 模型状態をJSON互換辞書へ保存・復元可能。
- 同一形成資料なら順序に依存せず同じSHA-256。
- samplingなし。必要な選択は決定論的。

`最小厳密言語模型()` は世界知識を持たない `UNK/EOS` priorで、**厳密LM法則の最小成立確認**だけを担う。能力やLargeを意味しない。

## Runtime

`ミニドラ()` は二核を別保持する。

```python
body.言語模型核   # MINIDORA厳密言語模型
body.能力模型核   # v0.4由来の候補・関係評価核
body.模型核       # 能力模型核の後方互換alias
```

主要API:

```python
body.言語確率("文章")
body.次記号分布("接頭辞")
body.言語模型監査()
body.言語評価("質問", ("候補A", "候補B"))  # 能力側
```

## knowledge choice / HDS

既存knowledge choiceは能力側として維持する。

```text
自然言語 / Data
→ HDS Compiler
→ MINIDORA能力模型核
→ MINIDORA出力
→ HDS判断主体
  ├─ APPROVE → OUTPUT
  ├─ HOLD    → SILENT
  └─ REJECT  → SILENT
```

HDS候補score・参照寄与を厳密LM確率へ自動昇格しない。

## 計算経路

```text
日本語命令形P
→ 計算中間表現 v1
→ 計算実行境界 v1
→ 計算実行器
```

旧 `Layer0` は計算実行器の互換名であり、LM核ではない。

## 能力・Large・呼称

```text
厳密LM成立
!= 高推論能力
!= GPQA高得点
!= Large
!= 現代LLM呼称適合
```

v0.4の三面規模測定 `局所成立候補` は履歴として保持するが、v0.5へ自動継承しない。Largeはv7規模プロファイルで再監査対象とする。

## 現在の受入状態

```text
v0.5厳密LM核              = PASS
厳密正規化 / EOS終端       = PASS
模型状態保存・復元          = PASS
Runtime二核分離             = PASS
v0.4 knowledge choice回帰   = CI監査
GPQA / 推論能力              = 別評価
Large / 現代LLM呼称         = 再監査要
製品・最終完成               = 別関門
```

## 試験

```bash
python tools/repository_consistency_check.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはUbuntu / Windows × Python 3.11–3.14で確認する。

## 文書入口

- [`設計/README.md`](設計/README.md)
- [`設計/02_大規模言語模型成立契約.md`](設計/02_大規模言語模型成立契約.md)
- [`REFERENCES.md`](REFERENCES.md)
- [`構文化/MINIDORA_v0.5/README.md`](構文化/MINIDORA_v0.5/README.md)
- [`評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md`](評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md)

## ライセンス

- **ソースコード、Runtime、Compiler、ライブラリ、テスト、ツール、CI・パッケージ設定**: Apache License 2.0 (`Apache-2.0`)
- **仕様、設計、理論、論文、解説、図表、構文化・評価文書、README等**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`)

これはデュアルライセンスではない。適用範囲は `LICENSE`、正式条件は `LICENSE-APACHE-2.0` / `LICENSE-CC-BY-4.0`、帰属は `NOTICE` を参照する。
