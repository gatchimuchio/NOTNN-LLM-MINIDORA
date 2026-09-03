# NOTNN-LLM-MINIDORA — ミニドラ

> **ニューラルネットワークやTransformerを中核に使わず、最小の言語模型Coreと外部能力Moduleを分離して構成する、日本語基底の非ニューラルLLM研究・実装プロジェクトです。**

[English translation](README.en.md) / [ハッカソン実装](ハッカソン/README.md) / [設計正本](設計/README.md) / [評価・実測](評価/README.md)

## 30秒でわかるMINIDORA

MINIDORAは、知識・専門能力・個別タスク能力を一つの巨大な模型へ詰め込む方向ではなく、責任を分離します。

```text
MINIDORA Core
├─ 非ニューラル厳密言語模型核
├─ 汎用能力模型核
├─ 汎用計算実行器
├─ 外部参照
└─ HDSによる異常時最小介入

外部Capability Module
├─ ニュース
├─ 要約
├─ 科学
├─ coding
└─ その他の専門能力
```

基本原則は次の3点です。

1. **Coreを小さく保つ** — 世界知識や専門solverを本体へ無制限に埋め込まない。
2. **能力をModuleとして後付けする** — Core再学習なしで能力を増設できる境界を持つ。
3. **応答経路を追跡する** — ハッカソン版では「なぜこの応答になったか」を後付け説明ではなく実行記録として保持する。

現行パッケージ版は **v0.5.0**。ハッカソン専用チャット層は **v0.2** です。

## 現在できること

| 項目 | 状態 | 内容 |
|---|---|---|
| 非ニューラル言語模型Core | 実装済み | 完全言語状態空間・持続模型状態・整合した言語確率法則を実装 |
| 汎用能力Core | 実装済み | 候補・証拠・関係・状態差を一般作用として扱う |
| HDS監督介入 | 実装済み | 未閉包・競合・観測不足等の異常時だけ最小介入 |
| 能力Module追加 | 実装・実測済み | Core再学習なしのModule追加で実効能力が増えることをcontrolled replayで確認 |
| ハッカソン用チャット | v0.2実装済み | 基本会話、ニュース取得、直前文脈の要約、Core委譲 |
| 応答トレース | v0.2実装済み | 経路選択・参照・Module入出力・会話状態・最終応答をhash chain化 |
| ブラウザUI / Cloud Run | 次段 | ハッカソン提出向け配信層として実装予定 |

## ハッカソンで見せるもの

デモ自体は意図的に単純です。

```text
ユーザー: 今日のニュースは？
MINIDORA: 外部参照から当日ニュースを提示

ユーザー: 要約して
MINIDORA: 直前に取得したニュースだけを対象に要約
```

ニュース→要約の専用経路では、外部LLMによる自由生成を混ぜず、取得済みDataから決定論的に抽出・圧縮します。

同時に各応答へ `trace_id` と監査root hashを付与し、次を追跡できます。

```text
入力
→ 経路選択
→ 外部参照 / 文脈参照
→ 能力Module実行
→ 応答構成
→ 会話状態更新
→ 監査root hash
→ 次応答へ前hashを接続
```

詳細: [ハッカソン専用実装 v0.2](ハッカソン/README.md)

## なぜModule方式なのか

MINIDORAでは、Coreと専門能力を別責任として扱います。

```text
Core      = 汎用作用
Data      = 外部化可能
Knowledge = 外部参照可能
Module    = 専門能力
Compute   = 汎用計算
HDS       = 異常時の最小制御
```

2026-09-02のGPQA Diamond controlled replayでは、保存済みbaselineへ既存科学専門能力Module群を追加接続した結果、次の差を観測しました。

| 条件 | 正答 | 全体正答率 | 回答時正答率 |
|---|---:|---:|---:|
| Module OFF | 8 / 198 | 4.04% | 20.51% |
| Module ON | **63 / 198** | **31.82%** | **73.26%** |

```text
Module発火 = 55
改善       = 55
退行       = 0
正答差     = +55
```

