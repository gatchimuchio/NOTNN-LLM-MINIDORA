# MINIDORA HDS監督介入制御 v1

状態: 現行正本  
基底言語: 日本語  
対象: MINIDORA選択問題の既存能力運用

## 1. 目的

HDSをMINIDORAのフィードバックループに対する**安全弁**として配置する。

通常MINIDORAの推論系は作り直さない。通常推論が自力で閉包した場合、HDSは介入せず、その結果を完全透過する。未閉包・競合・観測不足・状態停滞などの異常が観測された場合だけ、HDSが既存作用の起動を指示する。

```text
通常MINIDORA推論
        │
        ├─ 正常閉包 ─────────────→ そのまま出力
        │
        └─ 未閉包 / 競合 / 観測不足 / 停滞
                    ↓
                 HDS観測
                    ↓
          既存作用から次作用を選択
                    ↓
             既存作用を実行
                    ↓
             通常MINIDORAへ復帰
                    ↓
                通常再推論
```

HDSを後段の最終採否ラッパーとして置かない。また、HDSのために通常MINIDORA内部の候補生成・候補統合・採否を再構成しない。

## 2. 責任境界

通常MINIDORAは HDS Compiler、R、K3、direct relation、graph、candidate reconcile、Working Relation、local reparse、capability model、計算実行器、runtime採否、主体整合を保持する。候補生成・候補比較・回答形成・通常閉包は既存MINIDORAの責任である。

HDSが受け取るのは、既存処理状態、出力存在、根拠存在、直接検証状態、opaqueな参照状態署名、opaqueな候補状態署名、未解残差種別、既存MINIDORAが公開した介入可能作用だけとする。

HDSへ回答ラベル、候補本文、候補得点を渡さない。

HDSが返せるのは次だけである。

```text
NO_INTERVENTION
RUN_EXISTING_ACTION
REQUEST_STOP
```

HDSは回答を生成せず、候補の勝者を選ばず、通常MINIDORAのAPPROVEを再評価しない。

## 3. 正常系完全透過

最重要不変条件:

```text
HDS介入 = 0
=> HDS未搭載の通常MINIDORAと選択結果が完全同一
```

完全同一の対象には最低限次を含む。

- 初期参照経路
- 回答ラベル
- 回答内容
- APPROVE / SUSPEND / FAIL
- 通常MINIDORAが生成した理由
- 通常MINIDORA内部の能力作用

したがって、正常系に対してHDS用resolver、別能力提案の再統合、追加R、別採否Gateを挿入してはならない。

HDS監督メタ情報は、HDSが実際に介入した場合だけ付加できる。

## 4. 異常観測

HDSは正解ラベルやgoldを見て異常を判定しない。

観測対象は系自身の状態である。例:

- 通常MINIDORAがSUSPEND / FAIL
- 観測不足
- Data意味損失
- 候補競合
- 候補識別不足
- 状態差が生成されたが後続作用へ消費されない
- 同じ入力状態で同じ作用を反復しても進展しない

通常MINIDORAがAPPROVEした場合、診断文字列だけを理由にHDSが介入してはならない。

## 5. HDS介入可能作用

現行選択問題では最低限次を扱う。

- `REFERENCE` — 既存Rを段階的に広げて追加観測する。
- `EXISTING_WORKING_RECONCILE` — 既存Working Relation / 寄与Gate再作用。
- `EXISTING_LOCAL_REPARSE` — 既存局所Window再構文化。
- `EXISTING_CAPABILITY_MODEL` — 既存能力模型照合。
- `EXISTING_COMPUTE_EXECUTOR` — Compute IRが成立する領域で既存計算実行器を使う。

HDSが新しい能力作用を発明してはならない。既存側が作用機会として公開したものだけを起動できる。

## 6. 作用固有入力署名

同じ作用を無意味に反復しない。Rはquery plan / 取得段階、localは参照状態、Workingはrequest-local working state、capability modelは観測状態 / 候補状態、computeはCompute IRを既存側でopaqueな作用入力署名として公開する。

