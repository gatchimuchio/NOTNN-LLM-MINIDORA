# MINIDORA 設計正本ガイド

`設計/` は、現行MINIDORA Runtimeの意味境界・責任・受入条件を定める局所正本である。

外部モデルの観測結果そのものは `構文化/`、実測値は `評価/`、固定取得物は `artifacts/` に分離する。

## 正本の読み順

1. [`02_Layer0責任契約.md`](02_Layer0責任契約.md) — Layer-0上位契約をMINIDORAへ写像する。
2. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md) — 実行可能な命令形PとDataの分離を定める。
3. [`13_共有言語基底P仕様.md`](13_共有言語基底P仕様.md) — HDS CompilerとMINIDORA/Cが共有する文字・基本文法・基底概念の常在言語資産を定める。
4. [`14_英日意味コンパイル仕様_v0_3.md`](14_英日意味コンパイル仕様_v0_3.md) — 外部英語表層を日本語正本の意味フレームへ射影し、R境界で英語検索表層へ戻す責任を定める。
5. [`15_関係Scope意味転送仕様_v0_4.md`](15_関係Scope意味転送仕様_v0_4.md) — 関係へ掛かる極性・様相・量化・条件をHDS-IRからKまで損失なく転送する責任を定める。
6. [`16_関係Scope認識推論仕様_v0_5.md`](16_関係Scope認識推論仕様_v0_5.md) — 転送済みscopeを比較・直接検証で使用し、scope未対応graphへ誤投入しない責任を定める。
7. [`17_Scope対応R復号仕様_v0_6.md`](17_Scope対応R復号仕様_v0_6.md) — 日本語正本のscopeをR境界でだけ原英語に近い検索表層へ復号し、検索時の意味損失を防ぐ。
8. [`04_外部参照R仕様.md`](04_外部参照R仕様.md) — Data / Knowledgeの外部参照層Rを定める。
9. [`07_HDS_IR入力契約.md`](07_HDS_IR入力契約.md) — 公開HDS CompilerとRuntimeのHDS-IR境界を定める。
10. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — フル公開する標準Compilerの責任・非責任・性能改善境界を定める。
11. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md) — v1の公開Front-End Architecture履歴を保持する。
12. [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md) — Failure Signature候補、状態遷移graph、暗黙知構造、監査R probe、CognitiveWorld差分まで接続した履歴を保持する。
13. [`12_HDS_Compiler_Architecture_v1_2.md`](12_HDS_Compiler_Architecture_v1_2.md) — Failure Signature Bank、反復昇格、改善候補帰還を定める現行Architecture正本。
14. [`06_主体主幹仕様.md`](06_主体主幹仕様.md) — turnを跨ぐ主体状態と主体整合Gateを定める。
15. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md) — 日本語基底と、実務上必要な多言語表層・J/C/M文脈循環を定める。
16. [`05_完成判定関門.md`](05_完成判定関門.md) — 上記を横断して、プロトタイプ以後の製品・最終完成条件を定める。

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
        ├─ 共有言語基底P
        │      ├─ 英日意味コンパイル
        │      │      ↓
        │      │    日本語意味正本
        │      ├─ 関係Scope意味転送
        │      │      └─ 極性 / 様相 / 量化 / 条件
        │      ├─ 公開HDS Compiler
        │      │      ↓
        │      │    HDS-IR
        │      └─ MINIDORA / C意味処理
        ├─ HDS-IR → K Adapter
        │      ├─ relation.conditionsを保持
        │      └─ scope付き関係を実効関係へ分離
        ├─ Scope認識比較
        │      ├─ 関係 / 方向 / scope一致
        │      └─ scope未対応graphへの誤投入禁止
        ├─ R境界
        │      └─ 日本語scope + 復号表層 → 英語検索query
        ├─ P: どう処理するか
        ├─ R: 何について処理するか
        ├─ 主体主幹
        └─ Trinity文脈 J/C/M
        ↓
src/minidora/
        ↓
tests/ + 評価/
```

## HDS公開境界

- `src/minidora/hds_compiler_v1.py` と、その公開Front-End構成、明示Failure Signature Bankはフル公開対象であり、MINIDORAの通常の性能改善対象とする。`hds_compiler.py` は互換基礎Projectionとして保持する。
- HDS-IRスキーマ、Compilerの有限Projection、Failure Signatureの公開再利用契約を公開しても、HDS本体の上流理論・導出規則・非公開解析正本は自動的に公開しない。
- Compiler公開を理由にHDS本体の資料を `設計/` や `src/` へ複製しない。
- Failure Signature BankはCompiler自動自己改変器ではない。改善候補の最終採否は別境界へ委譲する。

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
- 共有言語基底Pへ百科事典的な世界知識を混入させない。
- HDS CompilerとMINIDORA/Cは同じ言語基底版を参照する。
- 英語表層を内部意味正本へ直接昇格させず、日本語正本の意味フレームを介す。
- 日本語意味正本を英語R検索queryへ無差別に混入させない。
- R検索復号用の英語表層を日本語意味正本そのものとして扱わない。
- 明示否定・様相をR検索query生成時に無言で落とさない。
- 関係の極性・様相・量化・条件を関係本体から切り離して無意味化しない。
- HDS-IRの `relation.conditions` をHDS→K境界で破棄しない。
- 肯定関係と否定関係をK graph上の同一predicateへ潰さない。
- 様相・量化・比較・条件の異なる関係を直接構造一致として加点しない。
- scopeを理解しない汎用graphへscope付き関係を無条件辺として流さない。
- `least likely` 等の選択反転と、`does not` 等の関係否定を同一視しない。
- 公開HDS Compilerは通常のRuntime実装として変更・試験・監査してよい。
- HDS本体の非公開正本を公開Compilerへ無断転記しない。
- 日本語を基底・規定言語とし、多言語は実務上やむを得ない境界だけに限定する。
- Failure Signature反復から改善候補を生成しても、自動適用・自己承認しない。
- 主体主幹をLayer-0第6責任として扱わない。
- Legacy構文化を現行設計へ無言で復帰させない。
- 設計変更時は実装・試験・README・評価解釈境界まで同時に監査する。
