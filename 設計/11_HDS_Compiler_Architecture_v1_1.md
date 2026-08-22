# HDS Compiler Architecture v1.1

## 0. 位置づけ

本文書は、MINIDORA公開標準HDS Compiler Architecture v1を、**再利用可能な構造生成とR接続**まで進めるv1.1正本である。

v1は廃棄しない。`10_HDS_Compiler_Architecture_v1.md` を履歴・前段契約として保持し、本版はその上へ追加する。

本版もHDS NativeまたはHDS Framework Kernelそのものではない。公開Compilerへ降ろすのは、入力から観測可能な構造、未固定、監査要求、Gate入力要求、Failure Signature候補、次観測候補までである。HDS本体の内部Gate判定アルゴリズム、原理の最終選別、Commit、世界全体の最終更新則は公開Compilerへ複製しない。

基底・規定言語は日本語とする。多言語は外部Data、API、原資料、検索表層等の実務上やむを得ない境界だけに許可する。

---

## 1. v1からの更新理由

v1は次を成立させた。

- 座標固定と未固定座標
- 動態、暗黙知、論証の検出
- 原理探索入力
- 不可能性、反論、証拠、投影、可逆性、時間、資源等の監査要求
- 留保、暫定性、最終採否委譲
- R / K / effortから監査metaを隔離する境界

ただしv1では、重要な情報の一部が「検出した」という平坦な記録に留まっていた。

v1.1では次へ進める。

```text
検出
→ 構造Record
→ Failure Signature候補
→ Checklist
→ Gate入力対応
→ 次観測/R probe
→ 結果帰還時のCognitiveWorld再解釈要求
```

Compilerを判断器へ変えるのではない。**判断側が必要とする構造と観測要求を、より高純度に準備するFront-End**へ進める。

---

## 2. 主要追加責任

### 2.1 状態遷移graph

動態を単語フラグへ縮約しない。

```text
StateNode
TransitionEdge
  source
  target
  condition
  action
  reversible
  rollback_target
```

明示された端点だけを固定する。端点を一意に決められない遷移は推測せずResidualへ送る。

対象となる例：

- 初期状態
- 条件分岐
- 状態遷移
- 更新
- 停止
- feedback
- rollback

状態遷移graphは、時間帰属・機構候補・反実仮想・可逆性監査へ接続できる構造を作る。

### 2.2 暗黙知構造Record

定義・前提・射程・不確実性を単なるラベルで終わらせない。

```text
TacitRecord
  type
  subject
  content
  classification
  valid_scope
  uncertainty
  provenance
  provisionality
  reopen_condition
```

特に定義は `定義対象 → 定義内容` の関係としてHDS-IRへ射影する。

前提・射程・不確実性は、入力から明示的に観測できた範囲だけを記録する。暗黙前提そのものをCompilerが自由生成してはならない。

### 2.3 Failure Signature候補

HDS正本のFailure Signature Bankを、公開Compilerでは**候補生成契約**として用いる。

```text
FailureSignatureCandidate := {
  failure_class,
  symptom,
  structural_cause,
  trigger,
  affected_scope,
  unaffected_scope,
  violated_assumption,
  recovery,
  next_probe_axis,
  reusable_check,
  recurrence_count,
  status
}
```

CompilerはFailure Signatureを確定正本化しない。単一入力から構造原因を観測できる場合は `PROBATION` 候補を生成する。

例：

- 座標未固定
- Closure不全
- 未解参照
- 状態遷移端点不全
- semantic loss

### 2.4 Checklist Generator

Failure Signature候補と監査要求を次へ変換する。

```text
failure_signature / audit_requirement
→ audit_question
→ required_evidence
→ gate_mapping
→ stop_or_recovery_rule
→ next_run_check
```

Checklistは永久固定しない。現行Compiler版における再利用可能なProjectionである。

### 2.5 Gate入力対応

公開CompilerはHDS Gate Stackの内部判定を実装しない。

代わりに監査要求をGate IDへ対応付ける。

主要対応：

- 座標固定要求 → G00
- Open Term → G01
- Closure → G02
- 不可能性 → G03
- 反論対称性 → G04
- 反論強度 → G05
- Evidence → G06
- 論証 → G07 / G08
- Projection → G09 / G15 / G18 / G19
- 可逆性 → G10
- Temporal Attribution → G11 / G24
- Resource / precision → G12 / G21
- Principle Discovery → G13
- Retention / Whole-Field Return → G17 / G20
- Total Provisionality / Version Local Identity → G23 / G25
- Self-Application → G26
- 最終採否委譲 → G27

この対応は**routing contract**であり、Gate Resultではない。

### 2.6 監査R probe

主検索を監査語で汚さない。

通常のR queryは従来どおり対象・関係・状態・条件・候補差分を優先する。

