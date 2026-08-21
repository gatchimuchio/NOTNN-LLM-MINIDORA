# ミニドラ（MINIDORA）

**NOTNN-LLM-MINIDORA** は、巨大ニューラルネットワークや Transformer を実行基盤とせず、LLM的機能を通常計算機上の分離構造として実装する非ニューラルネットワークLLMの研究・実装リポジトリです。

- 基底言語: **日本語**
- 正本ブランチ: **`main`**
- 現行実装候補: **MINIDORA v0.3**
- Layer-0: **v4.0-provisional**
- ライセンス: **Apache License 2.0**
- 著作: **がっちむち♂**
- 実装言語: Python 3.11+

## 現在の設計軸

MINIDORA v0.3は次の非対称構造を採る。

```text
K3                  = 主基盤
Llama 3             = 自己一貫性の対抗基準
その他LLM           = K3/Llama3差分の補助観測点
Layer-0 v4          = 実装非依存の機能責任契約
HDS / 日本語構文化  = 上流の分別・再射影手段
```

目標は **K3をベースに、Llama 3で観測した自己一貫性を主体主幹として内包したMINIDORA** である。

## 通常利用入口 — HDS意味コンパイル

利用者が日本語命令Pを事前に組み立てることを前提にしない。
通常入口は自然言語文字列であり、入力を直接Pへパターン変換するのではなく、HDSによって意味をHDS-IRへ射影し、局所的に実行可能になった閉包だけをLayer-0実行Pへloweringする。

```text
自然言語入力 / 外部Data
  ↓
HDSコンパイラ
  ↓
HDS-IR
  ├─ 座標
  ├─ 関係
  ├─ 暫定性
  ├─ 由来
  ├─ 残差
  └─ 意味作用履歴
  ↓
局所閉包
  ↓
Layer-0 × 日本語命令形 P
  ↓
主体整合Gate / 採否
  ↓
結果表面化
  ↓
自然言語出力
```

HDS-IRはHDS Nativeそのものではなく有限Projectionである。九座標を最終スキーマへ固定せず、未分別・表現不能・競合を削除せずResidualとして保持する。

`足す`、`和`等の表層語を別命令として実装しない。語義DataをHDS意味へ射影し、同じ`加算`作用へ閉包する。Pは「どう処理するか」、Dataは「何を意味し、何について処理するか」として分離する。

最小例:

```python
from minidora import ミニドラ

body = ミニドラ()
print(body.応答("2と3の和は？"))
# 5です。

ir = body.コンパイル("2足す3は？")
assert ir.実行核.作用 == "加算"
```

構造化結果が必要な場合も、`手順` を明示せず自然言語要求をそのまま実行できる。

```python
from minidora import ミニドラ, 要求

result = ミニドラ().実行(要求("2+2は？"))
assert result.値 == 4
assert result.HDS_IR is not None
```

現行HDSコンパイラは決定論的に、明示数式・比較、日本語算術の同義表現、文字数計数、外部参照をHDS-IRへ射影する。意味が局所閉包できない入力はPを捏造せず保留する。

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

Layer-0正本は `gatchimuchio/LLM-Layer-0-Functional-Compliance-Specification` を参照する。

## MINIDORA v0.3 実行構造

```text
自然言語 Input / 外部 Data
  ↓
HDS Compiler
  ↓
HDS-IR ────────────────┐
  ↓ 局所閉包            │
参照層 R / 主体状態 S_t │
  ↓                     │
Layer-0 × 日本語命令形 P│
  ↓                     │
K3基盤由来の能力処理     │
  ↓                     │
候補 / 状態差分          │
  ↓                     │
主体整合 Gate            │
  ↓                     │
採否・結果形成           │
  ↓                     │
自然言語 Output          │
  ↓                     │
監査・残差・由来帰還 ────┘
```

純粋計算主体の旧表現 `C = L0 ⊗ P` は、v0.3でも下位実行核として維持する。Data / Knowledge は `R` として計算主体から分離する。

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

主体状態は次を保持する。

- 主体ID
- 現在目的
- 判断基準
- 立場
- 選好
- 約束
- 仮説
- 未解残差
- 版

実差分は理由を必須とし、理由なし反転は保留する。理由付き自己訂正は許可し、旧版・新版・差分・理由・根拠を監査履歴へ残す。

## 構成要素

- **HDSコンパイラ**: 自然言語・外部DataをHDS意味空間へ射影し、HDS-IRを生成する
- **HDS-IR**: 座標・関係・暫定性・由来・残差・意味作用履歴を保持する実行前意味表現
- **Layer-0**: v4の5機能責任に適合する実装非依存核
- **P**: HDS-IRの局所閉包からloweringされる実行可能な日本語命令形
- **R**: Data / Knowledge を供給し、HDS意味空間へ統合される交換可能な外部参照層
- **主体主幹**: turnを跨ぐ主体状態と主体整合Gate
- **Runtime**: HDS-IR・P・R・Layer-0・主体主幹を接続し、結果と採否を返す

## リポジトリ構成

```text
src/minidora/                  MINIDORA実装
設計/                           Layer-0 / P / R / HDS-IR / 主体主幹 / 完成判定仕様
構文化/MINIDORA_v0.2/          旧公開再構成成果（Legacy）
構文化/MINIDORA_v0.3/          現行公開再構成成果
構文化/K3_HDS日本語構文_v2/    K3 full-weight基盤成果
構文化/Llama3_自己一貫性_HDS再構文化_v2/  Llama3自己一貫性差分成果
構文化/LLM横断_HDS日本語構文化_相対化ベンチマーク_v0_1/  補助差分観測
評価/                           適合・性能・回帰記録
tests/                          単体・negative control試験
```

主要入口:

- `src/minidora/hds_compiler.py` — 自然言語 / 外部Data → HDS-IR → P lowering
- `src/minidora/hds_ir.py` — HDS意味IRのRecord定義
- `src/minidora/言語.py` — Legacy互換API。意味処理はHDSコンパイラへ委譲
- `src/minidora/runtime.py` — HDS-IR / Layer-0 / P / R / 主体主幹の統合
- `src/minidora/主体.py` — 主体状態・理由付き更新・主体整合Gate
- `設計/07_HDS_IRコンパイラ仕様.md`
- `設計/02_Layer0責任契約.md`
- `設計/06_主体主幹仕様.md`
- `設計/05_完成判定関門.md`
- `構文化/MINIDORA_v0.3/`

## 実行と試験

Python 3.11以上を使用する。

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 日本語基底

README、設計、構文化、評価、運用方針は日本語を基底言語とする。
API、規格名、コード識別子、固有名詞、原文確認が必要な箇所では正確性を優先して原語を保持する。

日本語は表示上の翻訳ではなく、上流構文化から実装まで意味境界を維持する正本言語として扱う。

## Git運用

- 正本ブランチは **`main` 一本**。
- 作業ブランチを常設しない。
- 構文化正本・評価結果・固定成果物を整理目的だけで削除しない。

## 公開境界

MINIDORA実装、HDS-IR、P / R / Layer-0 / 主体主幹の境界、検証結果、公開可能な構文化成果を扱う。
上流HDSの内部解析方法そのものは公開対象外とする。

## ライセンスと著作

MINIDORAの独自実装および本リポジトリで作成した独自文書は **Apache License 2.0** の下で公開する。
第三者由来資料・モデル関連成果物には各出典・原著作者の利用条件が優先する。

**Copyright 2026 がっちむち♂**

- Llama 3 自己一貫性 HDS再構文化 v2（repo固定パッケージ）
