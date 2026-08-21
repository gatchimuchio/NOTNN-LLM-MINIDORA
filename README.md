# ミニドラ（MINIDORA）

**NOTNN-LLM-MINIDORA** は、巨大ニューラルネットワークや Transformer を実行基盤とせず、LLM的機能を通常計算機上の分離構造として実装する非ニューラルネットワークLLMの研究・実装リポジトリです。

- 基底言語: **日本語**
- 正本ブランチ: **`main`**
- 現行Runtime: **MINIDORA v0.3**
- プロトタイプ状態: **PROTOTYPE COMPLETE — 2026-08-22**
- Layer-0: **v4.0-provisional**
- ライセンス: **Apache License 2.0**
- 著作: **がっちむち♂**
- 実装言語: Python 3.11+

## 最初に読む — 論理基盤と正本階層

MINIDORAはLayer-0の意味を本リポジトリ内で独自再定義しない。

LLM機能責任の**論理上位契約**は、外部Repository:
[gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification](https://github.com/gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification)
を参照する。

- 現行仕様: `v4.0-provisional`
- MINIDORA参照commit: `4adf86d13d7beb99fe5eaa9e240b22996ba3d3bc`
- 現行5責任: 言語アドレス化 / 文脈束縛状態 / 変換・合成中核 / 文脈依存結果形成 / 結果表面

MINIDORA側の [`設計/02_Layer0責任契約.md`](設計/02_Layer0責任契約.md) は、上位Layer-0契約をMINIDORAへ写像する局所契約である。`src/minidora/layer0.py` はその実装であり、Layer-0そのものの代替正本ではない。

```text
外部Layer-0正本
  ↓ 論理上位契約
設計/02_Layer0責任契約.md
  ↓ MINIDORA局所写像
src/minidora/layer0.py + Runtime
  ↓ 実装
 tests/ + 評価/
  ↓ 検証
```

外部参照の位置づけ・更新規則・優先順位は [`REFERENCES.md`](REFERENCES.md) を正本とする。

## 状態の読み方

`PROTOTYPE COMPLETE` と製品・最終完成は別状態である。

```text
PROTOTYPE COMPLETE
= 正規アーキテクチャ経路が閉じ、外部未知問題で測定可能な非ゼロ能力を発生

PROTOTYPE COMPLETE
!= K3級性能
!= 製品・最終完成
!= 将来のスケーリング上限確定
```

プロトタイプ完成記録は [`評価/PROTOTYPE_COMPLETION_2026-08-22.md`](評価/PROTOTYPE_COMPLETION_2026-08-22.md)、製品・最終完成の関門は [`設計/05_完成判定関門.md`](設計/05_完成判定関門.md) を参照する。

## 30秒で確認する

公開Runtimeは、HDS Compilerを用意しなくてもLegacy互換経路を使って即時実行できる。

```bash
python -m pip install -e .
python -m minidora "2+3"
```

出力:

```text
5です。
```

採否境界まで機械可読で確認する場合:

```bash
python -m minidora --json "2+3"
```

インストール後は `minidora "2+3"` でも同じ入口を利用できる。引数を省略すると対話入力になる。

### 実装上の非ニューラル境界

現行の公開Runtimeについて、非ニューラル性は名称ではなく実行依存として確認できる。

- `pyproject.toml` のRuntime依存パッケージは **0**
- `torch` / `transformers` / `numpy` をRuntime依存として要求しない
- K3 / Llama 3は構文化・比較・設計上の観測基盤であり、公開Runtimeがそれらのニューラルモデル推論を呼び出すことを成立条件としない
- HDS Compiler内部実装は公開Runtimeから分離され、公開側はHDS-IR受入契約だけを持つ

## 現在の設計軸

MINIDORA v0.3は次の非対称構造を採る。

```text
Layer-0 v4          = LLM機能責任の論理上位契約
K3                  = 主たる能力・状態関係の観測基盤
Llama 3             = 自己一貫性の対抗基準
その他LLM           = K3 / Llama 3差分の補助観測点
HDS / 日本語構文化  = 上流の分別・再射影手段
```

現行Runtimeでは、K3由来の能力構造とLlama 3で観測した自己一貫性の成立関係を分離し、主体主幹・P・R・HDS-IR・Trinity文脈へ外在化する。

## 通常利用入口

利用者が日本語命令Pを事前に組み立てることを前提にしない。

HDS Compilerが接続されている場合、自然言語入力はHDSで意味付けされた `HDS-IR` としてRuntimeへ渡す。公開MINIDORAはCompiler内部方式ではなく、HDS-IRの受入・実行境界を規定する。

```text
自然言語入力 / 外部Data
  ↓
HDS意味Projection
  ↓
HDS-IR
  ├─ 座標
  ├─ 関係
  ├─ 暫定性
  ├─ 由来
  ├─ 残差
  └─ 意味作用履歴
  ↓ 実行可能な局所閉包のみ
Layer-0 × 日本語命令形 P
  ↓
主体整合Gate / 採否
  ↓
結果
  ↓
HDS履歴へ帰還
```

HDS-IRはHDS Nativeそのものではなく有限Projectionである。固定した最終スキーマとは扱わず、未分別・表現不能・競合をResidualとして保持できる。

`P = どう処理するか`、`Data = 何を意味し、何について処理するか` を分離する。言い換え表現や属性・時点・範囲などの意味情報を、新しいPとして増殖させない。

HDS Compilerは `HDSコンパイラProtocol` を満たす外部実装として差替え可能であり、Runtimeは直前結果と過去のHDS-IR履歴をCompilerへ帰還できる。HDS Compilerが接続されていない場合は、決定論的 `自然言語器` をLegacy互換経路として利用する。

詳細は [`設計/07_HDS_IR入力契約.md`](設計/07_HDS_IR入力契約.md) を参照する。

## Layer-0 v4 Functional Core

現行Layer-0は5責任で扱う。

1. 言語アドレス化
2. 文脈束縛状態
3. 変換・合成中核
4. 文脈依存結果形成
5. 結果表面

```text
責任数 != 機構数
```

`主体主幹` は第6責任ではない。主に **文脈束縛状態 × 文脈依存結果形成** を担うMINIDORA固有機構である。

Layer-0の意味・適合状態・negative controlは外部正本を優先し、MINIDORA固有写像は [`設計/02_Layer0責任契約.md`](設計/02_Layer0責任契約.md) に閉じる。

## MINIDORA v0.3 実行構造

```text
HDS-IR / Legacy自然言語入口
  ↓
外部 Data R
  ↓
主体状態 S_t ─────────────┐
  ↓ 必須参照              │
Layer-0 × 日本語命令形 P  │
  ↓                        │
K3基盤由来の能力処理       │
  ↓                        │
候補 / 状態差分            │
  ↓                        │
主体整合 Gate              │
  ↓                        │
採否・結果形成             │
  ↓                        │
自然言語 Output            │
  ↓                        │
理由付き主体更新 / HDS帰還 ┘
```

純粋計算主体の旧表現 `C = L0 ⊗ P` は、v0.3でも下位実行核として維持する。Data / Knowledge は `R` として計算主体から分離する。

## HDS-IR公開境界

公開Runtimeが扱うHDS-IRは、次のRecordを持つ。

- `HDS座標` — 対象・状態・文脈・目的・作用・境界等の開放型座標
- `HDS関係` — 座標間の依存・入力・結果・同一性等の関係
- `HDS残差` — 未分別・意味損失・未知・競合等の未閉包情報
- `HDS意味作用` — 意味Projectionにおける変換・保持・損失・検証履歴
- `HDS実行核` — 現行Layer-0で実行可能になった局所閉包

`HDSIR.実行可能` が偽の場合、RuntimeはPを捏造せず保留し、IRを履歴へ残す。実行核が参照する入力座標についても、未確定・未観測・矛盾・留保、または座標欠落があれば実行へ昇格させない。

## 外部参照R

参照Dataは文字列Dataに加え、必要に応じて次の意味メタデータを保持できる。

- 意味キー
- 値
- 時点
- 範囲
- 条件
- 意味確定状態

同一対象・同一意味キー・同一時点・同一範囲・同一条件であることがData側で確定した場合だけ、値の競合を矛盾として扱う。意味同一性が未確定な文字列同士へRuntimeが勝手に意味を補わない。

詳細は [`設計/04_外部参照R仕様.md`](設計/04_外部参照R仕様.md) を参照する。

## 主体主幹

Llama 3の再構文化では、自己専用の永続stateそのものより、次の循環が自己一貫性候補として観測された。

```text
assistant住所
→ 過去assistant出力の再入力
→ 全履歴参照
→ 共通Dense経路
→ 逐次Residual
→ preference選択
→ 出力
→ 次turnへ帰還
```

MINIDORAではこの性質を明示状態へ外在化する。

主体状態は、主体ID・現在目的・判断基準・立場・選好・約束・仮説・未解残差・版を保持する。実差分は理由を必須とし、理由なし反転は保留する。理由付き自己訂正は許可し、旧版・新版・差分・理由・根拠を監査履歴へ残す。

詳細は [`設計/06_主体主幹仕様.md`](設計/06_主体主幹仕様.md) を参照する。

## プロトタイプ完成 — 2026-08-22

MINIDORAは2026-08-22、**非ニューラル／非Transformerの言語計算系として、問題・4候補・外部DataをすべてHDSへコンパイルし、K/Jを通して外部未知ベンチに正答を発生させる一連の経路が閉じた**ことをもって、プロトタイプ完成と判定した。

完成時の固定基準値は **GPQA Diamond 8 / 198 = 4.0404040%**。比較基準のKimi K3公開値は93.5%。この記録はK3級性能の達成を意味しない。重要なのは、MINIDORAの正規アーキテクチャから測定可能な非ゼロの一般問題解決能力が実際に発生したことである。

固定runでは、4候補 **792/792**、取得Data **875/875** をHDS Compilerへ通し、Dataを生文字列FactとしてKへ直入れしていない。取得DataからはHDS座標87,434、HDS関係140,450、K構造Fact 200,568を形成した。

この値は**プロトタイプ完成時点の不変baseline**として保持し、将来の改善値で上書きしない。

- 完成判定・評価条件・解釈境界: [`評価/PROTOTYPE_COMPLETION_2026-08-22.md`](評価/PROTOTYPE_COMPLETION_2026-08-22.md)
- 機械可読baseline: [`評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json`](評価/GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json)
- 評価ディレクトリの読み方: [`評価/README.md`](評価/README.md)

## リポジトリ構成

| Path | 役割 | 正本性 |
|---|---|---|
| `REFERENCES.md` | 外部参照正本・Layer-0優先順位 | 参照階層の正本 |
| `設計/` | Layer-0局所写像、P、R、主体、HDS-IR、Trinity、完成関門 | 現行MINIDORA設計正本 |
| `src/minidora/` | Runtime実装 | 実装 |
| `tests/` | 単体・negative control・回帰 | 検証 |
| `評価/` | 適合・性能・baseline・完成判定の実測 | 評価記録 |
| `構文化/` | K3 / Llama 3 / その他LLM / MINIDORAの観測・再構成成果 | 観測・再構成 |
| `docs/` | 個別実装・接続経路の補助説明 | 補助文書 |
| `artifacts/` | 固定取得物・接続検証成果・派生物 | 固定成果物 |
| `tools/` | inventory・整合性監査等の開発補助 | 開発・監査用 |

各ディレクトリの境界は、それぞれのREADMEを参照する。

### 推奨する読む順番

1. [`REFERENCES.md`](REFERENCES.md)
2. [`設計/README.md`](設計/README.md)
3. [`設計/02_Layer0責任契約.md`](設計/02_Layer0責任契約.md)
4. [`設計/07_HDS_IR入力契約.md`](設計/07_HDS_IR入力契約.md)
5. [`設計/06_主体主幹仕様.md`](設計/06_主体主幹仕様.md)
6. `src/minidora/runtime.py`
7. `tests/`
8. [`評価/README.md`](評価/README.md)
9. [`構文化/README.md`](構文化/README.md)

## 主要実装入口

- `src/minidora/layer0.py` — Layer-0 v4参照情報とMINIDORA命令実行器
- `src/minidora/hds_ir.py` — 公開HDS-IR Record契約
- `src/minidora/hds_adapter.py` — 外部HDS Compiler接続Protocol
- `src/minidora/runtime.py` — HDS-IR / Layer-0 / P / R / 主体主幹の統合
- `src/minidora/言語.py` — HDS Compiler未接続時のLegacy互換入口
- `src/minidora/主体.py` — 主体状態・理由付き更新・主体整合Gate
- `src/minidora/__main__.py` — 即時実行CLI / JSON採否出力

## 実行・試験・整合性監査

Python 3.11以上を使用する。

```bash
python -m pip install -e .
python tools/repository_consistency_check.py
python -m unittest discover -s tests -v
```

CIではLinux / Windows上のPython 3.11・3.12・3.13・3.14で、次を実行する。

- editable install
- リポジトリ正本整合性監査
- `src / tests / tools` の構文確認
- 全単体試験
- `python -m minidora` smoke test
- `minidora` console script smoke test

## 日本語基底

README、設計、構文化、評価、運用方針は日本語を基底言語とする。
API、規格名、コード識別子、固有名詞、原文確認が必要な箇所では正確性を優先して原語を保持する。

日本語は表示上の翻訳ではなく、上流構文化から実装まで意味境界を維持する正本言語として扱う。

## Git運用

- 正本ブランチは **`main` 一本**。
- 作業ブランチを常設しない。
- 構文化正本・評価結果・固定成果物を整理目的だけで削除しない。

## 公開境界

公開対象はMINIDORA実装、HDS-IR入出力契約、P / R / Layer-0局所写像 / 主体主幹の境界、検証結果、公開可能な構文化成果である。

**HDS Compilerの内部実装および上流HDSの内部解析方法そのものは公開対象外とする。**

## ライセンスと著作

MINIDORAの独自実装および本リポジトリで作成した独自文書は **Apache License 2.0** の下で公開する。
第三者由来資料・モデル関連成果物には各出典・原著作者の利用条件が優先する。

**Copyright 2026 がっちむち♂**
