# NOTNN-LLM-MINIDORA — ミニドラ

> **MINIDORAは「ニューラルネットを使わずにLLMを作ってみた」プロジェクトではありません。**  
> 先にLLMを特定実装から切り離して構成定義し、既存LLMの能力成立作用を構文化したうえで、その構成・作用関係を非ニューラル方式で再実装する研究・実装プロジェクトです。

[English translation](README.en.md) / [製品版デモ](製品版/README.md) / [設計正本](設計/README.md) / [評価・実測](評価/README.md)

## まず結論 — MINIDORAは何をしたのか

MINIDORAの成立順序は、一般に想像されやすい順序と逆です。

```text
「非ニューラルLLMを作りたい」
    ↓
Transformerを別方式へ置換する
```

ではありません。

実際の順序は次です。

```text
1. 既存LLMを「TransformerだからLLM」と扱わず、
   LLMとして何が成立していればよいのかを実装方式から分離する

2. LLMの成立条件・境界・能力作用を構成定義する

3. K3 / GLM等の既存LLMを、固有アーキテクチャ名ではなく
   「何を保持し、何を変化させ、何を後で利用し、
    何を再参照・再結合して能力差を作っているか」へ構文化する

4. その構成と作用関係を、ニューラルネットワークやTransformerを
   中核に使わない別方式で実装する

5. その実装がMINIDORA
```

したがって、MINIDORAの中心的な問いは、

> **現在主流のLLM実装方式と、LLMとして成立するための構成そのものは同一なのか。**

です。

この問いを仕様・実装・実測で分離して確認しています。

---

## なぜTransformer / ニューラルネットワークが必須ではないのか

MINIDORAは、独立した正本 [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification) で、`Large Language Model / LLM` という外部慣用名を **Transformer・ニューラルネットワーク・自己回帰等の特定実装へ固定せず** 監査しています。

現行MINIDORAが固定参照している成立規定では、厳密言語模型の中核を次で分離しています。

```text
完全言語状態空間 L
+ 持続模型状態 M
→ 一つの整合した言語確率法則 P_M(L)
```

そして形成方式について、ニューラル学習やTransformerを普遍必須にはしていません。

```text
言語確率法則の形成方式
├─ ニューラル重み
├─ 計数
├─ 確率文法
├─ 表
├─ 図構造
└─ プログラム
```

ここで重要なのは、

> **「Transformerを否定した」のではなく、言語模型の成立条件と、その現在主流の実現方式を同一視しなかった。**

という点です。

ニューラルネットワークやTransformerは強力な実現方式です。しかし、それをそのまま「LLMそのものの定義」にはしていません。

MINIDORAは、この分離後に残った成立条件を別方式で実装しています。

---

## 「構文化」とは何か

MINIDORAは、既存LLMのソースコードやアーキテクチャをそのまま模倣していません。

公開weight・config・implementation等から観測できる構造を、固有名称から切り離し、**能力差を成立させている作用単位と関係**へ落とします。

LLM構成定義では、能力作用の観測単位を少なくとも次へ分けています。

```text
状態担体
作用
状態差
後続利用
参照変更
経路変更
計算量変更
再参照
再結合
循環尺度
```

例えば、既存LLMの観測から次のような関係を抜き出します。

```text
確定前の状態を保持する
→ 局所作用で状態が変わる
→ 後段でその状態を再利用する
→ 必要なら過去の参照へ戻る
→ 複数の候補・専門作用を再結合する
→ 条件に応じて経路や計算量を変える
```

ここで、KDA、MLA、DSA、MoE、mHC等の名前そのものをMINIDORAへコピーすることが目的ではありません。

```text
既存LLMで観測された構造
        ↓
何の作用が、どの状態差を作り、
その差が後続のどこで利用されるか
        ↓
実装方式に依存しない作用関係へ構文化
        ↓
MINIDORA側の別実装へ射影
```

このため、MINIDORA内に既存LLMと同じ内部機構が存在するとは主張しません。

**観測した機能・作用関係の再現と、元モデルのニューラル因果機構そのものの再現を分離しています。**

構文化の実例:

- [`構文化/K3_GLM_作用比較索引_v1.md`](構文化/K3_GLM_作用比較索引_v1.md)
- [`構文化/K3_能力成立作用構文化_v1/`](構文化/K3_能力成立作用構文化_v1/)
- [`構文化/GLM_5_3_能力成立作用構文化_D4_v1/`](構文化/GLM_5_3_能力成立作用構文化_D4_v1/)
- [`構文化/LLM横断_状態差作用構文化_v2/`](構文化/LLM横断_状態差作用構文化_v2/)

---

## つまり、MINIDORAは何ではないのか

誤読を避けるため、先に境界を示します。

| 誤読 | MINIDORAとの違い |
|---|---|
| **単純なルールベースチャットボット** | 固定応答シナリオを大量列挙することが中心ではない。言語模型核・能力作用・参照・判断・Moduleを分離している |
| **RAG** | 外部参照は利用するが、参照取得だけをLLMとはしていない。言語模型核と能力経路を別に持つ |
| **既存LLMの蒸留・量子化** | 既存ニューラル模型の重みを縮小・圧縮したものではない |
| **Transformer代替ニューラルネット** | 中核を別のニューラルアーキテクチャへ置換したものではない |
| **AI Agent** | Tool利用や自律実行だけをもってLLMと呼んでいるわけではない |
| **GPT-4級性能の宣言** | 現時点でフロンティアLLMと同等の総合性能を主張していない |

MINIDORAが検証しているのは、**LLMの構成・能力作用・実現方式を分離したとき、非ニューラル方式でどこまで再構成できるか**です。

---

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
既存LLMの構文化
    ↓ 実装固有名から作用関係を分離
MINIDORA Core
    ↓ 非ニューラル方式で再実装
交換可能なCapability Module
    ↓
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

## 現在どこまで成立しているか

MINIDORAでは、次を別々の成立・評価系列として管理しています。

```text
厳密言語模型成立
!= Core汎用能力性能
!= Module込みシステム性能
!= Product Prototype完成度
!= Large
!= GPT-4級性能到達
```

### 厳密言語模型核

非ニューラルな厳密言語模型核を実装し、完全言語状態・持続模型状態・整合した言語確率法則の境界を独立監査しています。

### Core汎用能力

専門solverをactive pathから外した2026-09-01 GPQA Diamond全198問:

```text
正式MINIDORA汎用模型核 / HDS非介入 = 19 / 198  (9.60%)
最小汎用Core + HDS異常時最小介入  = 23 / 198 (11.62%)
```

この値は現行Core能力の観測であり、MINIDORAがGPT-4等のフロンティアモデルと同等性能であることを示しません。

### Capability Moduleによる能力追加

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

これは **63/198をCore単体性能として主張するものではありません**。

観測したのは、**同一Coreを再学習せず外部Capabilityを追加し、その能力差が実性能差として発現したこと**です。

---

## 製品版デモ

ハッカソンでは「今日のニュースは？ → 3行で要約して」を見せる設計ですが、ニュース専用デモではありません。製品版は共通Capability契約とレジストリを持ち、日常能力をModuleとして追加できる構成です。

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
| [`構文化/`](構文化/) | 既存LLM等の観測・作用分離・再構成履歴 |
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
