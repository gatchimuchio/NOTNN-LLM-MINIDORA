# NOTNN-LLM-MINIDORA — ミニドラ

> **ミニドラは、ニューラルネットワーク（NN）やTransformerを使わず、最小・最軽量・シンプルな構成でLLMとして成立する汎用言語模型核を作るプロジェクトです。**

MINIDORAは、日本語を基底・規定・内部意味正本とする非ニューラルネットワーク型LLM研究実装です。

目的は、専門知識・専門solver・巨大な内部Dataを本体へ詰め込み続けて性能を作ることではありません。

**少数の一般作用だけを持つ小さなLLM核を成立させ、Data・専門知識・専門処理は必要に応じて外部参照またはモジュールとして接続する。**  
これがMINIDORAの基本パラダイムです。

現行安定版は **v0.5.0**。  
2026-09-01時点の現行セーブポイントは **最小汎用LLM core + HDS異常時最小介入** です。

## モジュール拡張可能性は実証済み

MINIDORAの「Module」は将来構想ではありません。

> **MINIDORAは既にLLMとして成立している。その成立済みCoreを再学習・再訓練・大型化せず、外部の能力Moduleを追加接続することで実効能力と性能を後から拡張できる。これはGPQA Diamond 198問のcontrolled replayで実測済みです。**

この実証の主題は「科学Moduleを付けたらGPQAの点数が上がった」ことではありません。

主題は、

> **MINIDORAの能力面が閉じた一枚岩ではなく、Coreと能力Moduleを責任分離したまま、Module接続によって能力を追加・増設でき、その追加能力が実際の性能向上として発現することまで成立した**

ことです。

2026-09-02の既存科学専門能力Replayでは、保存済みFormal currentへ既存Module群を接続しただけで次の差が観測されました。

| 条件 | 正答 | 全体正答率 | 回答時正答率 |
|---|---:|---:|---:|
| Module OFF | 8 / 198 | 4.04% | 20.51% |
| Module ON | **63 / 198** | **31.82%** | **73.26%** |

```text
Module発火  55
改善        55
退行         0
正答差      +55
```

不発火時は保存済みbaselineをそのまま返すため、差分はModuleが実際に作用したケースへ局所化されています。発火した55ケースは、このReplay境界では55ケースすべてgoldと一致しました。

したがって、この測定は「63/198というスコア」をMINIDORA coreの性能として主張するものではなく、**能力追加がCore全体の再学習ではなく独立Moduleの接続として成立し、それを反復することでシステム能力を継続的に伸ばせることの実装・実測証拠**として保持します。

### 固定有限ベンチでは理論上100%まで到達可能

GPQA Diamondは198問の固定有限集合です。

今回、その未被覆集合のうち55問を、Coreを再学習せずModule追加だけで新たに正答可能へ変えました。

未被覆問題へ正しく作用するModuleを追加し、不発火時の透過性と既存正答を退行させない接続境界を維持できる限り、未被覆集合は反復的に縮小できます。

```text
未被覆 U0
↓ Module追加
U1 ⊂ U0
↓ Module追加
U2 ⊂ U1
↓
...
↓
未被覆 = 0
```

したがって、**GPQA Diamondのような固定有限ベンチに限れば、Module被覆を追加し続けることで理論上100%へ到達可能な構成です。**

これは「100%を既に実測した」という主張ではありません。

重要なのは、**100%へ向かう性能向上経路そのものが、巨大模型の再学習ではなく、成立済みMINIDORA Coreへ能力Moduleを追加する方式として実装上開かれた**ことです。

つまりMINIDORAの能力上限は、成立時点のCore単体スコアへ固定されません。接続するCapability集合を増やすことで、成立済みCoreを維持したままシステム能力を後から押し上げられます。

詳細:

