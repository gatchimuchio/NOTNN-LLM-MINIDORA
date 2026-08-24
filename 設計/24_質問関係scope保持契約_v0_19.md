# 質問関係scope保持契約 v0.19

## 1. 目的

v0.18でData側の関係修飾を `HDS修飾Fact` として損失なく保存できるようになった。

しかし質問側では、英日意味フレームが様相・条件・量化を認識していても、関係質問へは

```text
種別
未知位置
要求型
既知端点
検索述語
```

しか渡していなかった。

このため、

```text
Which compound may inhibit X?
```

と

```text
Which compound inhibits X?
```

が、関係質問IRでは同じ開放関係へ縮退していた。

v0.19では、**質問に明示された関係修飾を、質問全体のメタではなく開放関係そのものへ結び付ける**。

## 2. 対象

v0.19で質問relationへ保持する修飾は、v0.18のData修飾identityと同じ語彙に合わせる。

- `様相=可能`
- `様相=必要`
- `量化=全称`
- `量化=不定`
- `量化=全否定`
- `条件scope=<明示条件句>`

蓋然性 `most likely / least likely` はJの選択方向・比較意味と接続するため、v0.19のrelation qualifierへは入れない。

否定質問も既存J補集合制御を維持し、v0.19ではrelation polarityへ移さない。

## 3. 最終質問だけを対象とする

背景文の制御は質問relationへ伝染させない。

```text
Prior work may be incomplete.
Which molecule inhibits X?
```

なら、質問relationへ `様相=可能` を付けない。

既存の `_質問焦点` が最後の実質問だけを取り出し、その焦点内の制御からrelation qualifierを作る。

## 4. 先頭条件句

条件付き質問は、条件句を質問本体から分離してから関係構文を解析する。

```text
Under low pH, which compound may inhibit X?
```

を、

```text
質問本体:
Which compound may inhibit X?

関係:
未知始点 = compound
関係 = 阻害
既知終点 = X
様相 = 可能
条件scope = Under low pH
```

へ落とす。

対象は、局所的に境界が明示された先頭条件句だけとする。

- if
- when
- under
- given
- assuming
- unless
- in the presence of
- in the absence of

条件句と質問本体の境界が曖昧な場合は無理に分離しない。

## 5. 英日関係質問

`英日関係質問` に、

```python
修飾: tuple[tuple[str, str], ...]
```

を追加する。

これは日本語正本の意味identityであり、英語表層そのものではない。

例:

```python
(("様相", "可能"), ("条件scope", "Under low pH"))
```

条件scopeだけは条件内容そのものが意味境界なので、正規化した原表層を保持する。

## 6. HDS relationへの射影

英日意味Bridgeを `v0.4` へ更新し、関係質問の `修飾` を `HDS関係.条件` へ追加する。

```text
Which compound may inhibit X?
```

```text
関係種別 = 阻害
不足位置 = 始点
検索述語 = inhibit
様相 = 可能
英日意味射影 = v0.4
```

質問の未知端点は従来通り `未観測` のまま保持する。

## 7. R/K/Jへの影響

v0.19は意味保持までである。

- R: 既存検索構造を維持
- K: scope-aware回答をまだ追加しない
- J: 既存選択意図を維持
- M: 完全IRを保持

質問relationの修飾を保存しても、v0.19単体で採点規則は変えない。

## 8. 不変条件

1. 背景文の様相・条件を最終質問へ伝染させない。
2. 明示された質問scopeをrelationから落とさない。
3. `may/could/might/can/would` を `様相=可能` へ寄せる。
4. `must` を `様相=必要` へ寄せる。
5. 量化をrelation qualifierとして保持する。
6. 条件scopeは局所的に境界が明示された場合だけ保持する。
7. 受動態の意味方向を維持する。
8. `least likely` 等のJ選択方向とrelation様相を混同しない。
9. 世界知識を追加しない。
10. R queryや検索予算を変更しない。
11. benchmark固有分岐を追加しない。
12. scope-aware回答は次段へ分離する。

## 9. 次段

v0.20では初めて、

```text
質問relation qualifier
候補閉包relation
Data HDS修飾Fact
```

を同じidentity空間で照合する。

それまでは、v0.19で保持した質問scopeを採点へ使用しない。
