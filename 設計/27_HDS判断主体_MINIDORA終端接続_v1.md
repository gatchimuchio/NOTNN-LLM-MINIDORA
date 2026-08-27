# HDS判断主体 — MINIDORA終端接続仕様 v1

日付: 2026-08-27
状態: 実装候補
基底言語: 日本語

## 1. 目的

MINIDORA模型核が形成した候補差を、そのまま最大差規則で最終確定しない。
模型核を計算主体 `C`、HDSを判断主体 `J` として分離し、正式HDS選択経路を次で閉じる。

```text
HDS構文化済みQuestion / Candidate / Data
  ↓
MINIDORA模型核 C
  - 候補差形成
  - 参照差形成
  - checkpoint / 再作用
  ↓
HDS判断主体 J
  - 対象・関係・閉包
  - 証拠
  - 矛盾
  - 反論・候補横断
  - Commit
  - 総暫定性
  ↓
APPROVE / SUSPEND
```

`C` の出力は候補であり権威ではない。最終採否権は `J/HDS` だけが持つ。

## 2. HDS本体との境界

本実装はHDS全体の公開転記ではない。
MINIDORAの知識選択終端に必要な有限射影だけを実装する。

含む:

- 対象・関係・閉包判定
- 出典単位の証拠分別
- 候補横断調停
- 矛盾保持
- 反転問題のN-1消去
- Commit / HOLD
- 暫定性保持
- 非選択候補・不確実性保持

含まない:

- HDS原理探索全体
- 永続記憶更新 `U`
- 外界作用のリスク判定
- Owner権限変更
- HDS本体の非公開解析正本

外界作用を伴わない知識選択では、リスク・可逆性判定門を `NOT_APPLICABLE` と明示する。

## 3. 証拠分別

判断主体は参照ごと、候補ごとに模型関係の寄与を分別する。

```text
+2以上  確定支持
+1      弱支持
-1      反対向・弱い反証
-2以下  確定反証
0       非寄与
```

この値は新しいHDSスコアではない。既存MINIDORA `能力作用則.py` が保持する関係方向・極性・scope差の意味を、そのまま判定門の状態へ写す。

同じ参照が複数候補を同程度に支持する場合、`HDS候補横断調停` により共通支持をCommit根拠から除外する。
参照をtop-k剪定せず、当該要求で得た全参照を保持する。

## 4. 通常選択のCommit条件

通常選択では次を満たす場合だけ `APPROVE` する。

1. 質問frameに `semantic_loss` 等の閉包阻害がない。
2. 候補集合のうち、出典横断調停後に完全関係支持を持つ候補が一つだけである。
3. その候補に確定反証がない。
4. 競合候補が同時にCommit可能状態ではない。
5. 最終権限が `J/HDS` にある。

弱支持だけの場合は情報を捨てず保持するが、断定へ昇格させない。

## 5. 反転選択

`except / least likely / incorrect` 等の反転選択は最低スコア投票にしない。

```text
N候補中 N-1候補がそれぞれCommit可能
かつ
残る候補が一つ
```

の場合だけ、その残余候補を例外として局所採用する。
閉じなければ `SUSPEND` する。

## 6. 暫定性

`APPROVE` は世界本体の絶対真理認定ではない。

```text
断定状態   = 局所暫定断定
運用状態   = COMMIT
採用状態   = 暫定採用
閉包状態   = CLOSED_FOR_OPERATION
暫定性状態 = 入力HDS-IRの暫定性を継承
```

非選択候補と不確実候補は判断結果へ保持し、後続観測で再開放可能とする。

## 7. 禁止事項

- HDS判断を `MINIDORA模型核` 内へ逆流させない。
- 旧K3 helperを正式回答経路へ復帰させない。
- benchmark正解ラベルを判断条件に使わない。
- 単純最大スコアをHDS判断と呼ばない。
- 共通sourceを独立根拠へ水増ししない。
- 弱支持のみで断定しない。
- 矛盾を消してからCommitしない。
- 非選択候補を削除しない。

## 8. 受入条件

- 一候補だけに完全関係証拠 → APPROVE
- 同一sourceが複数候補を共通支持 → SUSPEND
- 別sourceが競合候補を完全支持 → SUSPEND
- 支持と確定反証が共存 → SUSPEND
- 弱支持のみ → SUSPEND
- semantic_loss → SUSPEND
- 反転N-1成立 → 残余候補をAPPROVE
- 参照なし → SUSPEND
- 候補順・参照順で判断不変
- Cの参照最大候補とJの採用候補が異なり得る

## 9. 責任式

```text
C_result = MINIDORA(question, candidates, compiled_data)
Decision = HDS_Judge(question_hds, C_result, evidence_boundary)

Authority(C_result) = candidate_only
Authority(Decision) = J/HDS
```

これにより、HDSで観測・構文化・再構成・DataコンパイルしたMINIDORAが、終端でもHDSによって意思決定する循環を閉じる。
