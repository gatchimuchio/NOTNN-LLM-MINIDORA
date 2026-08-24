# Scope対応R復号仕様 v0.6

## 1. 目的

HDS Compiler内部で意味scopeを保持しても、R検索queryへ戻す時にscopeを落とせば、外部Dataへの到達経路で再び意味損失が起きる。

v0.6は、日本語正本の関係scopeと原英語表層を分離保持し、**R境界でだけ検索可能な英語へ復号する**。

```text
外部英語
  ↓
日本語意味正本
  ├─ 関係 = 阻害
  ├─ 極性 = 否定
  └─ 様相 = 可能
  ↓
HDS内部処理
  ↓
R境界
  ↓
could not inhibit
```

## 2. 正本と復号表層の分離

意味正本:

```text
極性=否定
様相=可能
```

復号補助:

```text
極性表層=not
様相表層=could
```

復号補助表層は、scopeの意味同一性を決める正本ではない。
`may` と `could` がともに `様相=可能` へ落ちる場合、内部意味は日本語正本で扱い、R検索時だけ入力表層を再利用する。

## 3. 否定質問

```text
Which molecule does not inhibit enzyme X?
```

内部:

```text
関係=阻害
極性=否定
不足位置=始点
既知終点=enzyme X
極性表層=does not
```

候補AのR query:

```text
Compound A does not inhibit enzyme X
```

`Compound A inhibit enzyme X` へ無言で肯定化してはならない。

## 4. 様相質問

```text
Which of the following could inhibit enzyme X?
```

内部:

```text
関係=阻害
極性=肯定
様相=可能
様相表層=could
```

R query:

```text
Compound A could inhibit enzyme X
```

## 5. 様相否定

```text
Which molecule could not inhibit enzyme X?
```

内部:

```text
関係=阻害
極性=否定
様相=可能
極性表層=not
様相表層=could
```

R query:

```text
Compound A could not inhibit enzyme X
```

## 6. 選択反転との境界

```text
Which molecule is least likely to inhibit enzyme X?
```

`least likely` はJの候補選択反転であり、関係 `阻害` 自体の否定ではない。

従ってR queryを

```text
Compound A not inhibit enzyme X
```

へ変えてはならない。関係検索は肯定形を維持する。

```text
Compound A inhibit enzyme X
```

取得後にJが選択意図を適用する。

## 7. 条件・比較・量化

predicate外に置く方が自然な表層は、関係条件から検索文脈へ追加する。

- `条件表層`
- `比較表層`
- `量化表層`

ただし内部意味正本と検索表層を混同しない。

## 8. 不変条件

- 日本語意味正本をR都合で変更しない
- 外部英語表層を内部意味正本へ戻さない
- 明示否定を肯定queryへ落とさない
- modalを検索時に落とさない
- `least likely` を関係否定へ変換しない
- 世界知識をquery rendererへ埋め込まない
- benchmark固有分岐を作らない

## 9. 受入条件

- `does not inhibit` を否定queryへ復号できる
- `could inhibit` をmodal付きqueryへ復号できる
- `could not inhibit` の語順を復号できる
- `least likely` は肯定関係queryのまま
- scope正本条件とscope復号表層を同じrelationへ併存できる
- 既存R検索・候補対称性を壊さない
- 通常CIを全通過する

## 10. 次段

- 自然言語比較を関係としてコンパイルする
- 条件節と主節の局所scopeを改善する
- 共参照を意味端点へ解決する
- scope-aware multi-hop graphを設計する

改善は検索量ではなく、**意味に一致したDataへ到達する効率**で評価する。