- [`評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [`評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md`](評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)

## MINIDORAは何を変えるのか

一般的な大規模ニューラルLLMは、知識・言語・専門能力・個別タスク能力を主として学習済み重みや追加学習へ内部化します。

```text
知識
+ 言語能力
+ 数学能力
+ 科学能力
+ coding能力
+ 各種専門能力
        ↓
巨大なニューラル模型へ内部化
        ↓
性能向上とともに模型も肥大化
```

MINIDORAはこの方向を採りません。

```text
最小汎用LLM核
+ 外部Data
+ 外部参照R
+ 汎用計算実行器
+ 必要時だけ専門モジュール
+ HDSによる異常時最小介入
```

専門領域が必要なら、物理・化学・法律・医学・codingなどを**本体へ焼き込まず外部モジュールとして接続**します。

したがってMINIDORA本体で測りたいものは「どれだけ専門機能を持っているか」ではなく、

> **何も盛っていない最小の一般作用だけで、未知入力へどこまで同じ汎用処理を適用できるか**

です。

## パラダイム

MINIDORAでは、能力追加より先に責任を分離します。

```text
Core      = 汎用作用
Data      = 外部化可能
Knowledge = 外部参照可能
Module    = 専門領域
Compute   = 汎用計算
HDS       = 異常時だけ最小制御
```

本体へ新しい機能を追加する場合は、最低限次を満たす必要があります。

1. benchmark名・分野名・問題名を消しても一般作用として成立する。
2. 既存一般作用の組合せでは表現できない。
3. Dataまたは外部専門モジュールへ分離できない。

この三つを満たさない機能は原則としてcoreへ入れません。

## 現行構造

```text
入力
↓
HDS Compiler
↓
意味IR / 計算計画 / Data
↓
MINIDORA能力模型核
↓
必要な場合だけ
  ├─ REFERENCE
  └─ EXISTING_COMPUTE_EXECUTOR
        ↑
       HDS
  異常時のみ最小介入
↓
通常MINIDORAへ復帰
↓
出力
```

### 厳密言語模型核

MINIDORAは、完全言語状態空間と持続模型状態の上に、整合した言語確率法則を持つ非ニューラル言語模型核を実装しています。

```text
完全言語状態空間
+ 持続模型状態
→ 整合した言語確率法則
→ 条件分布
→ 連鎖則 + 終端
→ 完全系列確率
```

現行実装は `src/minidora/言語確率法則.py`。

### 能力模型核

能力模型核は、候補・証拠・関係・状態差を一般作用として扱います。

```text
状態担体
↓
作用
↓
状態差
↓
後続利用
↓
必要なら再参照 / 再結合 / 汎用計算
```

専門分野ごとの答え方を本体へ列挙する設計ではありません。

### HDS

HDSは回答主体ではなく**安全弁**です。

通常MINIDORAが自力で閉包した場合は介入しません。未閉包・競合・観測不足・停滞などの異常時だけ、既存の汎用作用を起動して通常MINIDORAへ戻します。

HDSは回答を生成せず、候補の勝者を選びません。

詳細: [`設計/32_MINIDORA_HDS監督介入制御_v1.md`](設計/32_MINIDORA_HDS監督介入制御_v1.md)

## 専門能力の扱い

専門solverはMINIDORA本体の汎用性能に含めません。

```text
MINIDORA core
├─ 汎用言語模型
├─ 汎用能力模型
├─ 汎用計算
├─ 外部参照
└─ HDS最小介入

外部module
├─ 物理
├─ 化学
├─ 医学
├─ 法律
├─ coding
└─ その他専門領域
```

Module追加による能力拡張そのものは2026-09-02に実測済みです。ただし、それによって上がった性能をcore単体の汎用性能とは扱いません。

この区別は重要です。

```text
Module接続で能力を拡張できる
!=
Module込みの得点をCore単体性能と呼ぶ
```

前者は成立済みの実装特性、後者は採用しない評価上の混同です。

## benchmarkの位置づけ

benchmarkは**性能を作るための仕様書ではなく、汎用能力を外部から観測する試験**です。

GPQAで高得点を取るだけなら、科学専門solverを追加し続けることもできます。しかしそれではMINIDORA本体の一般能力を測れません。

そのため現行セーブポイントでは専門solverをactive pathから外してcoreを測定しています。

一方、専門solverを接続したcontrolled A/Bは、**Core点数の測定ではなくモジュール拡張可能性の成立実証**として別系列に保持します。

### GPQA Diamond — 2026-09-01 Core測定

198問 controlled A/B:

```text
正式MINIDORA汎用模型核 / HDS非介入 baseline = 19 / 198  (9.60%)
最小汎用core + HDS異常時最小介入         = 23 / 198 (11.62%)
差分                                      = +4問 / +2.02pt
専門作用起動                              = 0
```

このスコア自体を完成指標にはしません。重要なのは、専門solverなしの同一汎用coreで測定していることです。

詳細: [`評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)

