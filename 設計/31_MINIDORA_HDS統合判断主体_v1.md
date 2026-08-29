# MINIDORA HDS統合判断主体 v1

状態: 試作正本候補  
対象: MINIDORAの選択問題実行経路  
基底言語: 日本語

## 1. 目的

MINIDORAの能力作用を増やすのではなく、**どの作用を次に要求し、どの計算結果を採用し、いつ留保・停止するか**という判断権限を、候補生成系から分離したHDS Judgement Subjectへ移す。

この設計はHDS全体をMINIDORAへ複製するものではない。HDSの有限なDomain Application / Projectionとして、一回のMINIDORA判断へ必要な判断主体条件だけを射影する。

## 2. 前提境界

LLM構成観測から得られる能力作用群と、意思決定主体を同一視しない。

```text
局所作用再現
≠ 作用関係再現
≠ 意思決定構造再現
≠ 能力主体
```

したがって、状態差・再参照・再結合等を増やすだけではHDS判断主体を成立させない。

HDSはLLM構成定義から生成しない。HDS側で既に定義されているJudgement Subject / Runtime境界を、MINIDORA領域へ有限射影する。

## 3. 三責任

```text
C_exec = 既存MINIDORA能力模型核 / 参照 / Compiler / 計算
J_hds  = MINIDORAHDS判断主体
M_mem  = MINIDORA認知世界 + 既存主体/Trinity記憶
```

物理的に同一Python processでも論理責任を分ける。

特に候補生成系のSelf-Commitを禁止する。

## 4. J_hdsの委任範囲

J_hdsが一回のRunで承認できる作用は次だけ。

1. `REFERENCE` — 追加観測を要求する。
2. `EVALUATE` — 候補差の計算を要求する。
3. `COMMIT` — 計算結果を局所採用する。
4. `SUSPEND` — 現条件では閉じないと判断する。
5. `STOP` — 終端済Runを停止する。

J_hdsは外部世界への任意行動、目的の自律変更、無制限探索を行わない。

## 5. Run状態

`MINIDORA認知世界` は少なくとも次を保持する。

- run_id
- 対象
- 委任目的
- HDS-IR
- 参照利用可能性 / 必須性
- 参照試行状態 / 参照数
- 評価状態 / 評価回答
- 未解残差
- 作用履歴
- 暫定性
- 再開放条件
- 版

要約結果だけを正本状態にせず、作用履歴と残差を保持する。

## 6. 最小循環

```text
Compiled CognitiveWorld
        ↓
J_hds: 次観測は必要か
   ├─ yes → REFERENCE → 観測帰還
   └─ no
        ↓
J_hds: 計算要求
        ↓
EVALUATE by C_exec
        ↓
候補計算結果
        ↓
J_hds
   ├─ 局所閉包支持 → COMMIT
   └─ 未閉包       → SUSPEND
```

候補計算結果が `APPROVE` を返しても、その時点ではまだRun状態は `OPEN` である。別のCOMMIT承認点を通ったときだけ `COMMITTED` になる。

## 7. 再開放

SUSPENDまたはCOMMIT後も、理由付きでRun Projectionを再開放できる。

再開放は旧履歴を消さない。

```text
旧世界
+ 新観測 / 未解残差 / 委任変更
→ REOPEN
→ 新版CognitiveWorld Projection
```

## 8. 無限循環防止

一回のMINIDORA Runは作用予算を持つ。

予算を使い切った場合は精度を落として完遂扱いせず `SUSPEND` する。

## 9. 既存資産の扱い

維持する:

- 厳密言語模型核
- 能力模型核
- HDS Compiler
- 参照供給器
- HDS選択推論実行
- 主体主幹 / Trinity記憶

責任を変更する:

- `能力状態差循環` はworker内部の局所計算であり、全体の次作用決定権を持たない。
- 旧 `hds判断主体.py` のoutput-only Gateは終端互換資産であり、中央制御主体とは扱わない。

## 10. 試作Runtime

`src/minidora/runtime_hds_v1.py` の `HDS駆動ミニドラ` を試作Runtimeとする。

選択問題では、既存v0.5の固定直列制御ではなく、`MINIDORAHDS判断主体` が `REFERENCE → EVALUATE → COMMIT/SUSPEND` を選ぶ。

非選択問題は既存v0.5へ委譲する。

## 11. 成立と非主張

本試作が成立させるもの:

- 継続したRun状態
- 委任目的
- 次観測 / 計算要求生成
- 候補生成と最終採用の分離
- COMMIT / SUSPEND権限
- 理由付き再開放経路
- 作用予算による有限停止

本試作だけでは主張しないもの:

- HDS Framework Kernel完全実装
- HDS全原理発見機構の完全再現
- AGI全体の自律主体
- 外部世界行動主体
- LLM一般にHDSが普遍必須であること

この境界を保ったまま、MINIDORAに必要なHDS判断主体の最小成立を実装する。
