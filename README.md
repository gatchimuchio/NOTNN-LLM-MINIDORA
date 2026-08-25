# ミニドラ（MINIDORA）

**NOTNN-LLM-MINIDORA** は、巨大ニューラルネットワークやTransformerをRuntime成立条件にせず、言語模型の成立関係を通常計算機上の明示構造として実装する、日本語基底の非ニューラルネットワークLLM研究・実装リポジトリです。

- 基底・規定言語: **日本語**
- 正本ブランチ: **`main`**
- 現行Runtime: **MINIDORA v0.4**
- 上流正本: **大規模言語模型成立規定 `2026-08-26-成立規定-2`**
- v0.3プロトタイプ状態: **PROTOTYPE COMPLETE — 2026-08-22（履歴固定）**
- v0.4大規模性: **再測定要**
- ライセンス: **Apache License 2.0**
- 著作: **がっちむち♂**
- 実装言語: Python 3.11+

## 上流正本

MINIDORAはLLMの成立条件を本リポジトリ内で独自再定義しません。

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版: `2026-08-26-成立規定-2`
- MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`

局所写像は [`設計/02_大規模言語模型成立契約.md`](設計/02_大規模言語模型成立契約.md) を正本とします。

旧 `Layer-0` は歴史上の暫定名称です。旧v4責任契約は [`設計/旧/02_Layer0責任契約_v4.md`](設計/旧/02_Layer0責任契約_v4.md) に履歴として残します。

## v0.4で何を作り直したか

旧MINIDORAでは、算術・比較・状態更新等を実行する汎用命令器を `Layer0` と呼び、LLM成立責任の中心へ置いていました。

新しい上流規定と突合すると、この実体はLLM模型中核ではなく**計算実行器**です。

v0.4では主語を入れ替えます。

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

これが現行MINIDORAの模型中核です。

実装:

- [`src/minidora/模型.py`](src/minidora/模型.py) — LLM模型中核。
- [`src/minidora/計算実行器.py`](src/minidora/計算実行器.py) — 汎用計算作用。
- [`src/minidora/layer0.py`](src/minidora/layer0.py) — 旧API互換窓口。
- [`src/minidora/runtime.py`](src/minidora/runtime.py) — v0.4統合Runtime。

## 模型中核

現行模型核は確率分布やsamplingを必須形式にしません。

候補ごとに、文脈と再利用可能な模型関係から**成立差**を決定論的に形成します。

```text
文脈付き内部状態
  ×
模型関係群
  ×
候補言語状態
  ↓
候補ごとの成立差 + 寄与根拠
```

根拠差が0、または最上位が同率の場合は、一候補へ勝手に確定しません。

### 言語体系

既定は日本語自然言語ですが、模型契約そのものは自然言語だけに限定しません。

```python
from minidora import MINIDORA模型核, 関係規則, 言語状態, 成立候補

core = MINIDORA模型核((
    関係規則(
        "日本首都",
        文脈必須=frozenset({"日本"}),
        候補必須=frozenset({"東京"}),
        差=5,
    ),
))

result = core.評価言語状態(
    言語状態("日本 首都", "自然言語:ja"),
    (
        成立候補("東京", 言語状態("東京", "自然言語:ja")),
        成立候補("パリ", 言語状態("パリ", "自然言語:ja")),
    ),
)

assert result.最有力候補ID == "東京"
```

プログラム言語等も、対象言語体系を明示したうえで同じ模型核へ渡せます。

## Runtime入口

v0.4 `ミニドラ` は模型核を直接保持します。

```python
from minidora import ミニドラ

