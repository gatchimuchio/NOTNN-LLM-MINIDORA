# 12 MINIDORA v0.5実測との接続

## 観測値

2026-08-28のGPQA Diamond 198問 controlled A/B:

- current: 20 / 198 = 10.10%
- controlled baseline: 22 / 198 = 11.11%
- current answered: 120
- baseline answered: 95
- checkpoint_count: 815
- checkpoint_reactivations: 0
- global_reconciliations: 0
- candidate_cross_updates: 0
- specialist_actions_invoked: 0

## 構文化側へ返された問い

旧v1は、公開LLM構造から「中間状態へ後段から再作用できる」ことを広く抽出していた。しかしMINIDORA実測は、**状態らしいものを記録しただけでは能力作用にならない**ことを露出した。

そこでv2ではLLM側の観測も再分解した。

- stateの存在
- stateを後段が読むこと
- state内容でweight/referenceが変わること
- state内容でpathが変わること
- stateを明示的に再参照すること
- stateが複数差と再結合すること

このうちどこまで必要かはまだ決めない。

## 現時点で言えること

MINIDORAの `checkpoint_count=815` は状態記録量を示すが、`reactivations=0` ならcheckpoint機構自身については後続再利用を観測できていない。

ただし能力核の他経路がstate依存計算を行っている可能性は別監査である。よって、checkpoint 0発火だけをGPQA低得点の単独原因と断定しない。

次の検証では、checkpoint/working stateを介入的に除去・固定し、出力・候補差・参照集合・作用回数が変化するかを計測する必要がある。
