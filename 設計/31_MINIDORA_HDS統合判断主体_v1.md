# MINIDORA HDS統合判断主体 v1

状態: 試作正本候補  
対象: MINIDORAの選択問題実行経路  
基底言語: 日本語

## 1. 目的

MINIDORAの能力作用を増やすのではなく、**どの作用を次に要求し、どの計算結果を採用し、いつ留保・停止するか**という判断権限を、候補生成系から分離したHDS Judgement Subjectへ移す。

この設計はHDS全体をMINIDORAへ複製するものではない。HDSの有限なDomain Application / Projectionとして、一回のMINIDORA判断へ必要な判断主体条件だけを射影する。

## 2. 前提境界

```text
局所作用再現
≠ 作用関係再現
≠ 意思決定構造再現
≠ 能力主体
```

HDSはLLM構成定義から生成しない。HDS側で既に定義されているJudgement Subject / Runtime境界をMINIDORA領域へ有限射影する。

## 3. 三責任

```text
C_exec = 既存MINIDORA能力模型核 / 参照 / Compiler / 計算
J_hds  = MINIDORAHDS判断主体
M_mem  = MINIDORA認知世界 + 既存主体/Trinity記憶
```

候補生成系のSelf-Commitを禁止する。

## 4. 権限境界

```text
C_exec: REFERENCE結果 / EVALUATE結果 / PROPOSE
J_hds : 次作用要求 / COMMIT / SUSPEND / STOP / REOPEN
```

旧 `hds判断主体.py` のoutput-only Gateはv0.5互換資産として残すが、v1経路では通さない。

候補計算が正の一意候補を形成しても、状態は `PROPOSE` であり採用ではない。別のJ_hds COMMITを通って初めて外部結果へ昇格する。

## 5. J_hdsの委任作用

1. `REFERENCE` — 追加観測を要求する。
2. `EVALUATE` — 候補差の計算を要求する。
3. `COMMIT` — PROPOSEされた結果を局所採用する。
4. `SUSPEND` — 現条件では閉じないと判断する。
5. `STOP` — 終端済Runを停止する。

外部世界への任意行動、目的の自律変更、無制限探索は行わない。

## 6. 最小循環

```text
Compiled CognitiveWorld
        ↓
J_hds: REFERENCEが必要か
   ├─ yes → C_execへ観測要求 → 帰還
   └─ no
        ↓
J_hds: EVALUATE要求
        ↓
C_exec: PROPOSE / SUSPEND
        ↓
J_hds
   ├─ PROPOSE + 局所閉包支持 → COMMIT
   └─ 未閉包                 → SUSPEND
```

`PROPOSE ≠ APPROVE ≠ COMMIT` を固定する。

## 7. Run状態

`MINIDORA認知世界` は対象、委任目的、HDS-IR、参照状態、評価状態、未解残差、作用履歴、暫定性、再開放条件、版を保持する。

## 8. 再開放

SUSPENDまたはCOMMIT後も理由付きでRun Projectionを再開放できる。旧履歴を消さない。

## 9. 無限循環防止

Runは作用予算を持ち、超過時は精度を落として完遂扱いせず `SUSPEND` する。

## 10. 既存資産

維持する:

- 厳密言語模型核
- 能力模型核
- HDS Compiler
- 参照供給器
- 主体主幹 / Trinity記憶
- v0.5 Runtime（比較基準）

v1では、既存 `能力状態差循環` はworker内部の局所能力作用とし、全体の次作用決定権を持たない。

## 11. 成立と非主張

成立させるもの:

- 継続Run状態
- 委任目的
- 次観測 / 計算要求生成
- 候補生成と最終採用の分離
- COMMIT / SUSPEND権限
- 理由付きREOPEN
- 有限停止

主張しないもの:

- HDS Framework Kernel完全実装
- HDS全原理発見機構の完全再現
- AGI全体の自律主体
- 外部世界行動主体
- LLM一般にHDSが普遍必須であること

この境界を保ち、MINIDORAに必要なbounded HDS Judgement Subjectの最小成立形とする。
