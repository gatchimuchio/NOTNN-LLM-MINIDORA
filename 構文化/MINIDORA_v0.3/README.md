# MINIDORA v0.3 公開再構成成果

## 位置づけ

v0.3は、v0.2の `Layer-0 × 日本語命令形P × 外部参照R` を保持しつつ、2026-08-21までのHDS横断構文化成果を反映した更新版である。

本ディレクトリは**公開再構成成果**であり、現行設計正本そのものではない。現行契約は `../../設計/`、Runtime実装は `../../src/minidora/` を参照する。

### 基準順位

1. **K3** — 主基盤
2. **Llama 3** — 自己一貫性を抽出する対抗基準
3. **その他LLM** — K3/Llama3差分を精密化する補助観測点

## Layer-0正本境界

`Layer0/` はMINIDORA側の公開再構成成果を保持するが、Layer-0そのものの論理正本ではない。

論理上位正本:
[gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)

- 現行仕様: `v4.0-provisional`
- MINIDORA参照commit: `4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc`
- MINIDORA局所写像: [`../../設計/02_Layer0責任契約.md`](../../設計/02_Layer0責任契約.md)

## 更新点

- Layer-0参照を `v4.0-provisional` の5責任へ更新
- 旧8責任はv0.2のLegacyとして保持
- Llama 3の自己一貫性再構文化から「主体主幹」を追加
- K3由来の動的能力処理と主体状態を分離
- 理由なし反転を保留、理由付き自己訂正を監査可能に更新
- Runtimeで結果未形成、矛盾、境界違反を採否へ接続
- Layer-0 v4 negative controlと主体主幹固有negative controlを追加

## 実行構造

```text
言語要求
  ↓
言語アドレス化 / 参照R
  ↓
主体状態 S_t ─────────┐
  ↓ 必須参照          │
Layer-0 × 日本語命令P │
  ↓                    │
K3基盤由来の能力処理   │
  ↓                    │
候補 / 状態差分        │
  ↓                    │
主体整合Gate           │
  ↓                    │
結果形成               │
  ↓                    │
結果表面               │
  ↓                    │
理由付き主体更新 ──────┘
```

## Layer-0 v4

現行責任:

- 言語アドレス化
- 文脈束縛状態
- 変換・合成中核
- 文脈依存結果形成
- 結果表面

`主体主幹` は第6責任ではない。
`文脈束縛状態 × 文脈依存結果形成` を主に担うMINIDORA固有機構である。

## 公開境界

本ディレクトリは公開可能な再構成物のみを保持する。
上流HDSの内部解析方法そのものは含めない。
