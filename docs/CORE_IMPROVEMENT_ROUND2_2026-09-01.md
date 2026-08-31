# MINIDORA 汎用core改善2 — 2026-09-01

基準commit: `318f0a088218c558052e1fe1c010226c11422a1a`

## 目的

MINIDORAを「最小・最軽量・シンプルな非NN LLM核」として改善する。benchmark得点や専門領域の穴埋めではなく、一般作用の純度・軽量性・決定論・日本語意味保持だけを対象とした。

## 変更

### 厳密言語模型

- 文書群を全件tuple化せず1-passで形成する。
- 既存模型状態からDataを増分形成できる。
- 系列確率計算の履歴を `次数 - 1` に限定する。
- 単一記号確率では語彙全分布を毎回生成しない。
- `条件付き記号分布.確率_of()` の一時dict生成を廃止する。
- 最尤次記号の同率処理で語彙indexを候補ごとに探索しない。
- 復元時に負/0計数、語彙外遷移、過長文脈など壊れた模型状態を入口で拒否する。

形成結果・系列確率は従来と同じ厳密 `Fraction` 法則を維持する。

### 汎用計算ABI

- 比較は指定された演算子だけを評価する。
- 算術で `+=` / `*=` 等を使わず、入力可変値を破壊しない。

### 日本語基底言語構造

- 否定・条件のscopeを文境界と明示対比境界へ局所化する。
- 既存27個の日本語関係述語から否定活用を文法派生する。
- 世界知識・専門語彙・benchmark語彙は追加しない。

### Runtime

`runtime_v03` 継承を現行v0.5 Runtimeから外した。

既定Runtimeは次だけで成立する。

```text
厳密言語模型
+ 能力模型
+ 汎用計算器
+ 外部Data / R
+ 最小作業文脈
+ HDS安全弁
```

旧主体主幹、Trinity文脈系、K3 helperはactive defaultから外し、明示接続/明示API時だけ互換経路として利用する。

多turnで必要な `現在焦点 / 直前結果 / IR履歴 / 未解残差` は、AGI主体構造ではなくRuntimeの最小作業文脈として保持する。

### package import

root `minidora/__init__.py` のeager importを遅延attributeへ変更する。

`import minidora` だけではHTTP Provider、旧K3、旧Trinity、旧Runtimeなどを起動しない。既存公開名は要求された時に読み込む。

## サンドボックス検証

- 厳密LM形成 A/B: 5000 / 5000 完全一致
- 増分形成 vs 全量再形成: 3000 / 3000 完全一致
- 壊れた模型状態: 全拒否
- 単一記号確率経路: 合成模型で全分布経路比 約88倍高速
- 計算辞書同値比較: PASS
- mutable list算術入力非破壊: PASS
- 日本語既存述語: 27 / 27 肯定保持
- 日本語否定活用: 108 / 108 極性保持
- 日本語/英語否定scope: PASS
- plain package import: legacy submodule自動起動なし
- native v0.5 Runtime smoke: PASS

## 境界

追加していないもの:

- 専門solver
- GPQA固有規則
- gold / qid / case ID
- NN / Transformer
- HDS winner selection
- 新しい外部依存

この改善後もbenchmarkは観測手段であり、core設計の目的にはしない。
