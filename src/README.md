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
| `模型.py` | v0.4由来の能力部品・互換実装 |
| `能力状態差循環.py` | v0.5現行標準能力模型核。状態差→次作用→新状態差の循環 |
| `模型_v05.py` | v0.5公開統合窓口。厳密言語模型核と能力状態差模型核を分離公開 |
| `runtime.py` | 二核・計算実行器の統合。標準能力核は状態差起動型 |
| `hds_compiler_v1.py` | 公開HDS Compiler Architecture v1.3 / Pipeline v1.4 |
| `hds_compiler_action_delta.py` | 作用→状態差→後続利用の構文化 |
| `hds_compiler_records_v1_3.py` | 作用差分構造の型 |
| `hds_compiler_pipeline_v1_4.py` | 意味IR・計算計画・作用差分構造の並列束 |
| `hds_model_projection.py` | HDS作用差分型→MINIDORA能力作用型の有限射影 |
| `hds_choice_runtime.py` | 正式能力経路・実測統計・HDS出力境界 |
| `hds判断主体.py` | MINIDORA能力出力の後段判断門 |
| `計算中間表現.py` | 計算専用中間表現 |
| `計算実行器.py` | 決定論的計算 |
| `layer0.py` | 旧API互換 |

既存英字ファイル名は互換性を壊さない形で段階移行する。新規独自内部概念名は日本語を正本とする。

## 言語模型成立規定

- https://github.com/gatchimuchio/LLM-Constitutive-Specification
- `2026-08-28-成立規定-8`
- `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## 能力状態差循環

v8観測単位:

```text
状態担体 / 作用 / 状態差 / 後続利用 /
参照変更 / 経路変更 / 計算量変更 /
再参照 / 再結合 / 循環尺度
```

HDS Compilerは作用・状態差・後続利用を構文化する。MINIDORA能力状態差模型核は、その構造と能力作用の前後差を使って次作用を選ぶ。

```text
一次能力作用
↓
候補状態差
↓
差なし → 終了
差あり → 次作用選択
          ↓
         再作用
          ↓
         新状態差
```

実装上の重要境界:

- 同一証拠を段階名だけ変えて再加点しない。
- 状態差が無ければ再作用しない。
- HDS Compilerの後続利用に未確認追加条件が残る場合は発火させない。
- Compiler固有型を能力核の内部正本にしない。
- 能力得点・作用差分を厳密言語模型確率へ混入しない。

局所正本: `../設計/30_MINIDORA能力状態差循環_v1.md`

## 現行能力実測

2026-08-28 GPQA Diamond全198問:

```text
checkpoint再活性   = 134
大域再照合         = 134
候補横断更新       = 21
専門作用起動       = 0
current正答         = 16 / 198
controlled baseline = 22 / 198
```

したがって、機構実発火は合格、GPQA能力改善は不合格。

詳細: `../評価/MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md`

## 履歴互換

`runtime_v03.py`、`旧_layer0_v03.py`、旧Pipeline v1.3、v0.4模型・評価は履歴互換のため保持する。