この結果は **63/198をCore単体性能として主張するものではありません**。同一Coreへ外部Capabilityを追加し、その追加能力が実際の性能差として発現することを確認した実証です。

詳細:
- [モジュール拡張成立実証](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [能力Module拡張境界](設計/35_MINIDORA_能力Module拡張境界_v1.md)

## Core単体の現在地

専門solverをactive pathから外した2026-09-01のGPQA Diamond全198問では、次の結果です。

```text
正式MINIDORA汎用模型核 / HDS非介入 = 19 / 198  (9.60%)
最小汎用Core + HDS異常時最小介入  = 23 / 198 (11.62%)
```

この数値は現行Coreの能力観測であり、MINIDORAがGPT-4等のフロンティアモデルと同等性能であることを示すものではありません。

また、v0.5における **Large** 判定は **再監査** 対象です。旧版の規模評価を自動継承しません。

詳細: [GPQA Diamond — Minimal Generic Core](評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)

## クイックスタート

要件: Python 3.11以上

```bash
python -m pip install -e .
```

MINIDORA Core:

```bash
python -m minidora "2+3"
```

ハッカソン用チャット:

```bash
python -m minidora.ハッカソン
```

同一セッションで次を入力します。

```text
> 今日のニュースは？
> 要約して
```

監査ログをJSONLへ追記保存する場合は `MINIDORA_AUDIT_LOG` を設定します。詳細は [ハッカソンREADME](ハッカソン/README.md) を参照してください。

## リポジトリ案内

初見では上から順に読むことを推奨します。

| 場所 | 役割 |
|---|---|
| [`README.md`](README.md) | 公開向け入口・現状・主張範囲 |
| [`README.en.md`](README.en.md) | 英語翻訳版。日本語正本に従属 |
| [`ハッカソン/`](ハッカソン/) | デモ・製品化向け専用層 |
| [`設計/`](設計/) | 現行MINIDORAの局所設計正本 |
| [`評価/`](評価/) | 適合・性能・回帰・実測証拠 |
| [`src/minidora/`](src/minidora/) | 現行実装 |
| [`tests/`](tests/) | 単体・回帰試験 |
| [`docs/`](docs/) | 補助文書・セーブポイント・案内 |
| [`構文化/`](構文化/) | 観測・再構成・構文化履歴 |
| [`artifacts/`](artifacts/) | 固定取得物・派生成果 |
| [`REFERENCES.md`](REFERENCES.md) | 上位正本と参照関係 |

より詳しい読み順: [docs/README.md](docs/README.md)

## 日本語基底と英語版

MINIDORAは **日本語を規定言語・基底言語・内部意味正本** とします。英語版は国際公開のための翻訳・互換表層であり、意味上の正本ではありません。

上位正本:

- Cognitive Engineering Foundations: https://github.com/gatchimuchio/cognitive-engineering-foundations
  - 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- LLM Constitutive Specification: https://github.com/gatchimuchio/LLM-Constitutive-Specification
  - 版: `2026-08-28-成立規定-8`
  - 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

詳細: [REFERENCES.md](REFERENCES.md)

## 主張の境界

このリポジトリでは、次を混同しません。

```text
厳密言語模型成立
!= 汎用能力性能
!= GPQA得点
!= Module込みのシステム性能
!= Large
!= フロンティアLLMとの性能同等性
!= 製品完成
```

MINIDORAが採用する成立規定に対する適合、Core能力、Module拡張、ハッカソン製品層は、それぞれ別の証拠と評価系列で管理します。

## 検証

リポジトリ標準検証:

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはUbuntu / Windows、Python 3.11–3.14を対象にしています。

## ライセンス

成果物の種類ごとにライセンスを分離しています。

- ソースコード・実装: **Apache License 2.0** — [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0)
- 仕様・設計・理論・評価・README等の文書: **CC-BY-4.0** — [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)
- 適用範囲: [`LICENSE`](LICENSE)
- 帰属・第三者由来物: [`NOTICE`](NOTICE)

## Author

**がっちむち♂**

MINIDORAは研究履歴を消して見栄えだけを整えるのではなく、現行状態・成立証拠・失敗・Legacyを区別して公開します。