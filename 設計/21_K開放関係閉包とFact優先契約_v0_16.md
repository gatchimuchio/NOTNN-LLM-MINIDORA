# K開放関係閉包とFact優先契約 v0.16

## 1. 目的

v0.15でHDS Compiler→Runtimeの責務別射影を確立した。

v0.16は、そのK入力を増やすのではなく、**既に渡された構造をKが候補比較で最後まで使い切る**ことを目的とする。

対象は次の二点だけである。

1. 開放関係質問を候補ごとの有向比較構造へ閉じる。
2. 同一source内ではatomic Factをdocument集約より優先する。

世界知識、検索query、検索量、Compiler語彙は変更しない。

## 2. 開放関係の候補閉包

例:

```text
What does Alpha use?
```

v0.15のK質問射影は、

```text
既知始点 = Alpha
関係 = 使用
未知終点 = object
```

を保持する。

候補が

```text
A = engine
B = stone
```

なら、Kの候補比較には次を渡す。

```text
A: Alpha --使用→ engine
B: Alpha --使用→ stone
```

これは世界事実の採用ではない。

`HDS候補代入仮説` として、**問いと候補を比較するための期待構造**を作るだけである。

### 2.1 実体候補だけを閉包する

候補が実体句なら未知端点へ代入する。

候補自身が命題、否定、条件、様相等を持つ場合は、文字列ごと未知端点へ代入しない。v0.15の `HDSK候補代入可能` 境界をそのまま使用する。

### 2.2 baselineとdirect verifierを同じ候補構造へ統一する

従来、候補代入仮説は主にdirect verifierで使われ、通常K比較は未閉包の候補意味を使っていた。

v0.16では、

```text
verification_candidate_irs
```

を通常 `HDSIRネイティブAdapter` にも渡す。

これにより、baseline照合とdirect verifierが同じ有向候補構造を消費する。

## 3. 同一source内のFact優先

Kは一つのR文書から、

- atomic Fact
- document集約

の両方を作る。

同一source・同一候補で両方が支持を返す場合、document集約は複数Factのbagであり、atomic Factより意味粒度が粗い。

したがって同一source内の優先順位を、

```text
direct > atomic fact > document
```

とする。

同じ粒度同士でのみ得点を比較する。

禁止:

```text
atomic fact score = 3
same-source document bag score = 9
↓
document bagを採用
```

v0.16:

```text
atomic factを採用
```

異なるsource間の比較・加点は従来通りである。

## 4. なぜData Projectionで削らないか

Data文書は複数の事実を含む。

問いを知らないData Projection段階で、

```text
安全な関係が一つある
→ 他の意味語を全部捨てる
```

とはしない。

どの構造が問いに必要かはK比較時に初めて決まるためである。

したがってv0.16は、

- Compiler出力を削らない
- R取得Dataを削らない
- K Data射影を追加圧縮しない
- K比較時の候補閉包とsource内調停だけを変更する

## 5. 不変条件

1. v0.15のR/K/J/M責務分離を維持する。
2. 完全HDS-IRを破壊しない。
3. 世界知識を追加しない。
4. 検索query・検索予算を変更しない。
5. benchmark固有分岐を追加しない。
6. 実体候補だけを開放関係へ代入する。
7. 命題候補は自身の意味構造を維持する。
8. 逆向き関係を正向き一致として扱わない。
9. 同一sourceをFactとdocumentで二重加点しない。
10. 同一sourceでは direct > atomic fact > document の意味粒度を優先する。
11. 異なるsourceの独立性は維持する。

## 6. 検証

機械回帰では最低限次を確認する。

- 開放関係の未知始点/未知終点を候補で閉じる。
- 通常K比較が候補閉包後の方向を使う。
- 逆向きFactと正向きFactを分別する。
- 同一sourceで高得点documentが低得点atomic Factを上書きしない。
- directはatomic Factより優先する。
- 同じ粒度のFact同士では高得点を採用する。
- 既存source横断調停・独立source加点を維持する。

採否順序は、構造整合 → 単体回帰 → Windows/Ubuntu CI → 最後に外部benchmark受入確認とする。
