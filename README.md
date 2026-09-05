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

この問いを、仕様・実装・機構実測・能力実測に分けて確認しています。

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

# ここを誤読するとMINIDORAの意味が変わる — GPQA / Module / 推論

MINIDORAの実測を読むとき、次の3点を混同しないでください。

```text
GPQAを使う理由
!= GPQA得点そのものを成果にすること

Module追加
!= Core再学習
!= fine-tuning
!= Coreへの専門知識の焼き込み

推論機構の成立
!= 正答率が高いこと
!= Chain-of-Thought文章を生成すること
!= 人間同等の一般推論が成立したこと
```

## なぜGPQA Diamondを使っているのか

GPQA Diamondは、MINIDORAがLLMであることを定義するためのベンチマークではありません。また、GPQAの点数だけから「推論が成立した」と主張するためにも使っていません。

MINIDORAにとってGPQA Diamondは、**同じ固定問題集合に対し、内部の一つの機構・接続条件だけを変えたとき、外部から観測できる状態差・能力差が本当に発生するかを測るための観測面**です。

使いやすい理由は次です。

1. **198問の固定有限集合**であり、同一問題を条件差だけ変えて繰り返し測定できる。
2. **正答goldが固定**されており、内部機構の実行後に結果差を客観的に採点できる。
3. 科学・専門知識を要する問題群なので、**科学専門Capabilityを外付けしたときの能力差**を観測しやすい。
4. 問題番号やgoldを推論に使わず、dataset hash・seed・artifact・workflowを固定して、測定境界を監査できる。
5. 絶対スコアだけでなく、**同一baselineに対するOFF/ON差分**を測れる。

このリポジトリでは、GPQA Diamondを少なくとも2つの異なる目的で使っています。

| 実験 | 見ているもの | 何を変えるか | 何を直接示すか |
|---|---|---|---|
| 2026-08-28 能力状態差循環 | 状態差が次作用選択へ到達するか | 状態差循環・再作用機構 | 推論・知識処理の**機構が実際に作動したか** |
| 2026-09-02 科学専門能力Replay | 外部専門Moduleの純寄与 | Module OFF / ON | 同一CoreへCapabilityを接続して**実効能力を後付けできるか** |

したがって、同じGPQAという名前が出ていても、**機構実験とModule能力実験を同じ主張へ圧縮しません。**

詳細:

- [能力状態差循環 GPQA実測](評価/MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md)
- [既存科学専門能力 Replay実測](評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)

## 「Module追加」とは何か

MINIDORAのCapability Moduleは、成立済みCoreの外側へ責任分離した**追加可能・交換可能・監査可能な能力単位**です。

```text
Core      = LLMとしての成立・汎用作用
Data      = 外部化可能
Knowledge = 外部参照可能
Module    = 分離・追加・交換可能な能力
Compute   = 汎用計算
HDS       = 制御
```

Module追加は次ではありません。

- Coreの再学習
- fine-tuning
- 重み更新
- Transformer追加学習
- Core大型化
- Core置換
- benchmark正答表の埋め込み
- 「Module込みの性能」をCore単体性能と呼ぶこと

成立済みの拡張形式は次です。

```text
同一baseline / 同一Core
        │
        ├─ Module OFF → baseline結果
        │
        └─ Module ON
             ├─ Module成立 → Module由来結果
             └─ Module不成立 → baseline結果を継承
```

能力Moduleは、少なくとも責任範囲・発火条件・実行結果・由来を追跡でき、成立しない入力では勝手な候補選択を行わず通常経路へ透過します。

2026-09-02のcontrolled replayでは、リポジトリ内に既に存在していた科学専門能力群を明示接続し、新しいGPQA解法器・gold参照solver・問題番号分岐を追加せず、次を観測しました。

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

このReplay境界では、Moduleが発火した55問は55問すべてgoldと一致し、Module不発火問題には新しい差を作っていません。

