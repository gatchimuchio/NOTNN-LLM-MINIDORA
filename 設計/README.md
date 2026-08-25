# MINIDORA 設計正本ガイド

`設計/` は現行MINIDORA Runtimeの意味境界・責任・受入条件を定める局所正本である。

外部LLM成立条件は `LLM-Constitutive-Specification`、外部モデル観測は `構文化/`、実測値は `評価/`、固定取得物は `artifacts/` に分離する。

## 正本の読み順

1. [`02_大規模言語模型成立契約.md`](02_大規模言語模型成立契約.md) — 上位LLM成立規定をMINIDORA v0.4へ写像する。
2. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md) — 計算実行器へ渡す日本語命令形PとDataの分離。
3. [`25_計算中間表現_実行境界_v1.md`](25_計算中間表現_実行境界_v1.md) — Compute IR / ABIに相当する計算専用境界。
4. [`26_HDS_Compiler_Pipeline_v1_3.md`](26_HDS_Compiler_Pipeline_v1_3.md) — 意味HDS-IRと計算計画・計算降下を分離する現行Compiler Pipeline。
5. [`13_共有言語基底P仕様.md`](13_共有言語基底P仕様.md) — HDS Compiler / 言語対応が共有する日本語基底資産。
6. [`14_英日意味コンパイル仕様_v0_3.md`](14_英日意味コンパイル仕様_v0_3.md) — 外部英語表層の意味射影境界。
7. [`04_外部参照R仕様.md`](04_外部参照R仕様.md) — 外部Data参照。
8. [`07_HDS_IR入力契約.md`](07_HDS_IR入力契約.md) — HDS-IRを模型中核・計算中間表現と分離した意味/運用境界。
9. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md) — 公開Compilerの責任・非責任。
10. [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md)
11. [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md)
12. [`12_HDS_Compiler_Architecture_v1_2.md`](12_HDS_Compiler_Architecture_v1_2.md)
13. [`06_主体主幹仕様.md`](06_主体主幹仕様.md)
14. [`08_多言語_Trinity文脈契約.md`](08_多言語_Trinity文脈契約.md)
15. [`05_完成判定関門.md`](05_完成判定関門.md)

番号は成立履歴を保持するため整理目的だけで振り直さない。

## 上位LLM成立規定

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版: `2026-08-26-成立規定-2`
- MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`

旧Layer-0 v4は現行上位契約ではない。旧局所契約は [`旧/02_Layer0責任契約_v4.md`](旧/02_Layer0責任契約_v4.md) に履歴として保持する。

## 現行構造

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
      ↓
命令計算降下
      ↓
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
意味HDS-IR
  ├─ R / K / J / 監査
  └─ 計算計画
       ↓
     計算降下
       ↓
     計算中間表現 v1
```

旧 `Layer0` 命令器は **計算実行器** の互換名であり、模型中核ではない。

## HDS公開境界

- 公開HDS Compilerは公開Runtime資産として保持する。
- Meaning/Audit Architectureは `v1.2`、意味/計算責任を分離するPipelineは `v1.3`。
- `意味コンパイル()` が意味正本入口で、意味IRへPや計算初期状態を入れない。
- `コンパイル束()` は意味IRと計算計画を別保持する。
- `計算降下()` は形成済み計算計画から計算中間表現へ降下し、自然言語を再解析しない。
- 旧 `コンパイル()` は互換窓口に限定する。
- HDS本体の上流理論・非公開解析正本を公開Compilerへ無断転記しない。

## 状態語

- `合格` / `PASS`
- `保留` / `SUSPEND`
- `失敗` / `FAIL`
- `非適用` / `NOT_APPLICABLE`

`PROTOTYPE COMPLETE` は2026-08-22のv0.3系プロトタイプ成立記録であり、現行模型核の大規模性や製品完成を自動保証しない。

## 変更規則

- LLM成立意味変更は外部正本を先に確認する。
- 模型核と計算実行器を再び同一視しない。
- HDS-IRと計算中間表現を無言で同一視しない。
- Pと計算中間表現を無言で同一視しない。
- 意味HDS-IRへ計算Pを戻さない。
- 計算降下で自然言語を再解析しない。
- 計算実行境界へ自然言語/HDS意味解析を戻さない。
- PへDataを埋め込まない。
- 共有言語基底へ百科事典的世界知識を混入しない。
- 日本語を基底・規定言語とし、他言語は実務上やむを得ない境界だけに限定する。
- Legacy構文化・旧Layer-0契約を現行設計へ無言復帰させない。
- 設計変更時は実装・試験・README・評価解釈境界まで同時に監査する。
