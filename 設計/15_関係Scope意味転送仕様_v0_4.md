# 関係Scope意味転送仕様 v0.4

## 1. 目的

HDS Compilerの責務は、入力に存在する意味を勝手に足さず、勝手に捨てず、MINIDORA/C・K・Jが扱えるHDS-IRへ変換することである。

v0.3までに英語の語形・関係・質問構造を日本語正本へ射影したが、**関係に掛かる極性・様相・条件がHDS→K境界で弱く、同じ関係へ潰れる経路**が残っていた。

v0.4では次を不変条件とする。

```text
A inhibits B
A does not inhibit B
A may inhibit B
If X, A inhibits B
```

これらを同一の無条件肯定関係として扱わない。

## 2. 処理順

```text
外部英語
  ↓
基礎HDS Compiler
  ↓
英語明示関係Projection
  - 語形
  - 受動態
  - 否定態
  - 様相態
  - 旧式偽陽性除去
  ↓
英日意味Projection
  - 日本語正本関係
  - 極性scope
  - 様相scope
  - 量化scope
  - 条件scope
  ↓
HDS-IR
  ↓
HDS→K Adapter
  - relation.conditionsをprovenanceへ保持
  - 否定関係を別predicateへ分離
  ↓
C / K / J
```

## 3. 極性

### 3.1 肯定

```text
Protein A inhibits Protein B.
```

```text
始点 = Protein A
関係 = 阻害
終点 = Protein B
極性 = 肯定
```

### 3.2 否定

```text
Protein A does not inhibit Protein B.
```

```text
始点 = Protein A
関係 = 阻害
終点 = Protein B
極性 = 否定
```

Kでは肯定 `阻害` と否定 `否定.阻害` を別predicateとして保持する。
肯定Dataで否定候補を直接証明してはならず、その逆も同様とする。

## 4. 受動態

```text
Protein A is not inhibited by Protein B.
```

は英語の表面順ではなく意味方向へ戻す。

```text
Protein B --否定.阻害→ Protein A
```

## 5. 様相

```text
Protein A may inhibit Protein B.
```

旧式抽出で `Protein A may` を主語にしてはならない。

```text
始点 = Protein A
関係 = 阻害
終点 = Protein B
様相 = 可能
```

`can / could / may / might / must / would` を関係端点から分離する。

## 6. 条件

単一の明示関係で条件scopeが一意な場合だけ、条件をその関係へ接続する。

```text
If condition X, Protein A inhibits Protein B.
```

```text
関係 = 阻害
条件種別 = 条件
条件表層 = If condition X
```

複数関係がありscopeが一意に決められない場合、条件を無理に全関係へ配らない。

## 7. HDS→K転送

relation.conditionsをK投入時に破棄しない。

```text
relation_condition:極性=否定
relation_condition:様相=可能
relation_condition:条件種別=条件
relation_condition:条件表層=...
```

をprovenanceへ保持する。

否定関係はgraph上でも肯定関係と同一predicateにしない。

## 8. 候補代入

問いの未知端点へ候補を代入するとき、`不足位置`だけでなく次も継承する。

- 検索述語
- 極性
- 様相
- 量化
- 条件
- その他の意味scope

候補代入によって問いの意味条件を落としてはならない。

## 9. 安全境界

- 世界知識を追加しない
- GPQA固有分岐を作らない
- 名詞共起から関係を捏造しない
- `least likely` の選択反転を関係否定へ変換しない
- 明示否定質問と反転選択問題を分ける
- 複数関係でscope不明な制御を無理に割り当てない
- 旧Compiler互換のために誤関係を残さない

## 10. 受入条件

- `A does not inhibit B` が否定阻害として一意に残る
- 旧式の `A does not` 主語を持つ肯定関係を除去する
- `A is not inhibited by B` の方向と極性を保持する
- `A may inhibit B` でmodalを主語へ混入させない
- 単一条件命題の条件を関係へscopeできる
- HDS→Kでrelation.conditionsを保持する
- K graphで肯定/否定関係を分離する
- 直接関係検証でも肯定/否定を混同しない
- 通常CIを通過する
- GPQA Diamond 198問でv0.3からの退行有無を測定する

## 11. 比較基準

v0.3のGPQA Diamond実測を基準とする。

```text
correct = 26 / 198
accuracy = 13.13%
answered = 117
answered accuracy = 22.22%
SUSPEND = 81
documents retrieved = 2688
```

R取得はrun間で変動するため、正解数だけでなく回答時正答率・SUSPEND・取得Data量・関係scopeの回帰試験を併記して採否する。
