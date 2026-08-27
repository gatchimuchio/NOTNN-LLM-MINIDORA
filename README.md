# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定言語とする非ニューラルネットワーク型の大規模言語模型研究実装である。

現行系は、旧Layer-0前提を外し、外部正本 [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification) `2026-08-27-成立規定-3` を上位基準として構成再現7条件まで再監査したMINIDORA v0.4である。

## 現行模型中核

```text
対象言語状態
  ↓ 言語対応
文脈付き内部状態
  ↓
状態分離・保持
  ↓
一般模型関係 / 形成済み関係 / 参照寄与
  ↓
未確定候補差の共同保持
  ↓
候補共同再照合・再作用・再結合
  ↓
終端成立差
```

標準6関係（意味連続、順序連続、有向関係整合、肯否整合、履歴近接、条件結合）は維持するが、6関係だけを構成再現全体とは扱わない。

## 正式knowledge choice

現行の責任境界は次で固定する。

```text
自然言語 / Data
  ↓
HDS Compiler
  ↓
MINIDORA入力
  ↓
MINIDORA模型核 C
  ↓
MINIDORA出力
  ↓
HDS判断主体 J
  ├─ APPROVE → 外部出力
  ├─ HOLD    → SILENT
  └─ REJECT  → SILENT
```

模型核 `C` はHDS Compilerで構文化された入力を計算し、`MINIDORA出力`を形成する。後段HDS `J` の判断入力は **MINIDORA出力だけ** であり、Question / Candidate / Data / Referenceを直接読み直さない。

HOLD / REJECT後はそこで終端する。後段HDSは再検索・再計算・差し戻し・MINIDORA再起動を行わない。再試行や別手段への切替が必要な場合、それはMINIDORA単体ではなく上位AGI全体HDSの責任である。

外部表示層はSILENTを「分かりません」と表面化してよいが、それはMINIDORAが生成した回答ではなく、**出力不存在状態の表示**である。

詳細: [`設計/28_HDS判断主体_MINIDORA出力Gate_v2.md`](設計/28_HDS判断主体_MINIDORA出力Gate_v2.md)

## 計算経路

```text
日本語命令形P
      ↓ 命令計算降下
計算中間表現 v1
      ↓
計算実行境界 v1
      ↓
計算実行器
```

外部技術語の `Compute IR / ABI` に相当する境界は、日本語正本では **計算中間表現 / 計算実行境界** と呼ぶ。

## HDS Compiler Pipeline

Meaning/Audit Architectureは `v1.2`、意味/計算責任分離Pipelineは `v1.3`。

```text
自然言語
  ↓
意味コンパイル
  ↓
意味HDS-IR（計算P非内包）
  ├─ R / K / 監査
  └─ 計算計画
        ↓
      計算降下
        ↓
      計算中間表現 v1
```

`意味コンパイル()` が意味正本入口。旧 `コンパイル()` は既存Runtime向け互換窓口でのみPを再付与する。

外部DataをMINIDORA入力へ整列する前段正本は `src/minidora/hds入力参照境界.py`。旧 `hds判断参照境界.py` は過去API互換aliasのみである。

## 重要な責任分離

```text
HDS Compiler
!= MINIDORA模型核 C
!= MINIDORA出力
!= HDS判断主体 J
!= 上位AGI全体HDS
!= 計算実行器
!= 外部参照R
```

旧 `Layer0` は現行では計算実行器の互換名であり、LLM模型中核ではない。

## v0.4大規模性

上流規定の **状態域規模 / 関係域規模 / 共有適用規模** の三面で再測定した。

現行判定:

```text
LARGE_SCALE_STATUS = 局所成立候補
```

代表測定値:

| 観測面 | 結果 |
|---|---:|
| 試験状態 | 384 |
| 識別内部状態 | 384 / 384 |
| 試験言語体系 | 3 |
| 10,000文字状態 | PASS |
| 履歴深さ256 | PASS |
| 一般関係族 | 17 / 17 |
| 関係構造 | 544 / 544識別 |
| 方向差 | 成立差へ到達 |
| 肯否差 | 成立差へ到達 |
| 履歴順序差 | 成立差へ到達 |
| 条件結合差 | 成立差へ到達 |
| 共有適用 | 256 / 256 |
| 模型関係実体 | 6 |

この `大規模` は、上流規定どおり比較集合・版・観測条件に依存する**規模記述**である。GPT/Qwen/Kimi等の現代ニューラルLLMとのparameter数・計算量・benchmark性能の同等性を意味しない。

正本記録: [`評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md`](評価/MINIDORA_v0_4_規模測定_v2_2026-08-26.md)

## 旧成果の扱い

2026-08-22の `PROTOTYPE COMPLETE`、過去GPQA実測、K3横断構文化、旧Layer-0契約、v0.3 Runtimeは履歴として保持する。

2026-08-27の「後段HDSが元Data/Referenceを再審査する」実装・GPQA測定も失敗観測として履歴保持するが、現行責任境界へは継承しない。

旧性能値を現行模型核・現行HDS出力Gateの性能へ無言転用しない。

## 試験

```bash
python -m unittest discover -s tests -v
python tools/規模測定.py
```

CIはUbuntu / Windows × Python 3.11–3.14で、package install、repository consistency audit、compileall、unit tests、v0.4規模測定、module CLI smoke、console script smokeを確認する。

## 文書入口

- [`設計/README.md`](設計/README.md) — 現行設計正本ガイド
- [`設計/28_HDS判断主体_MINIDORA出力Gate_v2.md`](設計/28_HDS判断主体_MINIDORA出力Gate_v2.md) — MINIDORA出力からHDS終端Gateへの現行正本
- [`設計/27_HDS判断主体_MINIDORA終端接続_v1.md`](設計/27_HDS判断主体_MINIDORA終端接続_v1.md) — 誤接続の失効記録
- [`REFERENCES.md`](REFERENCES.md) — 外部正本・参照階層
- [`構文化/README.md`](構文化/README.md) — 観測・再構成成果
- [`評価/README.md`](評価/README.md) — 実測・完成判定履歴

## ライセンス

本リポジトリは成果物種別でライセンスを分離する。

- **ソースコード、Runtime、Compiler、ライブラリ、テスト、ツール、CI・パッケージ設定**: Apache License 2.0 (`Apache-2.0`)
- **仕様、設計、理論、論文、解説、図表、構文化・評価文書、README等の説明文書**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`)

これはリポジトリ全体をどちらか任意で選べるデュアルライセンスではない。成果物の種類ごとに適用ライセンスを分ける。

適用範囲は `LICENSE`、正式条件は `LICENSE-APACHE-2.0` / `LICENSE-CC-BY-4.0`、帰属・第三者由来物は `NOTICE` を参照する。
