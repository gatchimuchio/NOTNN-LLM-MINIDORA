# MINIDORA 設計正本ガイド

`設計/` は現行MINIDORA Runtimeの意味境界・責任・受入条件を定める局所正本である。

外部LLM成立条件は `LLM-Constitutive-Specification`、外部モデル観測は `構文化/`、実測値は `評価/`、固定取得物は `artifacts/` に分離する。

## 正本の読み順

1. [`02_大規模言語模型成立契約.md`](02_大規模言語模型成立契約.md) — 上位LLM成立規定をMINIDORA v0.4へ写像する。
2. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md) — 計算実行器へ渡す日本語命令形PとDataの分離。
3. [`13_共有言語基底P仕様.md`](13_共有言語基底P仕様.md) — HDS Compiler / 言語対応が共有する日本語基底資産。
4. [`14_英日意味コンパイル仕様_v0_3.md`](14_英日意味コンパイル仕様_v0_3.md) — 外部英語表層の意味射影境界。
5. [`04_外部参照R仕様.md`](04_外部参照R仕様.md) — 外部Data参照。
6. [`07_HDS_IR入力契約.md`](07_HDS_IR入力契約.md) — HDS-IRを模型中核と分離した運用入力境界。
7. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — 公開Compilerの責任・非責任。
8. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md)
9. [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md)
10. [`12_HDS_Compiler_Architecture_v1_2.md`](12_HDS_Compiler_Architecture_v1_2.md)
11. [`06_主体主幹仕様.md`](06_主体主幹仕様.md) — turnを跨ぐ主体状態と主体整合Gate。
12. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md) — 既存多言語運用・文脈循環。
13. [`05_完成判定関門.md`](05_完成判定関門.md) — 製品・最終完成条件。

番号は成立履歴を保持するため整理目的だけで振り直さない。

## 上位LLM成立規定

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版: `2026-08-26-成立規定-2`
- MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`

旧Layer-0 v4は現行上位契約ではない。旧局所契約は [`旧/02_Layer0責任契約_v4.md`](旧/02_Layer0責任契約_v4.md) に履歴として保持する。

## v0.4現行構造

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

ここまでがLLM模型中核。

その外側に、

```text
HDS意味Projection / 外部参照 / 候補生成
              ↓
           模型中核
              ↓
主体整合 / 採否 / 生成運用 / 表面化

日本語命令形P
      ↓
  計算実行器
```

を置く。

旧 `Layer0` 命令器はv0.4で **計算実行器** と再分類する。

## HDS公開境界

- 公開HDS Compilerは引き続き公開Runtime資産として保持する。
- HDS-IRは意味Projection・運用接続・監査履歴であり、LLM模型中核やCompute IRと同一視しない。
- v0.4模型核再構成の段階ではHDS Compiler本体を先回り改造しない。
- 次段でCompute IR / lowering境界を確定してからCompiler側を更新する。
- HDS本体の上流理論・非公開解析正本を公開Compilerへ無断転記しない。

## 状態語

設計・Runtimeの採否では原則として次を使う。

- `合格` / `PASS`
- `保留` / `SUSPEND`
- `失敗` / `FAIL`
- `非適用` / `NOT_APPLICABLE`

`PROTOTYPE COMPLETE` は2026-08-22のv0.3系プロトタイプ成立記録であり、v0.4模型核の大規模性や製品完成を自動保証しない。

## 変更規則

- LLM成立意味変更は外部正本を先に確認する。
- 模型核と計算実行器を再び同一視しない。
- HDS-IRとCompute IRを無言で同一視しない。
- PへDataを埋め込まない。
- 共有言語基底へ百科事典的世界知識を混入しない。
- 日本語を基底・規定言語とし、他言語は実務上やむを得ない境界だけに限定する。
- Legacy構文化・旧Layer-0契約を現行設計へ無言復帰させない。
- 設計変更時は実装・試験・README・評価解釈境界まで同時に監査する。
