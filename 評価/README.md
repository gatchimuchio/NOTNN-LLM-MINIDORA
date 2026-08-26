# 評価

`評価/` は、MINIDORAの適合・性能・回帰・完成判定に関する**実測記録**を保持する。

設計そのものは `../設計/`、Runtime実装は `../src/minidora/` を参照する。

## 現在の状態

### MINIDORA v0.4

2026-08-26、上流 **大規模言語模型成立規定 `2026-08-26-成立規定-2`** に基づく再構成系列を受入した。

正本:

- [`MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md`](MINIDORA_v0_4_REBUILD_ACCEPTANCE_2026-08-26.md) — 模型核・計算実行器分離。
- [`計算中間表現_実行境界_v1_受入_2026-08-26.md`](計算中間表現_実行境界_v1_受入_2026-08-26.md) — 計算中間表現 / 計算実行境界v1。
- [`HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md`](HDS_Compiler_Pipeline_v1_3_受入_2026-08-26.md) — 意味IR / 計算計画 / 計算降下分離。
- [`MINIDORA_v0_4_規模測定_v2_2026-08-26.md`](MINIDORA_v0_4_規模測定_v2_2026-08-26.md) — 三面規模再測定と関係域修正。
- [`GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json`](GPQA_Diamond_V0_4_CURRENT_2026-08-26.summary.json) — 再構成後v0.4のGPQA Diamond 198問現行実測。
- [`MINIDORA_三層射影精度監査_2026-08-26.md`](MINIDORA_三層射影精度監査_2026-08-26.md) — K3/他LLM→構文化→HDS Compiler→MINIDORA射影の三層精度監査。三層すべてを原因と判定し、直接主因をHDS Compilerの質問意味射影と特定。

### 三層射影精度監査

2026-08-26、GPQA Diamond 198問を使って性能採点とは別に意味射影coverageを全数監査した。

主要結果:

```text
K質問関係保持        3 / 198  = 1.515%
K topic-only        195 / 198 = 98.485%
候補K関係保持       283 / 792 = 35.732%
候補の関係0かつsemantic_lossなし 507 / 792
Expert Explanation K関係保持 174 / 198 = 87.879%
```

判定:

```text
① LLM構文化                  = 原因（高位作用は取れているが作用遷移則・形成則が不足）
② HDS Compiler               = 主因（質問意味をtopic-onlyへ過剰圧縮）
③ MINIDORA構成定義・射影     = 原因（能力保存射影不足 + 正式模型核と性能経路の不一致）
```

「Data compile success」を意味関係保存成功と同一視しない。射影鎖が閉じるまで、GPQA向け閾値調整・正解ルール追加・SUSPEND緩和を能力改善とは扱わない。

### 現行模型中核

```text
対象言語状態
→ 言語対応
→ 文脈付き内部状態
→ 再利用可能な模型側関係
→ 成立差
```

標準模型核は意味連続・順序連続・有向関係・肯否・履歴近接・条件結合の6関係作用を持つ。

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

Meaning/Audit Architectureは `v1.2` を維持する。

### v0.4大規模性

初回再測定v1では、状態域384/384・共有適用256/256に対し、関係域が意味集合中心で方向・肯否・履歴順序・条件結合を失っていたため **未成立** と判定した。

その後、模型核へHDSを導入せず言語構造を追加し、v2で再測定した。

現行判定:

```text
MINIDORA v0.4 大規模性 = 局所成立候補
```

v2代表値:

- 状態域: 384 / 384識別、3言語体系、10,000文字PASS、履歴256PASS
- 関係域: 17 / 17一般関係族、544 / 544関係構造識別
- 構造差: 方向 / 肯否 / 履歴順序 / 条件結合すべて成立差へ到達
- 共有適用: 256 / 256
- 模型関係実体: 6

この判定は上流規定の三面に対する比較記述であり、現代ニューラルLLMとの物理規模・benchmark性能の同等を意味しない。

## v0.3プロトタイプ履歴

2026-08-22時点で、旧v0.3系MINIDORAは **PROTOTYPE COMPLETE** と判定されている。

正本:

- [`PROTOTYPE_COMPLETION_2026-08-22.md`](PROTOTYPE_COMPLETION_2026-08-22.md)
- [`GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json`](GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json)

このbaselineは履歴固定値であり、現行v0.4模型核の規模・性能へ自動転用しない。

## GPQA Diamond 性能変遷

時系列索引は [`GPQA_Diamond_PROGRESS_2026-08-23.md`](GPQA_Diamond_PROGRESS_2026-08-23.md) と各日付の実測記録を使用する。

| 時点 | 区分 | 正答 | 正答率 | 扱い |
|---|---|---:|---:|---|
| 2026-08-22 | 初期診断 | 5 / 198 | 2.5253% | 無効診断 |
| 2026-08-22 | Prototype baseline | 8 / 198 | 4.0404% | 不変baseline |
| 2026-08-22 | v0.5開発途中 | 17 / 198 | 8.5859% | 途中参照値 |
| 2026-08-23 | v0.6系workflow実測 | 31 / 198 | 15.6566% | 完走実測・後続main値ではない |
| 2026-08-26 | 再構成後v0.4 current | 19 / 198 | 9.5960% | 再構成直後の完走実測 |
| 2026-08-26 | 再作用P0後 | 22 / 198 | 11.1111% | 完走実測。ただしworking relation再利用0のため再作用効果とは帰属しない |

再作用P0後実測:

- 回答: 122 / 198（61.6162%）
- SUSPEND: 76
- 回答時正答率: 18.0328%
- retrieval empty: 0
- 取得文書: 2,714
- Data compile: 2,714 / failure 0
- working relations created: 114,443
- working relations reused: 0
- checkpoint reactivations: 0
- global reconciliations: 0
- temporary working evidence: 0

P0による再作用は実データ上発火していないため、19→22の差を再作用機構の性能改善へ帰属しない。

2026-08-23 v0.6系実測との開発履歴上の差は、正答 `31 → 19`、回答 `128 → 118`、SUSPEND `70 → 80`、回答時正答率 `24.21875% → 16.1017%` である。ただしCompiler/configurationが異なるため統制されたA/B比較とは扱わない。

再構成直後は取得文書 `2,698`、K facts `101,554`、evidence facts `120,504`。retrieval emptyとData compile failureはいずれも0だった。現在は三層射影監査により、**Compilerの質問意味関係保存と、構文化→Compiler→構成定義の能力保存射影**を主要再監査対象とする。

SUSPEND境界を緩めて全問回答することは改善とは扱わない。

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
!= v0.4大規模性 局所成立候補
!= 製品・最終完成
!= 現代ニューラルLLMとの物理規模同等
!= K3級性能
```

製品・最終完成の関門は [`../設計/05_完成判定関門.md`](../設計/05_完成判定関門.md) を参照する。
