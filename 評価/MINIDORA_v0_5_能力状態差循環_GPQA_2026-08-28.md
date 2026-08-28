# MINIDORA v0.5 能力状態差循環 GPQA実測 — 2026-08-28

## 1. 目的

構文化v3・構成定義v8・HDS Compiler Architecture v1.3 / Pipeline v1.4をMINIDORA能力模型核へ接続した後、状態差が実際の次作用選択へ到達するかをGPQA Diamond全198問で観測する。

本実測は厳密言語模型成立判定ではない。推論・知識能力の診断である。

## 2. 測定固定

- workflow run: `33136492914` / run #160
- repository commit: `8a1167ab7af9fcfd25323da99a906495212e0d29`
- dataset: GPQA Diamond 198問
- current: 日本語基底・状態差起動MINIDORA能力模型核 + HDS Compiler作用差分 + HDS判断主体
- controlled baseline: 同一質問IR・同一取得資料を使う旧v0.3 helper、作業再作用/局所再照合なし
- artifact: `minidora-gpqa-current-measurement`
- artifact id: `9672803018`
- artifact digest: `sha256:fc76e70b62b5f528b9ac9c290b6fbd796d58d66286dabd1b689edc975de00694`

## 3. 機構実測

```text
completed                 = 198
checkpoint_count          = 725
checkpoint_reactivations  = 134
global_reconciliations    = 134
candidate_cross_updates   = 21
specialist_actions_invoked = 0
```

理由記録:

```text
CAPABILITY_STATE_DELTA_V1 = 197
STATE_DELTA_REACTION      = 113
STATE_DELTA_CROSS_UPDATE  = 21
HDS_ACTION_DELTA_ATTACHED = 10
HDS_ACTION_DELTA_CONSUMED = 0
```

1問はHDS question semantic lossで能力経路へ入っていない。

### 再活性回数分布

artifact個票198件を再集計した。

```text
再活性0回 = 85問
再活性1回 = 92問
再活性2回 = 21問
```

候補横断更新21問は、すべて再活性2回の群に属した。

したがって今回の実装では、少なくとも次の対応が実測された。

```text
一次能力作用で状態差なし
→ 再活性0

一次能力作用で状態差あり
→ 再活性1

再作用によってさらに新しい候補状態差が生成
→ 候補横断更新1
→ 再活性2
```

これは単にcheckpoint数や再作用回数を非ゼロへ書き換えた結果ではない。

## 4. Compiler作用差分

HDS Compiler由来の作用差分構造は10問で能力経路へ添付された。

```text
HDS_ACTION_DELTA_ATTACHED = 10
HDS_ACTION_DELTA_CONSUMED = 0
specialist_actions_invoked = 0
```

したがってGPQA取得資料では、現行の厳格条件

- 状態差あり
- 後状態が別作用入力へ接続
- 状態条件充足
- 未確認追加条件なし
- 連結終端状態が一候補を一意識別

を全て満たして実際の候補寄与へ消費されたCompiler作用差分は0件だった。

これは0を失敗値とは扱わない。条件を満たさない作用を発火させなかった結果である。

## 5. GPQA結果

### current

```text
correct                   = 16 / 198
accuracy                  = 8.0808080808 %
answered                  = 85
answer_rate               = 42.9292929293 %
answered_accuracy         = 18.8235294118 %
suspended                 = 113
```

### controlled baseline

```text
correct                   = 22 / 198
accuracy                  = 11.1111111111 %
answered                  = 92
answer_rate               = 46.4646464646 %
answered_accuracy         = 23.9130434783 %
suspended                 = 106
```

### 差

```text
correct_delta             = -6
accuracy_points           = -3.0303030303
answered_delta            = -7
answer_rate_points        = -3.5353535354
answered_accuracy_points  = -5.0895140665
changed_answers           = 81
improved_cases            = 8
regressed_cases           = 14
net_improved_cases        = -6
```

**GPQA能力改善は失敗。**

