# MINIDORA HDS監督介入制御 v1

状態: 現行正本  
基底言語: 日本語  
対象: MINIDORA選択問題の既存能力運用

## 1. 目的

既存MINIDORAの能力部品を作り直さず、通常実行系を保持したまま、未閉包・競合・観測不足が生じた時だけHDSが既存作用へ介入する。

HDSを後段の最終採否ラッパーとして置かない。

```text
既存MINIDORA通常実行
        │
        ├─ 閉包 → そのまま出力
        │
        └─ 未閉包 / 競合 / 観測不足
                    ↓
                HDS観測
                    ↓
          既存作用から次作用を選択
                    ↓
             既存MINIDORAへ復帰
                    ↓
                  再評価
```

## 2. 責任境界

既存MINIDORAは HDS Compiler、R、K3、direct relation、graph、candidate reconcile、Working Relation、local reparse、capability model、計算実行器、runtime採否、主体整合を保持する。候補生成・候補比較・回答形成は既存MINIDORAの責任である。

HDSが受け取るのは、既存処理状態、出力存在、根拠存在、直接検証状態、opaqueな参照状態署名、opaqueな候補状態署名、未解残差種別、既存MINIDORAが公開した介入可能作用だけとする。

HDSへ回答ラベル、候補本文、候補得点を渡さない。

HDSが返せるのは次だけである。

```text
NO_INTERVENTION
RUN_EXISTING_ACTION
REQUEST_STOP
```

HDSは回答を生成せず、候補の勝者を選ばず、最終COMMITを行わない。

## 3. 既存能力resolver

複数の既存能力から候補が形成された場合、既存MINIDORA内部のresolverが統合する。

- 直接関係検証は既存の強い局所証拠として保持する。
- 明示計算がある場合は計算完全一致を利用できる。
- K3系と能力模型系が同じ回答へ閉じれば採用できる。
- 一方だけが根拠付きで閉じ、他方が保留なら有効提案を利用できる。
- 根拠付き既存能力が異なる回答へ閉じた場合は、HDSに勝者を選ばせず `CANDIDATE_CONFLICT` として再作用候補へ戻す。

## 4. HDS介入可能作用

現行選択問題では最低限次を扱う。

- `REFERENCE` — 既存Rを段階的に広げて追加観測する。
- `EXISTING_WORKING_RECONCILE` — 既存Working Relation / 寄与Gate再作用。
- `EXISTING_LOCAL_REPARSE` — 既存局所Window再構文化。
- `EXISTING_CAPABILITY_MODEL` — 既存能力模型照合。
- `EXISTING_COMPUTE_EXECUTOR` — Compute IRが成立する領域で既存計算実行器を使う。

HDSが新しい能力作用を発明してはならない。既存側が作用機会として公開したものだけを起動できる。

## 5. 作用固有入力署名

同じ作用を無意味に反復しない。Rはquery plan / 取得段階、localは参照状態、Workingはrequest-local working state、capability modelは観測状態 / 候補状態、computeはCompute IRを既存側でopaqueな作用入力署名として公開する。

同一作用・同一入力署名をHDSが繰り返し要求しない。入力状態が変化した場合だけ同一作用を再利用できる。

## 6. 介入後復帰

HDSが作用を起動した直後にHDSが連続判断してはならない。

```text
HDS介入
↓
既存作用実行
↓
既存MINIDORA再評価
↓
監督観測点
↓
必要なら次のHDS介入
```

## 7. R修復

旧Rにはgeneric primaryが1件以上あるだけで候補別fallbackが起動しない場合と、取得上限をgeneric文書が占有して候補別sourceが落ちる場合があった。

現行active pathでは次を一般修復として使う。

- 未被覆候補だけ追加fallbackする。
- 候補別queryで得たsourceを対称に予算へ残す。
- 同一sourceは1件へ統合する。
- `hds_query_choice` は検索経路情報に限定し、真偽票へ変換しない。

## 8. 同一Data再投票境界

能力模型の候補集合縮小だけで、同じDataから新しい識別票を作らない。

active監督経路では能力模型内部の同Data再投票を無効化し、外界観測または作業状態が変化した場合にだけHDS監督ループから新しい評価Runを起動する。

## 9. 旧HDS終端経路

次は履歴・互換資産として保持するが、現行active pathでは使用しない。

- `hds判断主体.py` の output-only Gate
- `runtime_hds_v1.py`
- `hds統合runtime.py`
- `hds統合判断主体.py`
- `hds能力経路_v2.py` の別formal C
- `hds適応候補調停.py`

特に次の旧構造は現行では採用しない。

```text
MINIDORA
↓
後段HDS
↓
APPROVE / HOLD / REJECT
```

`28_HDS判断主体_MINIDORA出力Gate_v2.md` と `31_MINIDORA_HDS統合判断主体_v1.md` の現行状態宣言は本書によって上書きされ、両文書は履歴設計として扱う。

## 10. 不変条件

1. HDSへ回答ラベル・候補得点を渡さない。
2. HDSは既存能力の候補を新規生成しない。
3. HDSは既存能力間の競合時に勝者を選ばない。
4. 正常閉包時はHDS介入0を許す。
5. 同一作用・同一入力を反復起動しない。
6. 介入後は既存MINIDORA再評価へ戻る。
7. gold label / case ID / benchmark固有規則を使わない。
8. persistent canonical Kへrequest-local作業証拠を無断昇格しない。
9. 厳密言語模型核へHDS制御状態を逆流させない。
10. 非選択・計算・通常会話経路をHDS監督統合のために作り直さない。

## 11. 実装

現行active実装:

- `src/minidora/hds介入制御.py`
- `src/minidora/hds既存能力resolver.py`
- `src/minidora/hds監督選択runtime.py`
- `src/minidora/hds参照拡張.py`
- `src/minidora/runtime.py`

既存能力実装は置換せず再利用する。

## 12. 検証

- HDS監督面に回答・候補得点フィールドがない。
- 正常閉包ではHDS介入0。
- 未閉包時だけ既存作用を追加起動できる。
- 既存能力競合時にHDSが回答を選ばない。
- R候補被覆/source identity境界を維持する。
- repository consistency / 日本語基底 / compileall / unit tests / CLI smokeを通す。

GPQA再測定はこの構造還元の必須条件とはしない。
