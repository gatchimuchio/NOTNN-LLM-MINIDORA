# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定言語とする非ニューラルネットワーク型の大規模言語模型研究実装である。

現行系は、旧Layer-0前提を外し、外部正本 [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification) `2026-08-26-成立規定-2` を上位基準として再構成したMINIDORA v0.4である。

## 現行模型中核

```text
対象言語状態
  ↓
言語対応
  ↓
文脈付き内部状態
  ↓
再利用可能な模型側関係
  ↓
成立差
```

内部言語状態は意味語集合だけでなく、意味順序・有向関係・肯否・条件結合を保持する。

標準模型核の再利用可能関係群:

- 意味連続
- 順序連続
- 有向関係整合
- 肯否整合
- 履歴近接
- 条件結合

世界知識、HDS-IR、外部参照、主体状態、計算実行をLLM模型中核そのものへ混入させない。

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
  ├─ R / K / J / 監査
  └─ 計算計画
        ↓
      計算降下
        ↓
      計算中間表現 v1
```

`意味コンパイル()` が意味正本入口。旧 `コンパイル()` は既存Runtime向け互換窓口でのみPを再付与する。

## 重要な責任分離

```text
LLM模型中核
!= 計算実行器
!= HDS-IR
!= 計算中間表現
!= 外部参照R
!= 主体主幹
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

旧性能値を現行模型核の規模・性能へ無言転用しない。

## 試験

```bash
python -m unittest discover -s tests -v
python tools/規模測定.py
```

CIはUbuntu / Windows × Python 3.11–3.14で、package install、repository consistency audit、compileall、unit tests、v0.4規模測定、module CLI smoke、console script smokeを確認する。

## 文書入口

- [`設計/README.md`](設計/README.md) — 現行設計正本ガイド
- [`REFERENCES.md`](REFERENCES.md) — 外部正本・参照階層
- [`構文化/README.md`](構文化/README.md) — 観測・再構成成果
- [`評価/README.md`](評価/README.md) — 実測・完成判定履歴

## ライセンス

Apache License 2.0。著作権表示・NOTICE等の条件は `LICENSE` / `NOTICE` を参照する。
