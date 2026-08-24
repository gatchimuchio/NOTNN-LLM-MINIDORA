# 明示関係節照応コンパイル仕様 v0.8-clean

## 1. 目的

英語関係節で関係代名詞が意味端点として残る損失を防ぐ。

```text
Protein A, which inhibits Protein B, ...
```

を、

```text
Protein A --阻害→ Protein B
```

へ落とす。`which --阻害→ Protein B` とはしない。

## 2. 対象範囲

v0.8-cleanでは、非制限関係節のうち局所文法上先行詞が明示される次の形だけを扱う。

- `NP, which VERB X, ...`
- `NP, who VERB X, ...`
- `NP, which is VERBed by X, ...`

## 3. 非責任

次は扱わない。

- `it / this / that / they` の自由照応
- 文脈を跨ぐ代名詞解決
- カンマなしの制限関係節
- 最近傍名詞を先行詞だと推測する処理
- 世界知識による先行詞選択

曖昧な照応を誤って解決するより、未解決のまま保持する。

## 4. 変換

Compilerが先に生成した `which` / `who` を端点とする偽関係があれば除去し、共有言語基底Pが認識した先行詞で関係を再構成する。

受動態は英語語順ではなく意味方向へ正規化する。

```text
Protein A, which is inhibited by Compound X, ...
→ Compound X --阻害→ Protein A
```

## 5. 境界

- v0.3 mainから独立追加する
- 退行したscope系変更を含めない
- benchmark固有分岐なし
- gold非参照

## 6. 採用基準

v0.3実測 26/198・回答時正答率22.22%を基準とする。
通常CI全通過とGPQA Diamond 198問で明確な退行がないことを要求する。