### GPQA Diamond — 2026-09-02 Module拡張実証

```text
Module OFF = 8 / 198  (4.04%)
Module ON  = 63 / 198 (31.82%)
発火       = 55
改善       = 55
退行       = 0
```

これはCore性能比較ではなく、**同一Coreへ外部Moduleを接続して能力を追加できることの成立証拠**です。

この系列が示すのは「63/198が高い」ということではなく、**Module追加を能力向上操作として反復できる**ことです。固定有限ベンチでは、この被覆追加を続けることで理論上100%へ到達可能な構成が成立しています。

詳細: [`評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)

## 日本語基底

MINIDORAでは日本語を、説明用言語ではなく**内部意味正本・設計正本・規定言語**として扱います。

```text
日本語で対象化・差異化・関係化
↓
日本語で設計・構文化・監査
↓
日本語正本を保持
↓
外部API・規格・固有名など必要な境界だけ他言語を使用
```

英語等を第二基底や並列正本にはしません。

局所規定: [`設計/00_日本語基底規定_v1.md`](設計/00_日本語基底規定_v1.md)

## Authority

詳細な優先順位は [`AGENTS.md`](AGENTS.md) を正とします。

最上位理論正本:

- Repository: `https://github.com/gatchimuchio/cognitive-engineering-foundations`
- 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 基底言語・規定言語: 日本語

LLM成立条件の責任正本:

- Repository: `https://github.com/gatchimuchio/LLM-Constitutive-Specification`
- 版: `2026-08-28-成立規定-8`
- 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## 現行セーブポイント

2026-09-01の確定点:

- 最小汎用LLM core
- 専門solver active path = なし
- 旧K3 helper通常先行実行 = なし
- HDS = 異常時安全弁
- HDSによるwinner selection = なし
- 外部R = 汎用参照
- Compute IR = 汎用計算
- GPQA 198問実測済み
- main一本運用

追加成立特性:

- **外部能力Moduleによる能力拡張 = 実測済み**
- **Module追加による性能向上 = 実測済み**
- **能力追加のためのCore再学習 = 少なくとも実証済み科学能力群では不要**
- **固定有限ベンチでの反復Module被覆による100%到達経路 = 構成上成立**

詳細:

- [`docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md)
- [`評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)

## 試験

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIは Ubuntu / Windows × Python 3.11–3.14 を対象にします。

## 文書入口

- [`AGENTS.md`](AGENTS.md) — 実装・監査規約
- [`設計/README.md`](設計/README.md) — 現行設計正本ガイド
- [`設計/00_日本語基底規定_v1.md`](設計/00_日本語基底規定_v1.md) — 日本語基底
- [`設計/30_MINIDORA能力状態差循環_v1.md`](設計/30_MINIDORA能力状態差循環_v1.md) — 汎用能力状態差循環
- [`設計/32_MINIDORA_HDS監督介入制御_v1.md`](設計/32_MINIDORA_HDS監督介入制御_v1.md) — HDS安全弁
- [`docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md) — 現行セーブポイント
- [`評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md) — Module拡張成立証拠
- [`評価/README.md`](評価/README.md) — 実測履歴

## 能力・Large・呼称

```text
LLM核成立
!= 高推論能力
!= benchmark高得点
!= 専門能力の多さ
!= Largeの十分条件
```

MINIDORAはLLM核としての成立と汎用能力を分けて監査します。

同時に、成立済みCoreの外へCapabilityを分離し、Moduleとして追加することで、**システム全体の能力と性能を成立後も拡張できる**ことが実証済みです。

`Large`および現代的LLM呼称との対応範囲は必要に応じて再監査します。

## ライセンス

- **ソースコード、実行系、Compiler、ライブラリ、テスト、ツール、CI・パッケージ設定**: Apache License 2.0 (`Apache-2.0`)
- **仕様、設計、理論、論文、解説、図表、構文化・評価文書、README等**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`)

これはデュアルライセンスではありません。適用範囲は `LICENSE`、正式条件は `LICENSE-APACHE-2.0` / `LICENSE-CC-BY-4.0`、帰属は `NOTICE` を参照してください。