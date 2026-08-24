# HDS Compiler Runtime射影契約 v0.15

## 1. 目的

HDS Compilerは、自然言語から得た情報を一つの平坦な語集合としてミニドラへ渡す装置ではない。

Compilerは入力に含まれる意味を可能な限り保持した完全HDS-IRを作り、Runtimeはその完全IRから各責務が実際に消費できる最小十分なProjectionだけを渡す。

```text
自然言語
  ↓
HDS Compiler
  ↓
完全HDS-IR
  ├─ R核: 検索表層 / 検索述語 / 既知端点 / 条件 / 候補
  ├─ K核: 主題語 / 関係種別 / 有向端点 / 候補意味 / Data事実
  ├─ J核: 選択意図 / 値状態 / 残差 / 境界
  └─ M核: 完全IR / 由来 / 履歴 / 再開放情報
```

完全IRを削るのではない。**消費者ごとに見せる範囲を限定する。**

---

## 2. 最上位原則

### 2.1 Compilerが解釈し、Runtimeは射影する

自然言語の構文、語形、否定、様相、条件、関係方向、未知端点の解釈はCompiler責務である。

Runtime Projectionは自然言語を再解析しない。

禁止:

```text
Runtime
  ↓
英文regex再解析
  ↓
極性・様相・条件を推測
```

正:

```text
Compiler
  ↓
阻害(A→B)
極性=否定
様相=可能
条件scope=...
  ↓
Runtime Projection
  ↓
各消費者が表現可能な部分だけ選択
```

### 2.2 情報保持と利用可能性を分離する

完全IRには情報を保持する。

しかし、下流が正しく表現できない意味を「近い意味」に潰して渡してはならない。

```text
保持できる
≠
KへFactとして投入してよい
```

### 2.3 benchmarkは設計勾配にしない

開発順序は以下とする。

1. ミニドラの実消費構造を確認
2. Compiler出力契約を逆算
3. Runtime責務境界を固定
4. 単体・統合回帰
5. Windows / Ubuntu CI
6. 最後に外部benchmarkを受入確認として一度だけ実行

benchmark結果から局所的な語彙・規則を追加する探索は行わない。

---

## 3. Compilerの完全IR

Compilerは入力から以下を可能な限り保持する。

- 対象・実体
- 関係種別
- 関係方向
- 状態・属性・値
- 未知端点
- 否定
- 様相
- 条件・前提
- 選択意図
- 検索用外部表層
- 残差
- 値状態
- provenance
- 文脈・履歴接続
- 再開放条件

重要なのは、これらを同じFactとして平坦化しないことである。

---

## 4. relation scopeのCompiler分離

### 4.1 助動・否定を実体端点へ吸収しない

誤:

```text
A may --阻害→ B
A does not --阻害→ B
```

正:

```text
A --阻害→ B
様相=可能
```

```text
A --阻害→ B
極性=否定
```

`may`や`does not`は実体名の一部ではない。

基礎Compilerの関係抽出が端点へ吸収した助動・否定は、`HDS英語関係scope射影`がCompiler内部で実体から分離し、relation条件へ移す。

### 4.2 条件scope

明示的に同一文へ結び付く条件だけをrelation条件へ保持する。

```text
If condition X, A inhibits B.
```

```text
A --阻害→ B
条件scope=If condition X
```

談話を跨ぐ曖昧な条件伝播は行わない。

### 4.3 scope層は新しい世界関係を作らない

scope層は既存のCompiler関係を正規化・注釈する。

世界知識や共起から新規関係を推測しない。

疑問文の意味構造は質問意味Compilerへ委ねる。

---

## 5. R質問射影

Rは「問題を理解する主体」ではない。Compilerが確定した検索要求を外部参照へ運ぶ境界である。

### 5.1 関係質問

Rへ渡すもの:

- choice集合
- 検索述語付き関係
- 既知端点
- 未知端点位置
- 外部検索に必要な条件・時間・範囲

例:

```text
Which molecule inhibits Enzyme X?
```

候補A:

```text
Compound A inhibit Enzyme X
```

Rは完全質問文を再解釈しない。

### 5.2 選択制御を検索へ混ぜない

`least likely`、`except`等はJの選択意図であり、世界事実の検索条件ではない。

したがってR Projectionから除外する。

### 5.3 一般質問

関係スロットが作れない場合はCompilerの`検索.*`を優先する。

`検索.*`が無い場合のみ対象・実体・状態・属性・値・条件へ縮退する。

### 5.4 fallback裏口を閉じる

R Projectionの`原文/正規化文`も検索核から再生成する。

検索器がfallback時に元の完全質問文を読み直して制御語を再混入させてはならない。

---

## 6. K質問射影

現行K3/HDS nativeが主に消費するのは以下である。

- 問いの意味語
- 候補意味語
- 候補固有語
- 関係種別
- 始点→終点
- 独立出典
- confidence / 値状態 / 残差阻害