同一作用・同一入力署名をHDSが繰り返し要求しない。入力状態が変化した場合だけ同一作用を再利用できる。

## 7. 介入後復帰

HDSが作用を起動した直後にHDSが回答形成・候補統合を行ってはならない。

```text
HDS介入
↓
既存作用実行
↓
通常MINIDORA再評価
↓
監督観測点
↓
正常化なら終了
↓
未閉包なら必要時だけ次のHDS介入
```

HDSの役割は系を置き換えることではなく、異常時に系を正常な推論経路へ戻すことである。

## 8. R境界

初期RはHDS監督投入前の標準Rをそのまま使う。

HDSによるR拡張は、通常推論が観測不足等で閉じなかった場合だけ許可する。

追加Rでは次の一般修復を利用できる。

- 未被覆候補だけ追加fallbackする。
- 候補別queryで得たsourceを対称に予算へ残す。
- 同一sourceは1件へ統合する。
- `hds_query_choice` は検索経路情報に限定し、真偽票へ変換しない。

## 9. 同一Data再投票境界

能力模型の候補集合縮小だけで、同じDataから新しい識別票を作らない。

HDSが能力模型照合を起動する場合も、通常MINIDORAがSUSPENDした後の異常回復作用として扱う。正常APPROVEを別模型で再投票しない。

## 10. 旧HDS終端・再統合経路

次は履歴・互換資産として保持するが、現行active pathでは使用しない。

- `hds判断主体.py` の output-only Gate
- `runtime_hds_v1.py`
- `hds統合runtime.py`
- `hds統合判断主体.py`
- `hds能力経路_v2.py` の別formal C
- `hds適応候補調停.py`
- `hds既存能力resolver.py` を用いた監督用再統合

特に次の二種類を禁止する。

```text
MINIDORA
↓
後段HDS
↓
APPROVE / HOLD / REJECT
```

```text
通常MINIDORAを分解
↓
複数の能力提案へ再構成
↓
HDS用resolverで再統合
```

どちらも安全弁ではなく、通常系の置換になる。

## 11. 不変条件

1. HDSへ回答ラベル・候補得点を渡さない。
2. HDSは既存能力の候補を新規生成しない。
3. HDSは既存能力間の競合時に勝者を選ばない。
4. 通常MINIDORAがAPPROVEした場合はHDS介入0で完全透過する。
5. HDS非介入時は初期R・選択結果・理由を変更しない。
6. 同一作用・同一入力を反復起動しない。
7. 介入後は通常MINIDORA再評価へ戻る。
8. gold label / case ID / benchmark固有規則を使わない。
9. persistent canonical Kへrequest-local作業証拠を無断昇格しない。
10. 厳密言語模型核へHDS制御状態を逆流させない。
11. 非選択・計算・通常会話経路をHDS監督統合のために作り直さない。
12. HDS用resolverで通常MINIDORAの初期結果を再解釈しない。

## 12. 実装

現行active実装:

- `src/minidora/hds介入制御.py`
- `src/minidora/hds監督選択runtime.py`
- `src/minidora/hds参照拡張.py`
- `src/minidora/runtime.py`

`src/minidora/hds既存能力resolver.py` は履歴・互換資産として保持できるが、HDS安全弁active pathからは外す。

## 13. 検証

- HDS監督面に回答・候補得点フィールドがない。
- 通常APPROVEではHDS controller自体を呼ばない。
- HDS介入0で通常MINIDORA結果オブジェクトが完全透過する。
- 初期RがHDS投入前標準Rと同じである。
- 未閉包時だけ既存作用を追加起動できる。
- 介入後は通常MINIDORAを再実行する。
- HDS用resolverがactive監督経路に存在しない。
- R候補被覆/source identity境界を維持する。
- repository consistency / 日本語基底 / compileall / unit tests / CLI smokeを通す。

GPQAは構造受入後の能力観測であり、構造修正の成立条件そのものにはしない。
