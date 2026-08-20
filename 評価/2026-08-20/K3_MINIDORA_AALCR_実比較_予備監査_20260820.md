# K3 vs MINIDORA 実比較 — AA-LCR 予備監査

## 比較対象
- ベンチマーク: Artificial Analysis Long Context Reasoning (AA-LCR)
- K3: 公開された official MXFP4 実機再現（100問 × 3反復）
- MINIDORA: HDSコンパイラ → 固定R → MINIDORA のブラインド予備試験
- HDS/MINIDORA内部成果は外部送信・公開していない

## K3 実機再現
- 100問 × 3 = 300試行
- Frozen official Kimi-K3 judge: 254/300 = 84.67%
- GPT-5.6 Sol judge: 249/300 = 83.00%
- prompt tokens median: 95,119.5
- request elapsed median: 531.264 s
- mean: 580.854 s
- p95: 1,102.629 s
- serving: TP16 / DCP16, max context 1,048,576

## MINIDORA ブラインド予備試験
- 文書セット: co_dc_press_a
- 設問を見る前に6文書からRを固定
- R: 85 facts
- R SHA-256: 735814b2894c0686d877c60fab0653e980798667b2864ae95d78fe2ff5f81416
- その後に設問Q19と金答案を開示
- Q19要求: Equinix 2024 xScale capital expenditure guidance の上下限変化
- 金答案: -76%, -42%
- 固定Rに xScale CapEx guidance が存在せず、正答不能
- 正式ブラインド判定: 0/1

## 追加で発見したRuntime問題
現行の固定参照供給器は単語包含の線形検索であり、Q19に対して無関係な
revenue_growth_normalized_constant_currency や stockholders_equity 等もヒットした。
参照必須要求は「参照件数 > 0」だけで合格になるため、無関係参照でも合格判定し得る。
これはAA-LCR級比較では採否条件として不十分。

## 判定
- 現時点で「K3同等精度」は実測では支持されない。
- ただし今回落ちた主因は Layer-0算術能力ではなく、
  1. HDSコンパイルの意味被覆不足
  2. R検索の意味適合度判定不足
  3. Runtime採否が参照の存在だけを見ていること
  である。
- したがって次に比較すべき対象は、Layer-0の速度ではなく
  「全入力をHDS意味構造へ漏れなくコンパイルできるか」と
  「意味適合したRだけを根拠として採用できるか」。

## 参考: 既取得のMINIDORA局所効率
これはAA-LCRと同一タスクではないため精度比較には使わない。
- 50,000件 indexed R: p50 約4.13 µs
- known 10,000/10,000
- unknown 2,000/2,000 suspend
- GPU不使用
