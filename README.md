# NOTNN-LLM-MINIDORA — ミニドラ

> **ニューラルネットワークやTransformerを中核に使わず、最小の言語模型Coreと交換可能な能力Moduleを分離して構成する、日本語基底の非ニューラルLLM研究・実装プロジェクトです。**

[English translation](README.en.md) / [製品版デモ](製品版/README.md) / [設計正本](設計/README.md) / [評価・実測](評価/README.md)

## 上位正本

| リポジトリ | 役割 |
|---|---|
| [**認知工学基盤 — cognitive-engineering-foundations**](https://github.com/gatchimuchio/cognitive-engineering-foundations) | 認知工学・言語基底・HDS等の最上位理論正本 |
| [**LLM構成定義 — LLM-Constitutive-Specification**](https://github.com/gatchimuchio/LLM-Constitutive-Specification) | LLM成立条件・能力作用構成の責任正本 |

```text
認知工学基盤
    ↓ 理論・意味・日本語基底
LLM構成定義
    ↓ 言語模型成立条件・能力作用構成
MINIDORA Core
    ↓ 交換可能なCapability Module
MINIDORA Product Prototype
```

詳細: [REFERENCES.md](REFERENCES.md)

## 30秒でわかるMINIDORA

MINIDORAは、知識・専門能力・個別タスク能力を一つの巨大模型へ詰め込むのではなく、責任を分離します。

```text
MINIDORA Core
├─ 非ニューラル厳密言語模型核
├─ 汎用能力模型核
├─ 汎用計算実行器
├─ 外部参照
└─ HDSによる異常時最小介入

Capability Module
├─ 基本会話
├─ ニュース
├─ 要約
├─ 文脈変換
├─ 情報抽出
├─ 計算
├─ 知識参照
└─ 追加可能な専門・汎用能力
```

基本原則は3つです。

1. **Coreを小さく保つ** — 世界知識や専門solverを無制限に焼き込まない。
2. **能力をModuleとして後付けする** — 成立済みCoreを再学習せずCapability集合を増やす。
3. **応答経路を追跡する** — 「なぜこの応答になったか」を後付け生成ではなく実際の実行記録として保持する。

現行Coreパッケージは **v0.5.0**。製品向けチャット層は **Product Prototype v1** です。

## 製品版デモ

ハッカソンでは「今日のニュースは？ → 3行で要約して」を見せますが、ニュース専用デモではありません。製品版は共通Capability契約とレジストリを持ち、日常能力をModuleとして追加できる構成です。

現在の製品版:

- 基本会話
- RSSニュース外部参照
- 取得済み参照本文に接地した要約
- 明示文章の要約
- 直前応答の形式変換
- 情報抽出
- 決定論的計算
- Wikipedia知識参照
- 専用Module非該当時の既存MINIDORA Core委譲
- セッション別会話状態
- 能力候補・選択・Module版・入出力・参照・最終応答の完全経路監査
- SHA-256 hash chainと前応答hash接続
- ブラウザUI / HTTP API

起動:

```bash
python -m pip install -e .
python -m minidora.製品版 --serve
```

ブラウザで `http://localhost:8080/` を開きます。

API:

```text
POST /api/chat
GET  /api/trace/{trace_id}
GET  /api/capabilities
GET  /health
```

詳細: [製品版README](製品版/README.md)

## Capability Module拡張

能力Moduleは共通契約を持ちます。

```text
名前 / 版 / 優先度 / 判定 / 実行
```

新しい能力はレジストリへ登録でき、Product Chatや成立済みCoreの再学習を必要としません。Module不成立時は勝手な回答を作らず、次の適切な経路へ透過または保留します。

既存のGPQA Diamond controlled replayでは、同一baselineへ科学専門能力Module群を接続した結果、次を観測済みです。

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

これは **63/198をCore単体性能として主張するものではありません**。同一Coreへ外部Capabilityを追加し、その能力差が実性能差として発現したことの実証です。

製品版ではさらに `tools/製品能力Module実証.py` により、GPQAではない日常タスクでModule OFF / ONを同一Core上で比較できるようにしています。正式な日常能力差分値は実MINIDORA Core上での実行結果を取得して確定します。

詳細:
- [能力Module拡張境界](設計/35_MINIDORA_能力Module拡張境界_v1.md)
- [既存Module拡張成立実証](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [日常汎用能力受入](評価/日常汎用能力_受入_v1.md)

## Governance / Traceability

各応答について、実際に通過した経路を記録します。

```text
入力
→ 能力候補
→ Module選択
→ Module入出力 / 参照
→ 必要ならCore透過
→ 応答構成
→ 会話状態更新
→ root hash
→ 次応答へ前hash接続
```

`trace_id` から監査記録を取得できます。監査イベントはSHA-256 hash chainで改変検出可能です。

これはローカルファイルを改変不能にするWORMや暗号署名そのものではありません。`MINIDORA_AUDIT_LOG` は `flush + fsync` 付きJSONL追記を提供し、本番でのWORM・外部署名・外部anchorは配備層の責任として分離します。

## Core単体の現在地

専門solverをactive pathから外した2026-09-01 GPQA Diamond全198問:

```text
正式MINIDORA汎用模型核 / HDS非介入 = 19 / 198  (9.60%)
最小汎用Core + HDS異常時最小介入  = 23 / 198 (11.62%)
```

この値は現行Core能力の観測であり、MINIDORAがGPT-4等のフロンティアモデルと同等性能であることを示しません。

製品版の長期開発目標は **GPT-4級の一般チャット使用感** です。これは現時点の同等性能宣言ではなく、会話・要約・知識参照・比較・推論・計算・変換・検索・コード等の実利用能力をModuleとして増設し、実測で到達度を判断する目標です。

v0.5における **Large** 判定は **再監査** 対象であり、旧版の規模評価を自動継承しません。

## リポジトリ案内

| 場所 | 役割 |
|---|---|
| [`製品版/`](製品版/) | 製品向けチャットAI・起動・ガバナンス |
| [`src/minidora/製品版/`](src/minidora/製品版/) | Product Chat / Capability Registry / Module / API / UI |
| [`設計/`](設計/) | 現行MINIDORA局所設計正本 |
| [`評価/`](評価/) | 適合・性能・回帰・実測証拠 |
| [`src/minidora/`](src/minidora/) | MINIDORA Core実装 |
| [`tests/`](tests/) | 単体・回帰・製品版受入試験 |
| [`docs/`](docs/) | 補助文書・アーキテクチャ・セーブポイント |
| [`構文化/`](構文化/) | 観測・再構成履歴 |
| [`artifacts/`](artifacts/) | 固定取得物・派生成果 |

## 日本語基底

MINIDORAは **日本語を規定言語・基底言語・内部意味正本** とします。英語版は国際公開のための翻訳・互換表層です。

- Cognitive Engineering Foundations: https://github.com/gatchimuchio/cognitive-engineering-foundations
  - 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- LLM Constitutive Specification: https://github.com/gatchimuchio/LLM-Constitutive-Specification
  - 版: `2026-08-28-成立規定-8`
  - 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## 主張の境界

```text
厳密言語模型成立
!= Core汎用能力性能
!= GPQA得点
!= Module込みシステム性能
!= Product Prototype完成度
!= Large
!= GPT-4級性能到達
```

それぞれを別の証拠・評価系列で管理します。

## 検証

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
python -m minidora.製品版 "(12+8)*3"
```

CIはUbuntu / Windows、Python 3.11–3.14を対象にしています。

## ライセンス

- ソースコード・実装: **Apache License 2.0** — [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0)
- 仕様・設計・理論・評価・README等: **CC-BY-4.0** — [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)
- 適用範囲: [`LICENSE`](LICENSE)
- 帰属・第三者由来物: [`NOTICE`](NOTICE)

## Author

**がっちむち♂**
