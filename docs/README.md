# MINIDORA ドキュメント案内

`docs/` は補助文書・セーブポイント・公開案内を保持します。MINIDORAの現行設計の正本は [`../設計/`](../設計/) です。

## 初めて見る方へ

まず次の順で読むと、研究履歴に埋もれず現在地を把握できます。

1. [`../README.md`](../README.md) — MINIDORAとは何か、現在できること、主張の境界
2. [`../README.en.md`](../README.en.md) — 英語翻訳版。日本語正本に従属
3. [`../ハッカソン/README.md`](../ハッカソン/README.md) — ハッカソン向けチャット・ニュース・要約・監査層
4. [`../評価/README.md`](../評価/README.md) — 実測と評価系列
5. [`../設計/README.md`](../設計/README.md) — 現行設計正本と詳細読み順
6. [`../REFERENCES.md`](../REFERENCES.md) — 上位正本・参照commit・責任関係

## リポジトリの責任分離

| 場所 | 責任 | 初見向け |
|---|---|---|
| `README.md` | 公開入口・現行状態・主張範囲 | ◎ |
| `README.en.md` | 国際公開用翻訳 | ◎ |
| `ハッカソン/` | デモ・製品化向け専用層 | ◎ |
| `設計/` | 現行意味境界・責任・受入条件 | ○ |
| `評価/` | 適合・性能・回帰・実測証拠 | ○ |
| `src/minidora/` | 実行系の現行実装 | ○ |
| `tests/` | 単体試験・回帰試験 | ○ |
| `docs/` | 補助説明・セーブポイント | ○ |
| `構文化/` | 観測・再構成・構文化履歴 | △ |
| `artifacts/` | 固定取得物・派生成果 | △ |
| `.benchmark/` | benchmark補助資産 | △ |

## 現在の補助文書

- [`SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md) — 最小汎用LLM Core + HDS異常時最小介入を再開地点として固定したセーブポイント。
- [`CORE_IMPROVEMENT_2026-09-01.md`](CORE_IMPROVEMENT_2026-09-01.md) — Core改善記録。
- [`CORE_IMPROVEMENT_ROUND2_2026-09-01.md`](CORE_IMPROVEMENT_ROUND2_2026-09-01.md) — Core改善第2系列。
- [`HDS_IR_NATIVE_K3.md`](HDS_IR_NATIVE_K3.md) — 旧HDS-IR→K3相当能力核経路の補助記録。現行標準Coreのactive pathではない。
- `BRANCH_CONSOLIDATION_2026-09-01.md` 等 — 開発履歴・統合記録。

## 現行と履歴を混同しない

MINIDORAは研究開発の途中で複数の構成を試しています。そのため、ファイルが存在することと現行active設計であることは同義ではありません。

```text
現行正本       → 設計/README.md
現行実装       → src/minidora/
現行実測       → 評価/README.md
ハッカソン層   → ハッカソン/README.md
過去経路・履歴 → docs/ / 構文化/ / artifacts/
```

旧K3 helper、旧HDS終端経路、過去の専門solver等は履歴として残しますが、現行標準Coreへ無言復帰させません。

## 日本語基底

規定言語・基底言語・内部意味正本は日本語です。

英語版は国際公開用の翻訳であり、意味上の並列正本ではありません。公開入口の英語版は [`../README.en.md`](../README.en.md)、ハッカソン説明の英語版は [`../ハッカソン/README.en.md`](../ハッカソン/README.en.md) に置きます。

## 文書追加規則

補助文書を追加するときは、最低限次を明示します。

- 現行か履歴か
- どの設計正本を説明しているか
- 実装・評価・構文化のどの責任に属するか
- 日本語正本か翻訳か

`docs/` の記述が [`../設計/`](../設計/) と食い違う場合、補助文書側を自動的に正しいとは扱わず、不整合として再監査します。