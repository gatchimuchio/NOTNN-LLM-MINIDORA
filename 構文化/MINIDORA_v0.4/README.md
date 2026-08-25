# MINIDORA v0.4 再構成記録

日付: 2026-08-26

## 目的

外部正本 `LLM-Constitutive-Specification` の `2026-08-26-成立規定-2` を上流基準として、MINIDORAを旧Layer-0責任構造から再構成する。

## 基準

- Repository: https://github.com/gatchimuchio/LLM-Constitutive-Specification
- commit: `e94a13ba32208aabd9dc88b6de320872963725be`
- 正本: `規定/02_大規模言語模型成立.md`

MINIDORA自体を上流規定の成立証人には使用しない。

## 観測した旧混線

### 1. `layer0.py`

実装は算術、比較、取得、抽出、状態更新等の汎用命令インタプリタであり、言語状態から成立差を形成する模型側関係そのものではなかった。

判定: **LLM模型中核 → 計算実行器へ再分類**。

### 2. Runtime

v0.3 RuntimeはHDS-IR / P / R / 主体 / K3能力補助 / Layer0を統合していた。この運用統合は有用だが、システム全体をLLM模型中核と同一視すると境界が崩れる。

判定: **運用経路は互換保持、模型核を独立追加**。

### 3. HDS-IR

HDS-IRは意味Projection・運用入力・監査履歴を保持するが、LLM成立規定が要求する普遍的な模型内部形式ではない。

判定: **模型中核 / Compute IRから分離**。

## v0.4新模型核

```text
対象言語状態
→ 言語対応
→ 文脈付き内部状態
→ 再利用可能な模型側関係
→ 成立差
```

### 実装

- `src/minidora/模型.py`
- `言語状態`
- `言語対応`
- `文脈付き言語状態`
- `模型関係`
- `関係規則`
- `意味連続関係`
- `成立差`
- `MINIDORA模型核`

確率・samplingを中核必須へ入れない。

## Legacy保持

v0.3実装は削除せず、

- `src/minidora/runtime_v03.py`
- `src/minidora/旧_layer0_v03.py`
- `設計/旧/02_Layer0責任契約_v4.md`

として再現可能性を保持する。

公開旧名 `Layer0` は互換aliasに限定する。

## 評価境界

v0.3の `PROTOTYPE COMPLETE`、GPQA等の実測は履歴固定する。

v0.4模型核の大規模性へ旧値を自動転用しない。大規模性は、

- 状態域規模
- 関係域規模
- 共有適用規模

を新経路で再測定する。

## 次段

v0.4模型核がCIで閉じた後、次にCompute IR / ABIを定義する。

その後に、HDS semantic IRからCompute IRへのloweringとHDS Compilerの責任境界を更新する。
