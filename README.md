# NOTNN-LLM-MINIDORA

## 非ニューラルLLM「ミニドラ」

このリポジトリは、Kimi K3をHDSで解析し、実装固有構造をLayer-0へ縮約し、日本語命令形Pと外部参照Data Rへ再構成することで、非ニューラルLLMを実装・検証するための正本である。

## 固定式

```text
K3
↓ HDS
暫定原理
↓ 水平引き算
Layer-0責任
↓ 日本語構文化
命令形P
↓
L0(P, Input, Reference)
↓
MINIDORA
```

```text
MINIDORA
= Layer-0
+ HDSで抽出・縮約した日本語実行命令P
+ 交換可能な外部参照Data R
+ HDS由来の採否境界
```

## 重要境界

- KDA / MoE / Attention / Transformer等は入力側の観測資料であり、Layer-0の正本語彙ではない。
- scalarを一個ずつ意味へ対応付けることを目的にしない。
- Capabilityは命令形Pへ、Knowledge/Dataは外部参照Rへ分離する。
- 外部参照RはRAG追加機能ではなく標準Data Layerである。
- 日本語は表示言語ではなく、HDS解析・原理化・Layer-0縮約・命令実行の基底言語である。
- HDS採否GateとHDS解析本体を混同しない。

## リポジトリ構成

```text
設計/
  00_設計思想正本.md
  01_HDS解析規約.md
  02_Layer0責任契約.md
  03_日本語命令形P仕様.md
  04_外部参照R仕様.md
  05_完成判定関門.md

解析/
  README.md
  観測台帳/
  原理候補/
  水平引き算/

src/minidora/
  layer0.py
  命令.py
  参照.py
  採否.py
  runtime.py

tests/
  test_layer0.py
  test_reference.py
  test_runtime.py

評価/
  README.md
```

## 実装順序

1. K3公開情報を観測台帳へ固定
2. HDSで原理質問・並列Model・反対Model・摂動・反実仮想を実行
3. 実装固有物を水平引き算
4. Layer-0責任へ縮約
5. 日本語命令形Pへ構文化
6. 外部参照Rと接続
7. Runtime実装
8. held-out / 摂動 / 反実仮想 / 同一harnessで評価

原理候補が閉じる前に実装を追加しない。

## 現在の状態

この再構築版では、以前のK3固有opcode中心実装を正本から外し、設計思想・解析規約・Layer-0契約・日本語命令P・外部参照Rを基準に再出発する。

K3同等性は未宣言。完成判定は`設計/05_完成判定関門.md`に従う。
