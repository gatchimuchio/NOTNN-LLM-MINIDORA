# MINIDORA 性能改善 v0.6 作業記録 — 2026-08-23

## 状態

```text
IMPLEMENTED
PR DIFF AUDITED
REGRESSION FIXTURES ADDED
GITHUB ACTIONS RUNNER PRESTART FAILURE
EXTERNAL GPQA BENCHMARK NOT RERUN
```

本記録は性能改善実装の作業状態を固定するものであり、GPQA Diamond の新しい正式スコアを宣言するものではない。

固定prototype baselineは引き続き `GPQA_Diamond_PROTOTYPE_BASELINE_2026-08-22.json` の **8 / 198 = 4.0404040%** とする。過去baselineを上書きしない。

v0.5作業記録に記載された開発途中実測 **17 / 198 = 8.5858586%** は、v0.6の正式値として扱わない。

## v0.6 の目的

Jの `NO_GUESS` / `SUSPEND` 境界やLayer-0 / HDS Compiler契約を緩めず、選択問題で既に取得・構造化された証拠から候補差分を失わないようにする。

GPQA固有ルール、正解ラベル参照、gold依存分岐は追加しない。

## 実装した改善

### 1. 同一sourceの共通知識を候補識別証拠から分離

対象: `src/minidora/hds_candidate_reconcile.py`

従来は同一sourceが複数候補へ同程度に一致した場合でも、識別係数に正のfloorが残っていた。そのため「全候補へ当たる共通知識」が小さい候補marginやproof provenanceとして残り得た。

v0.6では次へ変更した。

- 一候補だけを支持するsourceは従来どおり識別係数 `1.0`
- 複数候補を支持するsourceは、最大競合候補に対する**相対優位**だけを識別力とする
- own <= competitor のsourceは当該候補のmarginへ寄与させない
- 調停得点 `0` のsourceは採用証拠・proof provenanceから除外
- 負の証拠へは変換しない

これは資料の絶対的な関連性と、4候補を区別する情報量を分離する変更である。

### 2. 反転選択意図の被覆拡張

対象: `src/minidora/choice_intent.py`

明示的な `except / incorrect / not true / cannot` に加えて、次の反転選択を `EXCEPTION` として扱う。

- `least likely`
- `least probable`
- `least expected`
- `least consistent`
- `least compatible`
- `least supported`
- `least plausible`
- `most unlikely`
- 対応する日本語の「最も可能性が低い」「最も整合しない」等

一方、単なる `smallest / minimum` は数値比較と混同するため `POSITIVE` のまま維持する。

### 3. HDS関係の始点→終点を候補意味署名へ保持

対象: `src/minidora/k3_hds_native.py`

従来の `HDS意味署名` は次だけを保持していた。

```text
語
関係種別
座標種別
```

このため、同じ語と同じ関係種別を使い、関係方向だけが異なる候補、例えば次を署名段階で区別できなかった。

```text
A → B
B → A
```

v0.6では `HDS関係辺署名` を追加し、非generic関係について次を保持する。

```text
関係種別
始点語
終点語
```

Kへ投入されたHDS relation factについても `→` の前後を分離して同じ有向署名へ復元する。

候補側に有向関係が存在する場合、候補の `始点→終点` 一致を優先し、問い側にある共通方向を逆向き候補へ伝染させない。

これにより、語集合だけでは同型だった候補を構造差で比較できる。

### 4. `false / incorrect` の内容語による誤反転を抑止

対象: `src/minidora/choice_intent.py`

従来は最終質問文に `false` や `incorrect` が含まれるだけで `EXCEPTION` へ反転し得た。

例えば次は正方向の質問である。

```text
Which mechanism explains the false positive signal?
Which process produces an incorrect measurement result?
```

v0.6では `false / incorrect / not` を単なる内容語として検出せず、`Which ... is false`、`Which ... is not ...` 等の**候補選択述語へ結び付く場合**だけ反転する方向へ狭めた。

これにより、誤り・偽陽性・非活性等を「説明対象」として含む通常質問を、誤答候補選択へ取り違えにくくする。

## 追加した回帰fixture

### `tests/test_hds_candidate_reconcile.py`

- 同一sourceのfact/document二重加点禁止
- 全候補共通sourceをmargin/provenanceから除外
- 僅差の共通sourceは相対差だけを残す
- 独立sourceは別々に加点

### `tests/test_choice_intent.py`

- `least likely / least consistent / most unlikely`
- `Which ... is false` と `Select the false statement`
- 日本語の反転表現
- `false positive / incorrect measurement` を誤反転しないnegative control
- `smallest / minimum` を誤反転しないnegative control

### `tests/test_k3_directed_relation.py`

- 同一語・同一関係種別でも逆方向を一致扱いしない
- Data `Alpha → Beta` が `Alpha → Beta` と `Beta → Alpha` を分別できる
- 問い側に `Alpha → Beta` が存在しても、それを逆向き候補へ共通ボーナスとして伝染させない

## 非変更境界

以下は変更していない。

- Layer-0上位契約
- HDS Compiler Protocol
- Jの `NO_GUESS`
- `SUSPEND` 境界
- GPQA固有分岐
- gold answer参照
- 正解ラベル別ルール
- ニューラルモデル依存

## GitHub Actions 状態

実装code head `28d25cd57728b3765c8d0586e970410736d33eef` で確認。

### 再構築CI

- workflow run: `#299`
- run id: `32582547792`
- Ubuntu / Windows × Python 3.11–3.14 の8jobすべて `failure`
- 全jobで `steps=null`
- job log URLも生成されていない

### GPQA current measurement

- workflow run: `#13`
- run id: `32582547752`
- `measure` job: `failure`
- `steps=null`
- job log URLも生成されていない

この失敗はcheckout・install・test・benchmarkのいずれも開始する前に発生しているため、**product regression / test failure / GPQA resultには分類しない**。

現時点のfailure classification:

```text
environment failure / runner prestart failure
```

## 補助論理確認

Actionsとは独立に、変更した決定論ロジックについて局所確認を行った。

- 反転意図fixture群は期待する `EXCEPTION / POSITIVE` に分離
- 全候補共通sourceは候補得点 `0` となりprovenanceから消える
- 一候補固有sourceは従来どおり識別係数 `1.0`

これはrepository全体のCI PASSを代替しない。全統合試験の観測状態は未確定のままとする。

## 現時点で確定できること

- v0.6の4改善は実装済み
- PR差分上、GPQA/gold固有依存は追加していない
- 新しい失敗クラスを狙った一般回帰fixtureを追加した
- 局所決定論ロジックは期待挙動を確認した
- Actionsは実行前停止のため、repository全体のテストPASS/FAILは未観測
- GPQA Diamond新スコアは未観測

## 未確定

- v0.6のGPQA Diamond正答数
- 回答数 / SUSPEND数の変化
- v0.5途中実測17/198からの増減
- Linux / Windows全matrixの実行結果

これらはrunnerが実際にstepを開始できる状態でのみ確定する。

## 次の測定条件

同一実装内容を含むmain commitに対して、次を実行する。

```text
repository_consistency_check
compileall
unittest discover
CLI smoke
GPQA current measurement
```

測定が成立した場合だけ、v0.6の新規評価記録として正答数・回答数・SUSPEND数・参照被覆・失敗分類を固定する。
