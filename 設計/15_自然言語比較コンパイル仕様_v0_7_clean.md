# 自然言語比較コンパイル仕様 v0.7-clean

## 1. 目的

v0.3正本の英日意味コンパイルを維持したまま、記号比較だけでなく英語の明示的な自然言語比較を日本語正本のHDS関係へ落とす。

```text
A is greater than B
→ A --比較.大→ B
```

世界知識や比較結果を推測する処理ではない。入力に明示された比較構造だけを保持する。

## 2. 対象

- greater / higher / larger than → `比較.大`
- less / lower / smaller than → `比較.小`
- at least → `比較.以上`
- at most → `比較.以下`
- equal / equivalent to / equals → `等価`
- different / unequal → `不同`

## 3. 質問

`Which quantity is greater than threshold X?` は、

```text
未知始点 = quantity
関係 = 比較.大
既知終点 = threshold X
検索述語 = greater than
```

へ落とす。

`What does Expression A equal?` は、

```text
既知始点 = Expression A
関係 = 等価
未知終点 = 未特定
検索述語 = equal to
```

へ落とす。

## 4. R境界

HDS内部の関係名は日本語正本とし、外部検索時だけ `検索述語` の英語表層を使う。
候補問題では未知端点へ候補を代入し、関係方向を保ったqueryを生成する。

## 5. 禁止

- 世界知識から大小・同値を補う
- `greater` という語があるだけで比較関係にする
- 任意形容詞の比較軸を推測する
- GPQA固有語・gold・問題番号を使う
- v0.4以後の退行したscope系変更を混入する

## 6. 比較基準

mainのv0.3実測を基準とする。

- correct: 26 / 198
- accuracy: 13.13%
- answered: 117
- answered accuracy: 22.22%
- SUSPEND: 81
- documents retrieved: 2688

通常CIを全通過し、GPQA Diamond 198問で明確な退行がないことを採用条件とする。
