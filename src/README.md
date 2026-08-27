# src

`src/minidora/` はMINIDORA Runtime実装を保持する。

## v0.5主要境界

| Module | 責任 |
|---|---|
| `規定参照.py` | 上位v7版・commit・厳密LM/再現区分の現行参照 |
| `言語確率法則.py` | 非ニューラル厳密LM核。exact条件分布・系列確率・EOS終端・模型状態保存 |
| `模型_v05.py` | v0.5統合facade。厳密LMと能力模型を同時公開 |
| `模型.py` | v0.4由来の候補・関係評価。v0.5では能力模型核互換実装 |
| `runtime.py` | `言語模型核` / `能力模型核` / 計算実行器の統合 |
| `hds入力参照境界.py` | HDS Compiler済Data→能力入力 |
| `hds_model_projection.py` | 能力結果→MINIDORA出力 |
| `hds判断主体.py` | MINIDORA能力出力の後段Gate |
| `計算中間表現.py` | 計算専用IR |
| `計算実行器.py` | 決定論的計算 |
| `layer0.py` | 旧API互換。現行LM核ではない |

## 二核

```text
言語確率法則.py = 厳密LM
模型.py          = 能力評価
```

候補scoreをLM確率へ読み替えない。

## 上位規定

- https://github.com/gatchimuchio/LLM-Constitutive-Specification
- `2026-08-28-成立規定-7`
- `debb83e091a705a5eac09ef4fb97a5b36305db6d`

## Legacy

`runtime_v03.py`、`旧_layer0_v03.py`、v0.4模型・評価は履歴互換のため保持する。