主検索で必要な証拠を取得できない場合のみ、Compilerが生成したChecklistから監査probeを追加できる。

例：

```text
G03 → counterexample / failure conditions
G04/G05 → alternative explanation
G06 → evidence
G13 → mechanism / boundary conditions
```

`監査.R_query` はCompiler metaとして保持するため、通常の構造query生成やK factへ直接混入させない。R fallback側が明示的に読み取る。

### 2.7 CognitiveWorld差分

HDS履歴が与えられた場合、現行CognitiveWorldを前回世界へ上書きしない。

```text
previous_cognitive_world
current_cognitive_world
added_coordinates
removed_coordinates
changed_relations
retrospective_reinterpretation_requests
old_world_retained = true
```

座標の消失は「旧座標が存在しなかった」ことを意味しない。旧Projectionを保持したまま、現在から見た再解釈要求を追加する。

---

## 3. R性能との接続

v1.1の狙いは監査文書を増やすことではない。

```text
問い/Data
→ 高純度Compiler
→ 状態・定義・前提・射程・不確実性の構造化
→ 未閉包/Faultの構造原因
→ 必要証拠の明示
→ 主R
→ 必要時だけ監査R probe
→ Data再Compiler
→ K/J
```

主検索が十分なら監査probeを追加しない。

この非対称性により、通常問題の検索純度を落とさず、0-hit / 未閉包 / 反証不足時だけ「次に何を探すべきか」をHDS構造から生成する。

---

## 4. 保持契約

v1.1では次を保持する。

- 全座標
- 全関係
- 不確実性
- Residual
- provenance
- 旧解釈
- 時間履歴
- CognitiveWorld履歴
- 帰還経路
- Failure Signature候補の由来
- Checklistの由来

不可逆pruningをCompiler適合動作にしない。

資源不足時は、保持できない情報を無言で削除して「完了」としない。Runtime側で必要ならHOLD / SUSPEND / OUT_OF_SCOPEへ接続できる情報を残す。

---

## 5. HDS本体との非公開境界

公開する：

- 入力から観測した座標・関係
- 未固定とResidual
- 状態遷移graph
- 暗黙知Record
- 監査要求
- Gate routing
- Failure Signature候補
- Checklist候補
- 次観測/R probe候補
- CognitiveWorld差分
- 暫定性・再開放条件

公開Compilerへ含めない：

- HDS Native
- HDS本体の上流導出規則
- Gate内部の最終判定アルゴリズム
- PrincipleStateの最終昇格・降格ロジック
- Commitの最終採否ロジック
- Framework Kernelの正本更新権限
- Native全体の再構成

Compilerの `G03` 等は「このGateに必要な情報を準備する」という意味であり、Gateそのものの複製ではない。

---

## 6. 原理発見境界

v1.1でも次を禁止する。

```text
PatternObserved → automatic Principle
SingleSuccess → automatic Principle
Possible → automatic True
MechanismMentioned → automatic MechanismEstablished
CurrentProjection → WorldItself
```

Compilerが扱う原理段階はFront-End候補である。

`SCOPED_PRINCIPLE` 以上の採用はCompiler責任ではない。

---

## 7. 日本語規定

内部の正式役割名、状態名、仕様、監査語、設計文書は日本語を正本とする。

英語その他の入力では、外部検索・原資料照合で意味を失わないため原表層を保持してよい。内部概念体系の正本を英語へ反転しない。

監査R probeも入力言語を優先し、翻訳精度が保証できない状況で無理に日本語/英語へ変換しない。

---

## 8. 受入条件

v1.1は最低限次を満たす。

1. 明示状態遷移をgraphで保持する。
2. 未固定遷移端点をResidualへ送る。
3. 定義・前提・射程・不確実性を別Recordとして保持する。
4. Failure Signature候補を生成し、確定扱いしない。
5. Failure Signature / audit requirementからChecklistを生成する。
6. Checklistにrequired evidence、Gate mapping、stop/recovery、next probeを持たせる。
7. 不可能性要求をG03へ接続する。
8. 監査R probeはprimary Rへ混入せず、fallbackでのみ利用する。
9. CognitiveWorld履歴を上書きせず、差分と再解釈要求を保持する。
10. 監査metaはK factへ昇格しない。
11. 監査metaだけでeffortを膨らませない。
12. v1の既存挙動を回帰させない。
13. 日本語基底・規定言語を維持する。
14. Compilerが最終採否を行わない。

---

## 9. 非完結宣言

v1.1もHDS Compilerの最終形ではない。

状態遷移、Failure Signature、Checklist、CognitiveWorld差分、Gate mapping、現在のRecord型は、現時点で外部化できた公開Projectionである。

次版では本版自身の失敗をFailure Signature化し、座標生成規則、作用素、監査要求、R probe、保持構造を再開放できなければならない。
