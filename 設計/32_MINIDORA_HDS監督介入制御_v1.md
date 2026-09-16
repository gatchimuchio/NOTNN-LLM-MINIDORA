# MINIDORA HDS監督介入制御 v1

状態: **MINIDORA30 / GPQA / 既存API互換性能正本**（2026-09-17責任再分類）  
旧状態: 2026-09-07時点の内部現行正本  
現行内部実行正本: `58_MINIDORA_HDS実行主体_v1.md`  
基底言語: 日本語  
対象: MINIDORA30選択問題の既存能力運用・性能再現

## 0. 現行HDS-firstとの責任境界

本書の経路は削除しない。MINIDORA30 / MINIDORA80 / GPQA正本値、既存API、過去比較を再現するための互換性能経路として維持する。

```text
本書の互換経路
通常MINIDORA
↓
正常閉包なら完全透過
↓ 未閉包時だけ
HDS監督介入
```

2026-09-17以後の内部開発正本は次である。

```text
HDS実行主体
↓
目的・状態・残差から常時作用を選択
↓
MINIDORA部品
↓
作用結果・状態差をHDSへ帰還
↓
再作用 / COMMIT / SUSPEND / FAIL
```

従って、本書中の「現行」「標準MINIDORA core」「active path」は、**MINIDORA30互換性能経路の内部での現行**を意味し、リポジトリ全体の内部実行正本を意味しない。本書の制約を新HDS-firstへ無言転用しない。

## 1. 目的

HDSをMINIDORA30互換フィードバックループに対する**監督介入層**として配置する。

用語を次のように固定する。

- **HDS監督** — 通常MINIDORAの状態を外側から観測し、介入要否を判定する層。監督そのものは出力を書き換えない。
- **HDS介入** — 監督判断により `RUN_EXISTING_ACTION` を発行し、既存作用を実際に起動すること。`REFERENCE`、`EXISTING_COMPUTE_EXECUTOR` 等はこの下位種別である。
- **HDS非介入** — `NO_INTERVENTION`。通常MINIDORAの結果を完全透過する。
- **HDS停止判断** — `REQUEST_STOP`。監督判断であり、既存作用を起動しないためHDS介入件数には含めない。

従来の「HDS安全弁」は、HDS監督介入層全体を指す総称としては廃止する。誤閉包防止や停止判断などの安全性はHDS監督介入層が持つ性質の一部であり、追加Reference取得・既存計算実行・再評価を含むHDS介入全体と同一視しない。

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

通常MINIDORAは HDS 構文化器、R、K3、direct relation、graph、candidate reconcile、Working Relation、local reparse、capability model、計算実行器、実行系採否、主体整合を保持する。候補生成・候補比較・回答形成・通常閉包は既存MINIDORAの責任である。

HDSが受け取るのは、既存処理状態、出力存在、根拠存在、直接検証状態、opaqueな参照状態署名、opaqueな候補状態署名、未解残差種別、既存MINIDORAが公開した介入可能作用だけとする。

HDSへ回答ラベル、候補本文、候補得点を渡さない。

HDSが返せるのは次だけである。

```text
NO_INTERVENTION
RUN_EXISTING_ACTION
REQUEST_STOP
```

HDSは回答を生成せず、候補の勝者を選ばず、通常MINIDORAのAPPROVEを再評価しない。

> この制約はMINIDORA30互換監督面の制約である。HDS-first新コアでは、模型・能力作用の局所成果をHDS実行状態へ帰還できるが、benchmark gold / case ID / 候補得点だけで最終COMMITしてはならない。

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

したがって、正常系に対してHDS用re解決器、別能力提案の再統合、追加R、別採否関門を挿入してはならない。

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

MINIDORA30互換coreでHDSが外側から起動する作用は、原則として次の二つへ限定する。

- `REFERENCE` — 既存Rを段階的に広げて追加観測する。
- `EXISTING_COMPUTE_EXECUTOR` — 構文化器が閉包済みCompute IRを生成できた場合だけ既存計算実行器を使う。

Working Relation再作用、局所再照合、能力模型再照合は能力模型核内部の一般作用であり、標準HDS監督が別経路として再実行しない。
専門領域解決器をHDS作用候補へ入れない。HDSは計算法則・専門知識・候補勝者を生成しない。

HDS-first新コアの作用集合はこの二作用へ限定しない。新コアでは、構文化・参照・計算・模型・能力・計画・合成等を明示作用契約でHDSへ公開する。

