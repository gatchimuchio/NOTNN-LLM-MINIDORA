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
- ABIは `$`、自然言語、HDS語彙を解釈しない。
- `即値` / `状態値` / `状態住所` を型で分離する。
- 未確定HDS入力は計算中間表現へ昇格しない。
- 同一の計算中間表現と初期状態から同一結果を返す。

設計正本: [`設計/25_計算中間表現_実行境界_v1.md`](設計/25_計算中間表現_実行境界_v1.md)

## HDS境界

現行公開HDS Compilerは引き続き公開Runtime資産として保持する。

現在の `HDS計算降下` は、現行HDS-IRに残る閉包済み互換 `手順` を計算中間表現へ移す移行用境界である。

次段ではHDS Compilerを次へ再設計する。

```text
自然言語
 ↓
HDS semantic frontend
 ↓
意味HDS-IR
 ↓
compute lowering backend
 ↓
計算中間表現
 ↓
計算実行境界
```

この再設計では、`HDSIR.手順` をsemantic IRの恒久責任から外す。

## 旧成果の扱い

2026-08-22の `PROTOTYPE COMPLETE`、過去GPQA実測、K3横断構文化、旧Layer-0契約、v0.3 Runtimeは履歴として保持する。

ただし、旧性能値を現行模型核の大規模性証拠へ無言転用しない。

現行v0.4の大規模性は次の3観測面で別途再測定する。

- 状態域規模
- 関係域規模
- 共有適用規模

## 試験

```bash
python -m unittest discover -s tests -v
```

CIはUbuntu / Windows × Python 3.11–3.14で、

- package install
- repository consistency audit
- compileall
- unit tests
- module CLI smoke
- console script smoke

を確認する。

## 文書入口

- [`設計/README.md`](設計/README.md) — 現行設計正本ガイド
- [`REFERENCES.md`](REFERENCES.md) — 外部正本・参照階層
- [`構文化/README.md`](構文化/README.md) — 観測・再構成成果
- [`評価/README.md`](評価/README.md) — 実測・完成判定履歴

## ライセンス

Apache License 2.0。著作権表示・NOTICE等の条件は `LICENSE` / `NOTICE` を参照する。
