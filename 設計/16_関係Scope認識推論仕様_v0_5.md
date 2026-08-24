# 関係Scope認識推論仕様 v0.5

## 1. 目的

v0.4は、HDS Compilerが抽出した関係scopeをHDS-IRからKまで消さずに運ぶ。
v0.5は、そのscopeをMINIDORA/Cの比較で実際に使用し、意味条件の異なる関係を同じ証拠として加点しない。

```text
v0.4 = scopeを運ぶ
v0.5 = scopeを読む
```

## 2. Scope正本

関係scopeは少なくとも次を保持する。

- 極性
- 様相
- 量化
- 比較
- 条件種別
- 条件表層
- 蓋然性

既定scopeは `極性=肯定` かつ他項目なしとする。

## 3. 直接構造一致

次は同じ関係として直接一致させない。

```text
A inhibits B
A may inhibit B
A does not inhibit B
If X, A inhibits B
If Y, A inhibits B
```

直接関係検証では、

```text
関係種別
+ 始点
+ 終点
+ Scope
```

が一致した場合だけ直接証拠とする。

`現実なら可能` 等の追加推論は、この一致層では行わない。

## 4. K実効関係

Kへ投入する関係predicateは、scope付き関係を無条件関係へ潰さない粗いラベルを持つ。

例:

```text
阻害
否定.阻害
様相:可能.阻害
条件:条件.阻害
```

条件表層は長大化と表記揺れを避けるためpredicate名へ直接埋め込まず、provenanceで厳密照合する。

## 5. 汎用Graph境界

現行汎用HDS意味Graphはscopeを状態として持たない。
従ってv0.5では、scope付き関係を無条件のmulti-hop辺へ降格させない。

```text
scopeなし関係 → 汎用Graph利用可
scope付き関係 → 直接scope照合へ限定
```

これは能力不足を隠すための推測ではなく、意味損失を防ぐ安全境界である。

scope-aware multi-hopは、別段階でgraph自体へscope状態を導入してから解放する。

## 6. 不変条件

- 肯定と否定を混同しない
- 可能と現実を無言で同一視しない
- 条件Xと条件Yを同一視しない
- 量化・比較・蓋然性を捨てない
- scope不明を勝手に補完しない
- 世界知識をCompiler/Kへ追加しない
- benchmark固有分岐を作らない

## 7. 受入条件

- HDS関係からscopeを機械取得できる
- K Fact provenanceから同じscopeを復元できる
- modal関係と無条件関係のscopeが不一致になる
- modal候補を無条件Dataで直接証明しない
- 同一modal scope Dataなら直接検証できる
- 条件X候補を条件Y Dataで直接証明しない
- scope付き関係をscope未対応汎用Graphへ入れない
- v0.4の極性・転送契約を維持する

## 8. 次段

v0.5以後は次を分離して行う。

1. scope-aware multi-hop graph
2. R検索queryへのscope保持
3. 自然言語比較・同値・属性関係の拡張
4. 複文の局所scope
5. 照応・共参照の解決精度

量を増やすのではなく、意味保持率と誤射影率で採否する。