## 6. 作用固有入力署名

同じ作用を無意味に反復しない。Rはquery plan / 取得段階、localは参照状態、Workingはrequest-local working state、capability modelは観測状態 / 候補状態、computeはCompute IRを既存側でopaqueな作用入力署名として公開する。

同一作用・同一入力署名をHDSが繰り返し要求しない。入力状態が変化した場合だけ同一作用を再利用できる。

HDS-first新コアでもこの原則を継承する。ただし「入力状態」はHDS全状態ではなく、各作用が**実際に消費する作用固有入力**でなければならない。無関係な残差・成果の変化だけで同じ外部GETや固定計算を再実行してはならない。

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

この復帰規則はMINIDORA30互換経路に限定する。HDS-firstでは作用結果を直接HDS実行状態へ帰還し、HDSが次作用を選ぶ。

## 8. R境界

初期RはHDS監督投入前の標準Rをそのまま使う。

HDSによるR拡張は、通常推論が観測不足等で閉じなかった場合だけ許可する。

追加Rでは次の一般修復を利用できる。

- 未被覆候補だけ追加代替経路する。
- 候補別queryで得たsourceを対称に予算へ残す。
- 同一sourceは1件へ統合する。
- `hds_query_choice` は検索経路情報に限定し、真偽票へ変換しない。

## 9. 同一Data再投票境界

能力模型の候補集合縮小だけで、同じDataから新しい識別票を作らない。

HDSが能力模型照合を起動する場合も、通常MINIDORAがSUSPENDした後の異常回復作用として扱う。正常APPROVEを別模型で再投票しない。

## 10. 旧HDS終端・再統合経路

次は履歴・互換資産として保持するが、MINIDORA30互換active pathでは使用しない。

- `hds判断主体.py` の output-only 関門
- `実行系_HDS_v1.py`
- `HDS統合実行系.py`
- `hds統合判断主体.py`
- `hds能力経路_v2.py` の別formal C
- `hds適応候補調停.py`
- `hds既存能力re解決器.py` を用いた監督用再統合

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
HDS用re解決器で再統合
```

どちらも本書のHDS監督介入ではなく、通常系の置換になる。

HDS-first新コアも旧終端HDSを復活させない。新コアはHDSが最初から作用を駆動するため、上記の「後段HDS」と構造が異なる。

## 11. 不変条件

1. MINIDORA30互換監督面ではHDSへ回答ラベル・候補得点を渡さない。
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
12. HDS用re解決器で通常MINIDORAの初期結果を再解釈しない。

## 12. 実装

MINIDORA30互換性能経路:

- `src/minidora/hds介入制御.py` — `標準HDS介入制御`
- `src/minidora/HDS監督選択実行系.py`
- `src/minidora/hds参照拡張.py`
- `src/minidora/実行系.py`

HDS-first内部正本:

- `src/minidora/HDS実行主体.py`
- `src/minidora/HDS駆動コア.py`
- `src/minidora/HDS構文化作用.py`
- `src/minidora/HDS汎用作用.py`
- `src/minidora/HDS模型作用.py`
- `src/minidora/HDS能力作用.py`
- `src/minidora/HDS計画作用.py`
- `src/minidora/hds介入制御.py` — `標準HDS一般作用制御`

`src/minidora/hds既存能力re解決器.py` は履歴・互換資産として保持できるが、HDS監督介入active pathからは外す。

## 13. 検証

MINIDORA30互換経路では次を維持する。

- HDS監督面に回答・候補得点フィールドがない。
- 通常APPROVEではHDS controller自体を呼ばない。
- HDS介入0で通常MINIDORA結果オブジェクトが完全透過する。
- 初期RがHDS投入前標準Rと同じである。
- 未閉包時だけ既存作用を追加起動できる。
- 介入後は通常MINIDORAを再実行する。
- HDS用re解決器がactive監督経路に存在しない。
- R候補被覆/source identity境界を維持する。

HDS-first新コアでは `58_MINIDORA_HDS実行主体_v1.md` の受入条件を別に満たす。

repository consistency / 日本語基底 / compileall / unit tests / CLI smokeは両経路で通す。

GPQAは構造受入後の能力観測であり、構造修正の成立条件そのものにはしない。MINIDORA30の正本値をHDS-first新コアの性能値へ読み替えない。
