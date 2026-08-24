# 明示AND関係展開仕様 v0.9-clean

## 1. 目的

Compilerが `A and B` を一つの関係端点として圧縮してしまう情報損失を、限定された明示ANDだけ解消する。

```text
Protein A and Protein B inhibit Enzyme X
```

を、

```text
Protein A --阻害→ Enzyme X
Protein B --阻害→ Enzyme X
```

へ落とす。

## 2. 対象

確定済みの英語関係で、始点または終点が次の高確度形を満たす場合だけ展開する。

- 単語同士: `A and B`
- 共通head: `Protein A and Protein B`

両端がANDなら直積へ展開する。

## 3. 禁止

- ORを両方真として展開しない
- 未知端点を展開しない
- 3項以上や長大なcoordinationを無理に展開しない
- 非対称な複雑句を分割しない
- 世界知識でANDの意味を補わない
- benchmark固有分岐を作らない

## 4. 既存関係

高確度AND展開に成功した関係は、元の一体化した関係を残さず個別辺へ置換する。これにより同一証拠の二重加点を避ける。

## 5. 採用基準

v0.3 mainのGPQA 26/198・回答時22.22%を比較基準とする。
通常CI全通過とGPQA Diamond 198問で明確な退行がないことを要求する。
