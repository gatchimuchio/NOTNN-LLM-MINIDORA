# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定言語とする非ニューラルネットワーク型の大規模言語模型研究実装である。

現行系は、旧Layer-0前提を外し、外部正本 [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification) `2026-08-26-成立規定-2` を上位基準として再構成したMINIDORA v0.4である。

## 現行中核

LLM模型中核:

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

計算経路:

```text
日本語命令形P
      ↓ 命令計算降下
計算中間表現 v1
      ↓
計算実行境界 v1
      ↓
計算実行器
```

HDS Compiler Pipeline:

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

外部技術語でいう `Compute IR / ABI` に相当する境界は、日本語正本では **計算中間表現 / 計算実行境界** と呼ぶ。

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

HDS-IRは意味Projection・運用入力・監査履歴である。計算中間表現は意味解釈後の実行専用表現であり、HDS-IRをそのまま実行形式とは扱わない。

## 計算中間表現 / 実行境界 v1

実装:

- `src/minidora/計算中間表現.py`
- `src/minidora/計算実行境界.py`
- `src/minidora/命令計算降下.py`
- `src/minidora/HDS計算降下.py`
- `src/minidora/計算実行器.py`

主な境界:

- 旧Pの `$a` のような文字列参照は、降下時に型付き `状態値("a")` へ変換する。
- 計算実行境界は `$`、自然言語、HDS語彙を解釈しない。
- `即値` / `状態値` / `状態住所` を型で分離する。
- 未確定HDS入力は計算中間表現へ昇格しない。
- 同一の計算中間表現と初期状態から同一結果を返す。

設計正本: [`設計/25_計算中間表現_実行境界_v1.md`](設計/25_計算中間表現_実行境界_v1.md)

## HDS Compiler Pipeline v1.3

Meaning/Audit Architectureは `v1.2` を維持し、Pipelineを `v1.3` とする。

- `意味コンパイル()` が意味正本入口。
- 意味HDS-IRは `手順=None`、計算初期状態を内包しない。
- `コンパイル束()` は意味IRと計算計画を別フィールドで保持する。
- `計算降下()` は形成済み束のみを受け、自然言語を再解析しない。
- 旧 `コンパイル()` は既存Runtime向け互換窓口で、最外周でのみPを再付与する。
- 独立Data/候補のコンパイルは意味入口を優先し、Pを混入しない。

設計正本: [`設計/26_HDS_Compiler_Pipeline_v1_3.md`](設計/26_HDS_Compiler_Pipeline_v1_3.md)

## 旧成果の扱い

2026-08-22の `PROTOTYPE COMPLETE`、過去GPQA実測、K3横断構文化、旧Layer-0契約、v0.3 Runtimeは履歴として保持する。

ただし、旧性能値を現行模型核の大規模性証拠へ無言転用しない。

### v0.4大規模性

**再測定要**。現行v0.4の大規模性は上流規定に従い、次の3観測面で別途測定する。

- 状態域規模
- 関係域規模
- 共有適用規模

比較集合・対象言語体系・物理規模値も同時に明示し、一点閾値で判定しない。

## 試験

```bash
python -m unittest discover -s tests -v
```

CIはUbuntu / Windows × Python 3.11–3.14で、package install、repository consistency audit、compileall、unit tests、module CLI smoke、console script smokeを確認する。

## 文書入口

- [`設計/README.md`](設計/README.md) — 現行設計正本ガイド
- [`REFERENCES.md`](REFERENCES.md) — 外部正本・参照階層
- [`構文化/README.md`](構文化/README.md) — 観測・再構成成果
- [`評価/README.md`](評価/README.md) — 実測・完成判定履歴

## ライセンス

Apache License 2.0。著作権表示・NOTICE等の条件は `LICENSE` / `NOTICE` を参照する。
