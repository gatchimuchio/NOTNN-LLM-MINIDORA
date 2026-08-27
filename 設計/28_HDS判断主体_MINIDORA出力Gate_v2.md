# HDS判断主体 — MINIDORA出力Gate仕様 v2

日付: 2026-08-27
状態: 現行正本
基底言語: 日本語

## 1. 目的

MINIDORAを計算機としてのLLMに固定し、後段HDSの責任を「MINIDORAが形成した出力を外へ出すか否か」に限定する。

```text
自然言語 / Data
  ↓
HDS Compiler
  ↓
MINIDORA入力
  ↓
MINIDORA
  ↓
MINIDORA出力
  ↓
後段HDS
  ├─ APPROVE → 外部出力
  ├─ HOLD    → SILENT
  └─ REJECT  → SILENT
```

後段HDSが拒否・留保した場合、MINIDORAへ差し戻さない。そこで一回のLLM入出力を終端する。

## 2. 責任境界

### HDS Compiler

- 自然言語・外部Dataを観測・構文化する。
- MINIDORAが扱う入力状態へ変換する。
- Dataの意味残差・関係・識別性等を前段で保持する。

### MINIDORA

- HDS Compilerから渡された入力を計算する。
- 候補差・参照差・checkpoint・再作用状態を形成する。
- 自律的な再検索・再試行・目的変更は行わない。

### 後段HDS

- 判断入力は **MINIDORA出力だけ** とする。
- MINIDORA出力を `APPROVE / HOLD / REJECT` へ分別する。
- Question / Candidate / Data / Referenceを直接読み直さない。
- 問題を解き直さない。
- MINIDORAへ差し戻さない。

## 3. MINIDORA出力

現行の後段HDS入力型は `MINIDORA出力` である。

保持するもの:

- 出力状態
- 出力候補ID
- 候補差
- 参照候補差
- 参照同率候補
- checkpoint数
- 再作用回数
- 終端遍歴数

これは元Dataそのものではない。**MINIDORAの計算結果を監査可能な形で表した出力状態**である。

正式knowledge choiceでは、一般表層差へfallbackせず `参照最有力候補ID` をMINIDORA出力候補とする。

## 4. 後段HDSの終端

### APPROVE

MINIDORA出力が局所的に整合し、外へ出せる場合だけ出力する。

```text
HDS状態       = APPROVE
外部出力状態  = OUTPUT
運用状態       = COMMIT
```

### HOLD

MINIDORAが出力を成立させていない場合は留保する。

```text
HDS状態       = HOLD
外部出力状態  = SILENT
運用状態       = HOLD
```

### REJECT

MINIDORA出力内部に不整合がある場合は拒否する。

```text
HDS状態       = REJECT
外部出力状態  = SILENT
運用状態       = REJECT
```

HOLD / REJECTのどちらも、外部回答は存在しない。

表示層が必要なら、この無回答状態を「分かりません」と表面化してよい。ただしこれはMINIDORAが生成した答えではなく、**出力不存在という状態の表示**である。

## 5. 差し戻し禁止

後段HDSには次を持たせない。

- 再試行
- 再検索
- 再計算
- MINIDORAへの差し戻し
- 入力修正
- 目的変更
- 手段変更

```text
HDS HOLD / REJECT
  ↓
SILENT
  ↓
END
```

この境界を越えて「なぜ失敗したか」「Dataを追加するか」「別手段へ切り替えるか」「再度MINIDORAを呼ぶか」を判断する責任は、MINIDORAを部品として使う**上位AGI全体HDS**に属する。

## 6. LLMとAGIの境界

MINIDORA単体:

```text
入力 → 計算 → 出力 → 局所HDS採否 → 終端
```

AGI全体:

```text
全体HDS
  ↓
MINIDORAを含む手段選択
  ↓
MINIDORA局所結果
  ↓
局所HDS判断
  ↓
その判断結果を全体HDSが次の認知対象として判断
  ↓
必要なら新しい行為を起動
```

したがって、判断の再帰はAGI側で成立するが、MINIDORA自身へ自己再試行機構を持たせない。

## 7. 禁止事項

- 後段HDSへQuestion / Candidate / Data / Referenceを直接渡さない。
- 後段HDSで元Dataの証拠評価をやり直さない。
- source confidenceを後段HDSの再審査材料にしない。
- 後段HDSが別候補を新規生成しない。
- HOLD / REJECT後にMINIDORAを自動再起動しない。
- 一般表層winnerで正式MINIDORA出力を上書きしない。
- 無回答をもっともらしい文章で穴埋めしない。

## 8. 受入条件

- `HDS判断主体.判断()` の判断入力は `MINIDORA出力` 一つだけ。
- MINIDORAの一意な正の正式出力 → APPROVE / OUTPUT。
- MINIDORA出力不存在 → HOLD / SILENT。
- MINIDORA出力不整合 → REJECT / SILENT。
- HOLD / REJECTに再試行・差し戻しフィールドが存在しない。
- 参照信頼を変えても、同一MINIDORA出力に対する後段HDS判断は変わらない。
- 前段HDS CompilerとMINIDORA入力境界は従来どおり維持する。

## 9. 責任式

```text
CompiledInput = HDS_Compiler(Input, Data)
ModelOutput   = MINIDORA(CompiledInput)
Decision      = HDS(ModelOutput)

FinalOutput = ModelOutput   if Decision == APPROVE
FinalOutput = ∅             if Decision in {HOLD, REJECT}

Feedback(MINIDORA, Decision) = forbidden
```

この構造により、MINIDORAは計算機としてのLLMに留まり、出力後の判断はHDS、判断後の再帰的行為は上位AGI全体HDSへ分離される。
