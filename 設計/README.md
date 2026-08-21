# MINIDORA 設計正本ガイド

`設計/` は、現行MINIDORA Runtimeの意味境界・責任・受入条件を定める局所正本である。

外部モデルの観測結果そのものは `構文化/`、実測値は `評価/`、固定取得物は `artifacts/` に分離する。

## 正本の読み順

1. [`02_Layer0責任契約.md`](02_Layer0責任契約.md) — Layer-0上位契約をMINIDORAへ写像する。
2. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md) — 実行可能な命令形PとDataの分離を定める。
3. [`04_外部参照R仕様.md`](04_外部参照R仕様.md) — Data / Knowledgeの外部参照層Rを定める。
4. [`06_主体主幹仕様.md`](06_主体主幹仕様.md) — turnを跨ぐ主体状態と主体整合Gateを定める。
5. [`07_HDS_IR入力契約.md`](07_HDS_IR入力契約.md) — 公開Runtimeと外部HDS Compilerの接続境界を定める。
6. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md) — 多言語表面とJ/C/M文脈循環を定める。
7. [`05_完成判定関門.md`](05_完成判定関門.md) — 上記を横断して、プロトタイプ以後の製品・最終完成条件を定める。

番号は成立順・履歴を保持しているため、文書の読み順と完全には一致しない。整理目的だけで番号を振り直さない。

## Layer-0の位置

Layer-0そのものの論理正本は本ディレクトリではない。

- 上位Repository: [gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)
- 現行仕様: `v4.0-provisional`
- MINIDORA参照commit: `4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc`

`02_Layer0責任契約.md` は、その上位契約をMINIDORAのP / R / HDS-IR / 主体主幹 / Runtimeへどう写像するかを定める。

詳細な外部参照階層は [`../REFERENCES.md`](../REFERENCES.md) を参照する。

## 現行構造

```text
外部Layer-0上位契約
        ↓
MINIDORA局所設計
        ├─ HDS-IR境界
        ├─ P: どう処理するか
        ├─ R: 何について処理するか
        ├─ 主体主幹
        └─ Trinity文脈 J/C/M
        ↓
src/minidora/
        ↓
tests/ + 評価/
```

## 状態語

設計・Runtimeの採否では原則として次を使う。

- `合格` / `PASS`
- `保留` / `SUSPEND`
- `失敗` / `FAIL`
- `非適用` / `NOT_APPLICABLE`

`PROTOTYPE COMPLETE` は2026-08-22に固定された**プロトタイプ段階の成立状態**であり、製品・最終完成とは別である。

## 変更規則

- Layer-0意味変更は外部正本を先に確認する。
- PへDataを埋め込まない。
- HDS Compiler内部方式を公開Runtime契約へ混入しない。
- 主体主幹をLayer-0第6責任として扱わない。
- Legacy構文化を現行設計へ無言で復帰させない。
- 設計変更時は実装・試験・README・評価解釈境界まで同時に監査する。
