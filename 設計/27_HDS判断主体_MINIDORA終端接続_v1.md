# HDS判断主体 — MINIDORA終端接続仕様 v1（失効）

日付: 2026-08-27
状態: **失効・監査履歴のみ**

この文書が定めていた「後段HDSがQuestion / Candidate / Data / Referenceを再度受け取り、出典証拠を再審査して採否する」構造は、MINIDORAの責任境界を誤っていたため失効した。

誤りは、HDS Compilerですでに構文化されMINIDORAへ入力されたDataを、MINIDORAの出力後に後段HDSが再び直接読む構造にした点である。これでは後段HDSがMINIDORAの出力を判断するのではなく、問題を再度解く経路になり得る。

現行正本は [`28_HDS判断主体_MINIDORA出力Gate_v2.md`](28_HDS判断主体_MINIDORA出力Gate_v2.md) とする。

現行境界:

```text
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

後段HDSはMINIDORA出力だけを受け取る。Question / Candidate / Data / Referenceを直接受け取らず、再検索・再計算・差し戻しも行わない。
