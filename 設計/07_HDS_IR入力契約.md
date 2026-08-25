# HDS-IR入力契約 — 計算中間表現v1境界

## 1. 目的

HDS-IRをMINIDORAのLLM模型中核および計算中間表現と混同せず、意味Projection・運用入力・監査履歴の境界として扱う。

## 2. 現行位置

```text
外部入力
  ↓
公開HDS Compiler
  ↓
HDS semantic IR
  ├─ R / K / J / Mへ意味Projection
  └─ 閉包済み互換手順
          ↓ HDS計算降下
     計算中間表現 v1
          ↓
     計算実行境界 v1
```

別系統:

```text
対象言語状態
  ↓ 言語対応
MINIDORA模型核
  ↓
成立差
```

HDS-IR、模型核、計算中間表現は接続し得るが同一物ではない。

## 3. 非同一性

```text
HDS-IR != LLM模型中核
HDS-IR != 成立差
HDS-IR != 計算中間表現
日本語命令形P != 計算中間表現
HDS Compiler != 計算実行境界
HDS Compiler != LLM成立条件
```

## 4. HDS-IRが保持する情報

現行HDS-IRは少なくとも次を保持する。

- 原文 / 正規化文
- 入力言語 / 出力言語
- HDS座標
- HDS関係
- HDS残差
- HDS意味作用
- 由来・暫定性・再開放条件
- 運用用実行核
- 初期状態
- 参照要求
- v0.3由来の互換 `手順`

最後の `手順` は今後のsemantic IR正本責任ではない。現行Compiler互換の移行資産として扱う。

## 5. 計算中間表現への降下

実装: `src/minidora/HDS計算降下.py`

現行v1では次だけを読む。

- `HDSIR.実行可能`
- `HDSIR.手順`
- `HDSIR.認知世界ID`
- `HDSIR.実行核.入力座標`
- `HDSIR.実行核.出力座標`
- `HDSIR.実行核.境界`
- `HDSIR.実行核.検証`

原文を再解析しない。

```text
HDS-IR原文
  × 再解析しない

閉包済み構造
  ↓
HDS計算降下
  ↓
計算中間表現
```

意味座標名は計算作用へ自動解釈せず、由来参照として保持する。

## 6. 降下禁止

次の場合は計算中間表現へ昇格しない。

- 実行手順未閉包
- semantic_loss残差
- 実行入力座標欠落
- 実行入力が未確定
- 実行入力が未観測
- 実行入力が矛盾
- 実行入力が留保

未観測と不成立を混同しない。

## 7. 日本語命令形Pとの関係

現行互換経路は次である。

```text
HDS-IR.手順
  ↓
日本語命令形P
  ↓ 命令計算降下
計算中間表現
  ↓
計算実行境界
```

Pは人間可読の運用命令、計算中間表現は実行専用表現である。

`$a`のようなP側の文字列参照規約は、降下時に `状態値("a")` へ型付けされる。計算実行境界は `$` を解釈しない。

## 8. Rとの接続

RはHDS座標等から検索要求を形成できる。

取得Dataは外部Dataであり、計算中間表現へ無言投入しない。意味解釈が必要なDataはHDS semantic IRまたは模型核側の言語状態へ戻す。

## 9. 模型核との接続

HDS意味Projectionから模型核へ渡すものと、計算実行器へ渡すものを分ける。

```text
HDS semantic IR
  ├─ 言語状態 / 文脈 / 候補条件 → 模型核
  └─ 閉包済み計算作用            → 計算中間表現
```

同じHDS-IRを使っていても、消費者ごとにProjectionを分離する。

## 10. 次段HDS Compiler再設計

Compute IR / ABI v1確定後、公開HDS Compilerを次へ分割する。

```text
自然言語
 ↓
semantic frontend
 ↓
意味HDS-IR
 ↓
compute lowering backend
 ↓
計算中間表現
```

目標:

- semantic frontendは意味・関係・残差・由来を保持する。
- compute lowering backendは実行可能性が閉じた場合だけ計算中間表現を形成する。
- `HDSIR.手順`をsemantic IRの恒久フィールドとして要求しない。
- HDS本体の非公開理論を公開Compilerへ無断転記しない。

## 11. 受入条件

- HDS-IRをLLM模型中核と呼ばない。
- HDS-IRを計算中間表現と呼ばない。
- HDS未閉包時は計算降下しない。
- 計算降下で自然言語を再解析しない。
- 旧Layer0実行責任を計算実行器へ限定する。
- 日本語を内部規定言語とする。
- HDS Compiler再設計前にcompute責任をsemantic frontendへ再混入させない。
