# HDS Compiler Architecture v1.2

## 1. 位置づけ

v1.2は、v1.1で生成可能になったFailure Signature候補を、反復Runを跨いで明示的に蓄積・再利用し、Compiler改善候補へ帰還する公開Architectureである。

v1.2はv1 / v1.1を削除・置換しない。旧Projection・旧失敗症状・局所条件を保持したまま、後継の再解釈を追加する。

基底・規定言語は日本語とする。多言語は外部API、規格、Data、原文照合、互換性など実務上やむを得ない表層に限定する。

## 2. 目的

v1.2の目的は、Failure Signatureを単発ログで終わらせず、次の閉路へ接続することである。

```text
Compiler Run
↓
Failure Signature候補
↓
明示Failure Signature Bank
↓
同型性・反復性・共通条件 / 局所条件の分離
↓
Signature状態更新
↓
Compiler改善候補生成
↓
回帰監査・上位採否
↓
必要な場合のみ次版Compilerへ反映
```

Compiler自身が実装規則を書き換えることは禁止する。

## 3. 明示Bank

Failure Signature Bankはglobal singletonにしない。

呼出側が明示的にBank instanceまたはSnapshotを保持・受け渡す。通常の `コンパイル()` / `詳細コンパイル()` はBankを参照せず、同一入力・同一引数に対して従来どおり決定論的でなければならない。

公開APIは次を基本とする。

```text
成果 = Compiler.詳細コンパイル(input)
Snapshot = Compiler.失敗帰還(成果, Bank, Run参照=...)
改善候補 = Compiler.改善候補(Bank)
```

## 4. Failure Signature昇格

単発失敗は `PROBATION` とする。

同一構造原因・同一失敗分類が独立Runで反復した場合、Failure Signatureとして `ACTIVE` へ昇格できる。v1.2の既定最小独立Run数は2とする。

ただし以下を禁止する。

- 同一Runの重複観測を反復回数へ二重計上する
- 症状文字列だけの一致で構造原因を統合する
- 構造原因が異なる失敗を同一Signatureへ統合する
- 共通条件抽出のために局所条件を削除する
- ACTIVE化をCompiler実装修正の自動承認とみなす

## 5. 共通条件と局所条件

複数観測を統合するとき、起動条件は次へ分離する。

- 共通起動条件: 同型失敗の全観測に共通する条件
- 局所起動条件: 一部観測だけに現れる条件

原症状、Run履歴、由来候補ID、影響範囲、非影響範囲、違反前提、回復、次探索軸、再利用チェックを保持する。

## 6. 改善候補

ACTIVE Signatureから、公開Compilerで扱える改善候補を生成する。

改善対象は少なくとも次を持つ。

- 座標生成規則
- 作用素集合
- 保持構造
- Domain Adapter
- Identity Lock
- Framework Projection
- Checklist

改善候補は `自動適用禁止=True` を必須とする。

改善候補の昇格には少なくとも次を要求する。

1. 同型失敗の独立反復
2. 既存正例・負例・境界例への回帰監査
3. HDS本体または権限を持つ上位判断主体による採否

## 7. 改善対象の既定写像

v1.2では最低限、次の公開可能な写像を持つ。

- `coordinate_unfixed` → 座標生成規則
- `closure_failure` → 座標生成規則
- `relation_failure` → 作用素集合
- `semantic_loss_failure` → 保持構造
- その他 → Checklist

これはHDS本体の最終選別規則ではなく、公開Front-Endの改善候補生成用の有限Projectionである。

## 8. Snapshotと再現性

BankはSnapshotを生成できなければならない。

Snapshotは少なくとも次を含む。

- 版
- 観測数
- 観測履歴
- Signature記録
- 改善候補
- 旧記録保持
- 自動自己改変禁止

SnapshotはUTF-8 JSONへ決定論的に直列化し、復元後も同一内容を保持できること。

## 9. HDS本体との境界

公開するもの:

- Failure Signature候補
- 明示Bank契約
- 反復・同型性の公開判定
- 共通 / 局所条件分離
- 改善対象候補
- 改善候補の昇格条件
- 自動適用禁止境界

公開しないもの:

- HDS Native / Kernelの上流導出規則
- HDS本体の最終Gate判定アルゴリズム
- PrincipleStateの最終昇格規則
- 全体更新則
- 非公開解析正本

v1.2のBankがACTIVE Signatureや改善候補を生成しても、それ自体をHDS本体の最終採否とみなしてはならない。

## 10. 受入条件

v1.2は少なくとも次を満たすこと。

1. 同一Run重複を二重計上しない
2. 独立Run反復でSignatureをACTIVE化できる
3. 共通起動条件と局所起動条件を分離する
4. 構造原因の異なる失敗を統合しない
5. ACTIVE Signatureから改善候補を生成する
6. 改善候補は自動適用禁止である
7. Bank JSON往復で監査状態を保持する
8. Bank帰還後も通常Compilerの同一入力結果が変化しない
9. v1 / v1.1機能契約を維持する
10. HDS本体非公開境界を維持する

## 11. 留保

v1.2は改善候補の自動実装、自己書換え、自己承認を扱わない。

今後、Failure Signatureの反復からDomain-local判定、MERGED / DEPRECATED / RETIRED状態遷移、回帰データセット生成、改善候補の機械監査補助を追加できる。ただし、それらも最終採否境界を越えてはならない。