## 6. 状態差循環別の分解

artifact個票を再集計した。

### A. 再活性なし — 85問

```text
current correct   = 0
baseline correct  = 5
current answered  = 0
baseline answered = 21
```

現行能力模型核では一次能力作用による状態差が無い場合、その後の再作用も出力も発生しない。

### B. 再活性あり・候補横断更新なし — 92問

```text
current correct   = 10
baseline correct  = 13
current answered  = 67
baseline answered = 59
改善              = 4
退行              = 7
```

一次状態差によって後続作用は起動したが、後続作用から新しい候補状態差を作れなかった群である。

### C. 候補横断更新あり — 21問

```text
current correct   = 6
baseline correct  = 4
current answered  = 18
baseline answered = 12
改善              = 4
退行              = 2
```

この21問は全件 `checkpoint_reactivations = 2`、`candidate_cross_updates = 1` だった。

つまり、

```text
状態差
→ 次作用
→ 新しい候補差
→ 次の再活性
```

まで到達した群では、今回の観測上はbaselineより正答数が2多かった。

ただしこの21問はcurrent機構の結果によって選ばれた部分集合である。したがって、これだけから「二段再作用が因果的に性能を+2した」とは確定しない。

因果寄与を確定するには、**同じ現行能力模型核・同じ取得資料で、再作用だけを無効化した対照**が必要である。

## 7. 回答状態遷移の分解

baseline / currentの回答有無を分けると:

```text
baseline回答 → current回答   = 59問
baseline回答 → current保留   = 33問
baseline保留 → current回答   = 26問
baseline保留 → current保留   = 80問
```

正答差:

- baseline保留→current回答: currentが5正答を新規獲得
- baseline回答→current保留: baselineの7正答を失う
- 両方回答した59問: current 11正答 / baseline 15正答で -4

合計 `+5 -7 -4 = -6` がcontrolled deltaと一致する。

したがって全体退行は単なる回答率低下だけではない。

1. 回答/保留境界の変化
2. 両方が回答した場合の候補選択差

の双方で発生している。

## 8. 解釈

### 成立したもの

```text
状態差なしで不発火             = PASS
状態差による再活性             = PASS
再作用後の新状態差             = PASS
新状態差による二段目再活性     = PASS
同一証拠の別名再加点禁止       = 機構試験PASS
Compiler作用差分の厳格不発火   = PASS
```

### 成立していないもの

```text
GPQA能力改善                    = FAIL
現行次作用選択の妥当性          = 未成立
現行一次能力作用の十分性        = 未成立
Compiler作用差分のGPQA実消費    = 0件
再作用単独の因果寄与            = 未分離
```

## 9. 今回得られた主要診断

旧実装では、checkpointを記録しても状態差が後続作用を変えず、再活性・大域再照合・候補横断更新が全て0だった。

今回、そこは解消した。

新しい問題は一段先へ移った。

> **状態差によって次作用が変わるだけでは足りない。どの状態差に対して、どの作用を次に選ぶかが能力を決める。**

今回の21問は「新しい差まで作れた循環」に能力上の可能性があることを示す一方、全体では初期作用・作用選択・出力境界がまだ弱い。

したがって次の主監査対象は「再作用を存在させること」ではなく、

```text
状態差の種別
↓
その差によって新しく必要になった不足
↓
不足を埋める作用の選択
↓
作用結果が何を変えたか
↓
再結合
```

の対応関係である。

## 10. 測定上の注意

- `data_compile_failed = 0` なので、今回のrunでは作用差分解析対象を全参照にした実装残差と通常Data成功集合の差は存在しなかった。
- したがってこの証拠境界修正は今runの集計値を変えない。
- `NO_FEEDBACK_LOOP` は後段HDS判断主体の「出力後に差し戻さない」境界名であり、MINIDORA能力模型核内部の状態差循環が無いという意味ではない。
- K3 93.5%との比較は外部能力尺度であり、本実装の機構受入とは分離する。
