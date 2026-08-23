# 公開HDS Compiler仕様 v0.2

## 1. 位置づけ

`src/minidora/hds_compiler_v1.py` をMINIDORAの公開標準HDS Compiler正本とする。`src/minidora/hds_compiler.py` は既存の基礎意味Projection互換層として保持する。

このCompilerはフル公開対象である。性能改善、試験、第三者監査、派生実装を許容する。

ただし公開対象は **自然言語→HDS-IRの有限Projection実装と、その公開Failure Signature再利用契約** であり、HDS本体の上流理論・導出規則・非公開解析正本ではない。

## 2. 言語

- 基底・規定言語: 日本語
- 内部役割名・状態名・関係名・制御語: 日本語
- 多言語: 外部API、規格、データ、ベンチマーク、互換性、原文照合など実務上必要な表層のみ
- 外部表層語は検索・出典追跡に必要な範囲で原言語保持

## 3. Compiler責任

入力から観測できる範囲で次をHDS-IRまたは公開Front-End成果へ射影する。

1. 原文 / 正規化文
2. 入力言語
3. 対象 / 主題
4. 関係 / 作用 / 方向
5. 状態 / 属性
6. 条件 / 文脈
7. 目的 / 検索焦点
8. 否定 / 反転選択
9. 数量 / 単位 / 比較
10. 共参照と未解残差
11. Projection履歴
12. 状態遷移graph
13. 定義 / 前提 / 射程 / 不確実性の構造Record
14. Failure Signature候補
15. Checklist / Gate routing / fallback監査R probe
16. CognitiveWorld差分 / 旧世界保持 / 再解釈要求
17. 明示Failure Signature Bankへの帰還
18. 反復SignatureからのCompiler改善候補生成

未知情報を補完して確定しない。

Architecture履歴は以下へ保持する。

- v1: [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md)
- v1.1: [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md)
- 現行v1.2: [`12_HDS_Compiler_Architecture_v1_2.md`](12_HDS_Compiler_Architecture_v1_2.md)

## 4. R性能との関係

MINIDORAではRの検索品質をCompiler出力の品質から切り離さない。

```text
入力
↓
公開HDS Compiler
↓
検索焦点・対象・関係・状態・条件
↓
R query
↓
Data取得
↓
同じ公開HDS Compiler
↓
Data HDS-IR
↓
K / J
```

性能改善では、検索件数を闇雲に増やす前にCompilerの役割分別・関係方向・条件・不足情報の純度を上げる。

v1.1以降の監査R probeはprimary queryへ常時混入させず、主検索不足時のfallbackに限定する。

## 5. 選択問題

選択問題では次を必須とする。

- 全候補を対称にHDS-IRへ保持する
- 正解ラベルをCompilerへ渡さない
- ベンチ固有規則をCompilerへ追加しない
- 否定・例外・least/most等の選択意図を検索前に保持する
- 候補内容はDataでありPへ埋め込まない

## 6. 関係方向

`A causes B` と `B causes A` を同一視しない。

受動表現など表層順序が逆でも、意味方向が確定できる場合は同一の有向HDS関係へ正規化する。

比較記号・矢印・因果・増減・阻害・活性化・要求・包含等は方向を保持する。

## 7. 数量

数量と単位を独立座標へ分離し、`数量単位` 関係で接続する。

科学記数法、符号、分数、比較演算子等を表層雑音として落とさない。

## 8. 残差

次を推測で閉じない。

- 参照先不明の指示語
- 意味同一性未確定
- 未観測値
- 矛盾
- 条件不足
- 状態遷移端点未固定
- 有限Projectionによる意味損失

実行を阻害しない未分別情報は残差として保持し、必要に応じて次turnやRで再開放する。

## 9. Failure Signature帰還

Failure Signature Bankはglobal暗黙状態にしない。

通常の `コンパイル()` / `詳細コンパイル()` はBankを参照せず決定論的である。Failure Signatureを蓄積する場合だけ、呼出側が明示BankとRun参照を渡す。

同一Runの重複観測を二重計上しない。独立Runで同一構造原因が反復した場合にのみSignatureをACTIVEへ昇格できる。

共通起動条件と局所起動条件を分離し、原症状・局所条件・由来候補ID・Run履歴を削除しない。

## 10. 改善候補

ACTIVE Failure Signatureから公開Compilerの改善候補を生成できる。

候補対象は、座標生成規則、作用素集合、保持構造、Domain Adapter、Identity Lock、Framework Projection、Checklist等とする。

改善候補は自動適用しない。反復確認、既存正例・負例・境界例への回帰、HDS本体または権限を持つ上位判断主体の採否を要求する。

## 11. 非責任

公開Compilerは以下を主張しない。

- HDS本体そのもの
- HDSの全理論の完全実装
- HDS本体の最終Gate判定アルゴリズム
- PrincipleStateの最終昇格規則
- Failure Signature改善候補の自動採用
- Compiler自身の自動自己改変
- 全自然言語の完全解析
- 全言語への対応
- ベンチ正答を知ること
- 外部Dataなしで未知事実を生成すること

## 12. 改善優先順位

1. 検索焦点 / 不足情報
2. 対象・作用・対象先の分離
3. 関係方向
4. 否定・反転・例外
5. 条件・範囲・時点
6. 数量・単位・数式
7. 共参照
8. Data HDS-IRの意味接続率
9. R queryの構造利用率
10. K/Jへ到達する独立証拠率
11. Failure Signature反復から得られる抽出規則改善候補
12. 回帰確認済み改善候補の選択的採用

## 13. 不足スロット

関係構造が高信頼に確定でき、始点または終点だけが疑問語で未観測の場合、疑問語を実体として確定しない。未知端点を `未観測` として保持し、既知端点・関係種別・検索述語・条件と結び付ける。

選択問題のR queryでは各候補を未観測端点へ差し込み、関係方向と条件を保持した候補別queryを生成する。関係構造を一意に決められない疑問文では不足スロットを推測生成せず、従来の焦点・構造queryへ縮退する。