したがって、この実験の中心的な意味は **31.82%という絶対スコアではありません。**

> **成立済みMINIDORA Coreを能力追加のために再学習・再訓練・大型化・置換せず、外部Capabilityを追加接続するだけで、システム全体の実効能力を後から増設でき、その増設が外部benchmark上の正答差として観測された。**

ということです。

つまり、MINIDORAでは少なくとも今回実証した範囲で、

```text
能力を増やす
!=
Coreそのものを学習し直す
```

が成立しています。

詳細:

- [能力Module拡張境界](設計/35_MINIDORA_能力Module拡張境界_v1.md)
- [モジュール拡張成立実証](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [モジュール拡張可能性 成立実証](評価/MINIDORA_モジュール拡張可能性_成立実証_2026-09-03.md)
- [GPQA Diamond 既存科学専門能力 Replay](評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)

## 「推論機構が成立している」とは何か

本リポジトリで「推論機構が成立している」と呼ぶとき、**正答したこと、説明文を生成したこと、Chain-of-Thoughtらしい文章を書いたこと**を根拠にはしません。

ここで観測対象にしているのは、実行系内部で次の因果的な処理関係が本当に通ったかです。

```text
状態 S_t
  ↓
作用 A_t
  ↓
状態差 ΔS_t
  ↓
更新状態 S_t+1
  ↓
状態差が実際の次作用選択へ到達
  ↓
後続作用 A_t+1
  ↓
必要なら新しい候補状態差
  ↓
再活性 / 再照合 / 再結合
  ↓
結果
```

重要なのは、**前段の状態差が後段の作用を実際に変えること**です。

単に複数ステップのログを並べたり、後から「こう考えた」と説明文を生成しただけでは、本リポジトリでは推論機構成立の証拠にしません。

### 直接の実測根拠

2026-08-28、GPQA Diamond全198問を使った能力状態差循環の機構実測では次を観測しました。

```text
completed                  = 198
checkpoint_count           = 725
checkpoint_reactivations   = 134
global_reconciliations     = 134
candidate_cross_updates    = 21
specialist_actions_invoked = 0
```

再活性回数は次のように分かれました。

```text
再活性0回 = 85問
再活性1回 = 92問
再活性2回 = 21問
```

観測された関係は次です。

```text
一次能力作用で状態差なし
→ 再活性0

一次能力作用で状態差あり
→ 再活性1

再作用によってさらに新しい候補状態差が生成
→ 候補横断更新
→ 再活性2
```

この実測では、少なくとも次の機構受入がPASSになっています。

```text
状態差なしで不発火             = PASS
状態差による再活性             = PASS
再作用後の新状態差             = PASS
新状態差による二段目再活性     = PASS
同一証拠の別名再加点禁止       = 機構試験PASS
Compiler作用差分の厳格不発火   = PASS
```

実装・試験・実測はそれぞれ分離されています。

- 実装: [`src/minidora/能力状態差循環.py`](src/minidora/能力状態差循環.py)
- 機構試験: [`tests/test_能力状態差循環_v1.py`](tests/test_能力状態差循環_v1.py)
- GPQA全198問実測: [`評価/MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md`](評価/MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md)

### ただし「推論機構がある」と「推論性能が高い」は別

同じ2026-08-28実測では、GPQA能力改善そのものは失敗しています。

```text
current             = 16 / 198
controlled baseline = 22 / 198
correct_delta       = -6
```

評価文書自身も次を未成立として残しています。

```text
GPQA能力改善                    = FAIL
現行次作用選択の妥当性          = 未成立
現行一次能力作用の十分性        = 未成立
Compiler作用差分のGPQA実消費    = 0件
再作用単独の因果寄与            = 未分離
```

したがって、このリポジトリが強く主張できる範囲は、

> **状態差が次作用を変え、後続作用が新しい状態差を作り、その差がさらに後続処理へ利用される多段の推論機構が実装・試験・全問実測で作動した。**

までです。

ここから直接、

```text
人間同等の一般推論
AGI
高いGPQA性能
フロンティアLLM同等能力
```

を導きません。

むしろ、この失敗実測によって、**「推論機構が存在すること」と「その作用選択が良く、能力が高いこと」を分離して評価できる**こと自体を保持しています。

---

## つまり、MINIDORAは何ではないのか

誤読を避けるため、境界を明示します。

| 誤読 | MINIDORAとの違い |
|---|---|
| **単純なルールベースチャットボット** | 固定応答シナリオを大量列挙することが中心ではない。言語模型核・能力作用・参照・判断・Moduleを分離している |
| **RAG** | 外部参照は利用するが、参照取得だけをLLMとはしていない。言語模型核と能力経路を別に持つ |
| **既存LLMの蒸留・量子化** | 既存ニューラル模型の重みを縮小・圧縮したものではない |
| **Transformer代替ニューラルネット** | 中核を別のニューラルアーキテクチャへ置換したものではない |
| **AI Agent** | Tool利用や自律実行だけをもってLLMと呼んでいるわけではない |
| **GPQA専用solver** | benchmark問題番号・gold表をCoreへ埋め込んでLLMと呼んでいるわけではない |
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
!= 推論機構成立
!= Core汎用能力性能
!= Module込みシステム性能
!= Product Prototype完成度
!= Large
!= GPT-4級性能到達
```

### 厳密言語模型核

非ニューラルな厳密言語模型核を実装し、完全言語状態・持続模型状態・整合した言語確率法則の境界を独立監査しています。

### 推論機構

状態差が後続作用選択へ到達し、再作用による新状態差と二段目再活性まで実測済みです。ただし、推論機構成立と推論性能改善を分離しており、2026-08-28 GPQA実測の能力改善はFAILとしてそのまま保持しています。

### Core汎用能力

専門solverをactive pathから外した2026-09-01 GPQA Diamond全198問:

```text
正式MINIDORA汎用模型核 / HDS非介入 = 19 / 198  (9.60%)
最小汎用Core + HDS異常時最小介入  = 23 / 198 (11.62%)
```

この値は現行Core能力の観測であり、MINIDORAがGPT-4等のフロンティアモデルと同等性能であることを示しません。

### Module込みシステム能力

科学専門能力Moduleを接続したcontrolled replayでは、Module OFF 8/198からON 63/198へ変化し、55発火・55改善・0退行を観測しました。

この値はCore単体性能ではなく、**同一Coreへ外部Capabilityを追加したシステム能力差**です。

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

Moduleの設計上の意味は「APIを呼べる」ことではなく、次の一連が成立することです。

```text
Moduleを追加できる
↓
対象入力で発火する
↓
追加能力が実際に作用する
↓
Module不発火時は既存経路を汚染しない
↓
能力差を外部評価で観測できる
```

詳細:

- [能力Module拡張境界](設計/35_MINIDORA_能力Module拡張境界_v1.md)
- [モジュール拡張成立実証](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [モジュール拡張可能性 成立実証](評価/MINIDORA_モジュール拡張可能性_成立実証_2026-09-03.md)
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
!= 推論機構成立
!= Core汎用能力性能
!= GPQA得点
!= Module込みシステム性能
!= Product Prototype完成度
!= Large
!= GPT-4級性能到達
```

さらに、LLM構成定義の境界に従い、次も同一視しません。

```text
局所作用再現
!= 作用関係再現
!= 意思決定構造再現
!= 能力主体
```

それぞれを別の証拠・評価系列で管理します。

製品版の長期開発目標は **GPT-4級の一般チャット使用感** です。これは現時点の同等性能宣言ではなく、会話・要約・知識参照・比較・推論・計算・変換・検索・コード等の実利用能力をModuleとして増設し、実測で到達度を判断する目標です。

v0.5における **Large** 判定は **再監査** 対象であり、旧版の規模評価を自動継承しません。

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