したがってKへCompilerが抽出したもの全部を渡さない。

### 6.1 未知端点と関係種別を分離する

```text
Which molecule inhibits Enzyme X?
```

未知なのはmoleculeであり、`阻害`という問い作用素ではない。

K質問射影では、

```text
関係種別 = 阻害       既知
始点 = molecule       未観測
終点 = Enzyme X       既知
```

として保持する。

世界事実を確定するのではなく、問いが要求する演算子を確定するだけである。

### 6.2 非関係質問

KはR専用`検索.*`を借りない。

公開Compilerが持つ`対象.主題語`を問い照合核として使う。

```text
Which statement best describes cellular respiration?
```

K核:

```text
対象.主題語 = cellular
対象.主題語 = respiration
choice集合
```

---

## 7. K候補射影

候補は、

1. 実体候補
2. 命題候補

を分ける。

### 7.1 実体候補

```text
Compound A
```

は未知端点へ代入できる。

### 7.2 命題候補

```text
Compound A inhibits X
Compound A does not inhibit X
Under condition Y, Compound A inhibits X
```

は文字列全体を未知実体へ代入してはならない。

実体/命題判定は完全候補IRで行う。

その後、実体候補だけK射影済み表現を候補代入へ使う。

命題候補はK射影後に残った自身の関係を直接検証へ渡す。

baseline候補比較と直接関係検証は同じK射影契約を使い、直接検証だけraw候補IRへ戻る経路を作らない。

---

## 8. K Data射影

R取得DataからKへ渡してよいもの:

- 対象・実体
- 関係述語
- 属性・値
- Kが表現可能な状態
- Kが表現可能な有向関係
- 値状態
- 残差阻害
- provenance / source confidence

次はKの世界Factへ入れない。

- `検索.*`
- `制御.*`
- `目的.*`
- `監査.*`
- query route
- Kでrelationへ束縛できないscope座標

### 8.1 未対応scopeを肯定Factへ潰さない

現在のKが否定・様相・条件scopeを関係演算として表現できない場合、

```text
A does not inhibit B
```

を

```text
A --阻害→ B
```

として投入してはならない。

同様に、

```text
A may inhibit B
If X, A inhibits B
```

も無条件肯定辺へ変換しない。

Compilerがrelation条件として

```text
極性=否定
様相=可能
条件scope=...
```

を保持し、Runtime K射影はその構造だけを見て有向辺への昇格を止める。

対象語・実体語などKが正しく扱える意味核は残してよい。

---

## 9. query routeは証拠ではない

どのqueryで取得したかは世界事実ではない。

`query_kind / query_choice`はprovenance・監査へ保持してよいが、候補真偽の意味Factへ昇格させない。

Kが評価する対象は取得本文をCompilerした結果である。

---

## 10. J / M

JとMには圧縮IRを渡さない。

J:

- 選択意図
- 値状態
- 残差
- 境界
- 採否に必要な完全文脈

M:

- 完全HDS-IR
- provenance
- 履歴
- 未解残差
- 再開放情報

を保持する。

したがってR/Kの効率化で監査・履歴情報を不可逆に失わない。

---

## 11. 実行経路

```text
入力
 ↓
HDS Compiler
 ↓
完全HDS-IR
 ├────────────→ M 保存
 ├────────────→ J 判断文脈
 │
 ├→ HDSR質問射影
 │    ↓
 │    R query
 │    ↓
 │   外部Data
 │    ↓
 │   HDS Compiler
 │    ↓
 │   完全Data IR
 │    ↓
 │   HDSKData射影
 │    ↓
 │    K
 │
 └→ HDSK質問射影
      + HDSK候補射影
      ↓
      C/K候補比較
      ↓
      J最終採否
```

---

## 12. 不変条件

1. 完全HDS-IRを破壊しない。
2. 自然言語の意味解釈をRuntimeへ移さない。
3. Runtime Projectionは構造選択・loweringだけを行う。
4. Rへ選択制御・監査メタを検索対象として渡さない。
5. Kへ検索・制御・目的・監査メタを世界Factとして渡さない。
6. 未知端点と既知関係種別を同じ未観測状態へ潰さない。
7. Kで表現できない否定・様相・条件scopeを無条件肯定辺へ潰さない。
8. 片端しか残らない関係をKへ作らない。
9. query routeを世界証拠へ昇格させない。
10. J/Mは完全IRを保持する。
11. benchmark固有分岐を入れない。
12. 世界知識をCompilerへ追加しない。

---

## 13. 受入順序

1. Compiler / Runtime責務境界の静的監査
2. relation scope分離回帰
3. R/K/J/M射影回帰
4. 既存全単体試験
5. Windows / Ubuntu CI
6. 最後に外部benchmarkを受入確認として一度だけ実行

外部benchmarkの数字から局所規則を逆算しない。
