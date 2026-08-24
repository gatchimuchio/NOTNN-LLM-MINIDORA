# 英語補助語端点正規化仕様 v0.12-clean

## 1. 目的

明示関係の抽出時に英語の時制・相を担う補助語が実体端点へ吸収される意味損失を防ぐ。

```text
Protein A is generating B
```

を、

```text
誤: Protein A is --生成→ B
正: Protein A --生成→ B
    相=進行
    時制=現在
```

へ正規化する。

## 2. 対象

- `is/are/was/were + V-ing` → 進行
- `has/have/had + 過去分詞` → 完了
- `has/have/had been + V-ing` → 完了進行
- `do/does/did + base verb` → 強調

補助語は実体名から分離し、関係条件へ保持する。

## 3. be + 過去分詞

`A is associated with B` のような表現をactive規則が `A is` 始点として誤抽出した場合、その偽関係は捨てる。
専用の明示構文で正しく抽出された `A --相関→ B` 等を残す。

同様に、受動態専用規則で意味方向が確定している関係は変更しない。

## 4. 非責任

- can/could/may/might/must/would等のmodalをactualへ変換しない
- `does not` 等の否定を肯定関係へ変換しない
- 世界知識を追加しない
- benchmark固有分岐を作らない

modal・否定は別の意味scope問題として扱い、本仕様では端点修正のために勝手に消費しない。

## 5. 採用基準

v0.3 mainのGPQA 26/198・回答時正答率22.22%を基準とする。
通常CI全通過とGPQA Diamond 198問で明確な退行がないことを要求する。
