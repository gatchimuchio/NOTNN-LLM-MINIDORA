# 明示分類コンパイル仕様 v0.10-clean

## 1. 目的

英語の明示分類を単なる語集合へ潰さず、日本語正本のHDS関係として保持する。

```text
Water is a compound
→ Water --分類→ compound
```

世界知識からWaterの分類を推測するのではなく、入力文に書かれた分類構造だけを抽出する。

## 2. 対象

- `A is a/an B`
- `A is a/an type of B`
- `A is a/an kind of B`
- `A is a/an form of B`
- `A is a/an class of B`
- `A is a/an example of B`

質問では、

```text
Which molecule is a compound?
```

を、

```text
未知始点 = molecule
関係 = 分類
分類先 = compound
検索述語 = is a
```

へ落とす。

## 3. R境界

内部関係は `分類` を正本とし、外部検索時だけ `is a` / `is a type of` を検索述語として使用する。
候補問題では未知始点へ候補を代入して検索する。

## 4. 安全境界

次は分類へ昇格しない。

- `A is not a B`
- `A is an inhibitor of B` のような前置詞付き役割・関係句
- 複雑な前置詞句
- 世界知識による暗黙分類
- benchmark固有分岐

単純分類先に `of / in / on / for / with / by / to` 等を含む場合は保守的に除外する。

## 5. 採用基準

v0.3 mainのGPQA実測を基準とする。

- correct: 26 / 198
- answered accuracy: 22.22%
- SUSPEND: 81

通常CI全通過とGPQA Diamond 198問で明確な退行がないことを要求する。