body = ミニドラ()
result = body.言語評価(
    "東京 日本",
    ("東京 日本", "パリ フランス"),
)
print(result.候補辞書())
```

`言語評価` は候補生成・外部検索・samplingを行いません。与えられた言語状態に対する成立差を返す模型中核入口です。

## 既存CLIと運用経路

既存CLIは互換維持します。

```bash
python -m pip install -e .
python -m minidora "2+3"
```

出力例:

```text
5です。
```

機械可読確認:

```bash
python -m minidora --json "2+3"
```

この算術経路はLLM模型中核の証明ではなく、**HDS意味Projection / 日本語命令形P / 計算実行器 / 採否 / 表面化**を通る既存運用互換経路です。

## 計算実行器

旧 `Layer0` 実装は削除せず、役割を正して保持します。

```text
日本語命令形P
    ↓
計算実行器
    ↓
算術 / 比較 / 取得 / 抽出 / 状態更新
```

`Layer0` という旧公開名は互換aliasです。新規設計ではLLM模型中核を意味しません。

## HDSの位置

HDSは引き続き重要な観測・意味Projection・運用手段です。しかしHDSであること自体をLLM成立条件にしません。

```text
外部入力
  ↓
公開HDS Compiler
  ↓
HDS-IR
  ↓
参照 / 選択 / 互換命令計画

別の模型中核:
言語状態 → 言語対応 → 模型側関係 → 成立差
```

HDS-IRをLLM模型中核やCompute IRと同一視しません。

今回のv0.4再構成ではHDS Compiler本体を先回り改造していません。次段でCompute IR / lowering境界を確定してからCompiler側を再設計します。

詳細は [`設計/07_HDS_IR入力契約.md`](設計/07_HDS_IR入力契約.md) を参照してください。

## 外部参照R

参照Rは外部Dataです。取得したDataを模型側関係の内部知識と自動同一視しません。

同一対象・同一意味キー・同一時点・同一範囲・同一条件であることが確定した場合だけ値競合を矛盾として扱う既存境界を維持します。

## 主体主幹

主体主幹はturnを跨ぐ主体状態、理由付き更新、自己一貫性Gateを担います。

これはLLM模型中核の追加部品ではなく、MINIDORAの運用主体性を担う外周機構です。

## K3 / Llama / 横断構文化

K3、Llama 3、その他LLMの構文化は、能力構造の観測・比較資産です。

公開MINIDORA Runtimeがそれらのニューラル推論を呼び出すことを成立条件にしません。

横断観測資産は `構文化/` に保持します。

## 大規模性

上流正本では、言語模型性と大規模性を分けます。

- 状態域規模
- 関係域規模
- 共有適用規模

v0.3のGPQA等の値は、その当時の統合経路に対する固定実測です。v0.4模型核の大規模性へ無言転用しません。

したがってv0.4移行直後の大規模性は **再測定要** とします。旧能力を否定する意味ではなく、実装境界変更後の評価を正しく分けるためです。

## v0.3プロトタイプ完成記録

2026-08-22の **PROTOTYPE COMPLETE** 判定は履歴固定です。

これは当時の非ニューラル／非Transformer経路が閉じ、外部未知ベンチで非ゼロ能力を発生させたことを示します。

```text
PROTOTYPE COMPLETE
!= v0.4大規模性の自動成立
!= 製品・最終完成
!= K3級性能
```

正本記録: [`評価/PROTOTYPE_COMPLETION_2026-08-22.md`](評価/PROTOTYPE_COMPLETION_2026-08-22.md)

## 非ニューラル境界

公開Runtimeの依存パッケージは引き続き0です。

- `torch` 不要
- `transformers` 不要
- `numpy` 不要
- モデルAPIへの依存不要

ニューラルモデルは観測・比較対象であり、公開MINIDORAの実行依存ではありません。

## 検証

```bash
python tools/repository_consistency_check.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはUbuntu / Windows × Python 3.11–3.14で実行します。

## ライセンス

本リポジトリの独自実装・独自文書は **Apache License 2.0** で提供します。詳細は `LICENSE` と `NOTICE` を参照してください。

第三者由来物には各出典・原著作者のライセンスと利用条件が適用されます。
