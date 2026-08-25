# 評価

`評価/` は、MINIDORAの適合・性能・回帰・完成判定に関する**実測記録**を保持する。

設計そのものは `../設計/`、Runtime実装は `../src/minidora/` を参照する。

## 現在の状態

### MINIDORA v0.4

2026-08-26、上流 **大規模言語模型成立規定 `2026-08-26-成立規定-2`** に基づく構造再構成を受入PASSとした。

正本:

- [`MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md`](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md) — 模型核・計算実行器分離、HDS境界、全CI行列。
- [`計算中間表現_実行境界_v1_受入_2026-08-26.md`](計算中間表現_実行境界_v1_受入_2026-08-26.md) — 計算中間表現・計算実行境界v1の受入。
- [`HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md`](HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md) — 意味IRと計算計画/計算降下の責任分離受入。

### 現行模型中核

```text
対象言語状態
→ 言語対応
→ 文脈付き内部状態
→ 再利用可能な模型側関係
→ 成立差
```

旧 `Layer0` 命令器は **計算実行器** へ再分類した。

### 計算経路

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

計算境界受入CI:

- workflow run id: `32888711819`
- validated head: `f7cb678dafdfd2010de3214852cbad7f9a9b5596`
- Ubuntu / Windows × Python 3.11–3.14: **全8 job PASS**
- 代表job: **336 tests / OK**
- 新規Compute IR / ABI試験: **7 / 7 PASS**
- K3相当構造: **47 / 47 PASS**

### HDS Compiler Pipeline v1.3

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

Pipeline受入CI:

- workflow run id: `32890261690`
- validated head: `29fe0bbca28310a23c23ef22c5533814d9fd06c3`
- Ubuntu / Windows × Python 3.11–3.14: **全8 job PASS**
- 代表job: **345 tests / OK**
- Pipeline v1.3試験: **9 / 9 PASS**
- K3相当構造: **47 / 47 PASS**
- CLI: `5です。`

### 未完了関門

v0.4の大規模性は**再測定要**である。

```text
v0.4構造受入PASS
+
計算中間表現/実行境界v1受入PASS
+
HDS Compiler Pipeline v1.3受入PASS
!= v0.4大規模性測定完了
!= 製品・最終完成
```

次段は上流規定に従い、対象言語体系・対象範囲・比較集合・状態域規模・関係域規模・共有適用規模・物理規模値・総合判断理由を明示して測定する。

## v0.3プロトタイプ履歴

2026-08-22時点で、旧v0.3系MINIDORAは **PROTOTYPE COMPLETE** と判定されている。

これは非ニューラル／非Transformer経路が閉じ、外部未知ベンチで非ゼロの正答能力を実測したプロトタイプ段階の完成を意味する。製品版・最終完成やK3級性能を意味しない。

正本:

- [`PROTOTYPE_COMPLETION_2026-08-22.md`](PROTOTYPE_COMPLETION_2026-08-22.md)
- [`GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json`](GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json)

このbaselineは履歴固定値であり、現行v0.4模型核の大規模性へ自動転用しない。

## GPQA Diamond 性能変遷

時系列索引は [`GPQA_Diamond_PROGRESS_2026-08-23.md`](GPQA_Diamond_PROGRESS_2026-08-23.md) を正本とする。

| 時点 | 区分 | 正答 | 正答率 | 扱い |
|---|---|---:|---:|---|
| 2026-08-22 | 初期診断 | 5 / 198 | 2.5253% | 無効診断 |
| 2026-08-22 | Prototype baseline | 8 / 198 | 4.0404% | 不変baseline |
| 2026-08-22 | v0.5開発途中 | 17 / 198 | 8.5859% | 途中参照値 |
| 2026-08-23 | v0.6系workflow実測 | 31 / 198 | 15.6566% | 完走実測 |

これらは過去の運用経路に対する履歴実測であり、再構成後v0.4模型核の規模・性能測定とは別記録とする。

## 評価軸

- 言語模型性
- 状態域規模
- 関係域規模
- 共有適用規模
- 推論
- 知識
- 命令追従
- 長文脈
- code
- agentic長期実行
- 未知停止
- 矛盾停止
- 主体的一貫性
- 理由付き自己訂正
- latency / memory / cost

## 状態の区別

```text
PROTOTYPE COMPLETE(v0.3)
!= v0.4構造受入PASS
!= 計算中間表現/実行境界v1受入PASS
!= HDS Compiler Pipeline v1.3受入PASS
!= v0.4大規模性測定完了
!= 製品・最終完成
!= K3級性能
```

製品・最終完成の関門は [`../設計/05_完成判定関門.md`](../設計/05_完成判定関門.md) を参照する。
