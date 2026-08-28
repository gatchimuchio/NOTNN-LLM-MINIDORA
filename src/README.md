# ソース実装

`src/minidora/` はMINIDORA実行系の現行実装を保持する。

## 言語規定

- 最上位理論正本: https://github.com/gatchimuchio/cognitive-engineering-foundations
- MINIDORA局所規定: `../設計/00_日本語基底規定_v1.md`
- 規定言語・基底言語・内部意味正本: 日本語
- 外国語: 実務上必要な外部互換境界のみ例外使用

## v0.5主要境界

| 実装 | 責任 |
|---|---|
| `規定参照.py` | 言語模型成立規定v8の版・commit・厳密言語模型・能力作用観測単位の参照 |
| `言語基底.py` | 日本語正本と外国語互換境界 |
| `言語確率法則.py` | 非ニューラル厳密言語模型核 |
| `模型.py` | 能力模型核互換実装 |
| `runtime.py` | 二核・計算実行器の統合 |
| `hds_compiler_v1.py` | 公開HDS Compiler Architecture v1.3 / Pipeline v1.4 |
| `hds_compiler_action_delta.py` | 作用→状態差→後続利用の構文化 |
| `hds_compiler_records_v1_3.py` | 作用差分構造の型 |
| `hds_compiler_pipeline_v1_4.py` | 意味IR・計算計画・作用差分構造の並列束 |
| `hds判断主体.py` | MINIDORA能力出力の後段判断門 |
| `計算中間表現.py` | 計算専用中間表現 |
| `計算実行器.py` | 決定論的計算 |
| `layer0.py` | 旧API互換 |

既存英字ファイル名は互換性を壊さない形で段階移行する。新規独自内部概念名は日本語を正本とする。

## 言語模型成立規定

- https://github.com/gatchimuchio/LLM-Constitutive-Specification
- `2026-08-28-成立規定-8`
- `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## 能力作用

v8観測単位:

```text
状態担体 / 作用 / 状態差 / 後続利用 /
参照変更 / 経路変更 / 計算量変更 /
再参照 / 再結合 / 循環尺度
```

HDS Compilerはこのうち作用・状態差・後続利用を構文化する。実発火は能力実行系の別責任。

## 履歴互換

`runtime_v03.py`、`旧_layer0_v03.py`、旧Pipeline v1.3、v0.4模型・評価は履歴互換のため保持する。
