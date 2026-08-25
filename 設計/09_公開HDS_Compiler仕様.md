# 公開HDS Compiler仕様

## 1. 位置づけ

`src/minidora/hds_compiler_v1.py` をMINIDORAの公開標準HDS Compiler正本とする。`src/minidora/hds_compiler.py` は基礎意味Projection互換層として保持する。

公開Compilerはフル公開対象である。ただし公開対象は **自然言語→HDS意味IRの有限Projection、公開Failure Signature再利用契約、計算降下境界** であり、HDS本体の上流理論・導出規則・非公開解析正本ではない。

現行版は次の二軸で管理する。

- Meaning/Audit Architecture: `v1.2`
- Pipeline: `v1.3`

## 2. 言語

- 基底・規定言語: 日本語
- 内部役割名・状態名・関係名・制御語: 日本語
- 多言語: 外部API、規格、データ、ベンチマーク、互換性、原文照合など実務上必要な表層のみ
- 外部表層語は検索・出典追跡に必要な範囲で原言語保持

## 3. 意味Compiler責任

入力から観測できる範囲で次を意味HDS-IRまたは公開Front-End成果へ射影する。

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

## 4. Pipeline v1.3

`意味コンパイル()` を意味正本入口とする。

```text
自然言語
↓
意味コンパイル
↓
意味HDS-IR（P非内包）
├─ R / K / J / 監査
└─ 計算計画
   ↓
 計算降下
   ↓
 計算中間表現 v1
```

- 意味IRへ `手順` と計算初期状態を入れない。
- `コンパイル束()` で意味IRと計算計画を別保持する。
- `計算降下()` は形成済み束を受け、自然言語を再解析しない。
- 旧 `コンパイル()` は既存Runtime向け互換橋に限定し、最外周でのみPを再付与する。
- 独立Data / 候補コンパイルは意味入口を優先しPを混入しない。

詳細は [`26_HDS_Compiler_Pipeline_v1_3.md`](26_HDS_Compiler_Pipeline_v1_3.md) を正本とする。

## 5. Architecture履歴

- v1: [`10_HDS_Compiler_Architecture_v1.md`](10_HDS_Compiler_Architecture_v1.md)
- v1.1: [`11_HDS_Compiler_Architecture_v1_1.md`](11_HDS_Compiler_Architecture_v1_1.md)
- 現行Meaning/Audit v1.2: [`12_HDS_Compiler_Architecture_v1_2.md`](12_HDS_Compiler_Architecture_v1_2.md)

Pipeline v1.3はv1.2意味・監査能力を置き換えず、責任境界だけを更新する。

## 6. R性能との関係

MINIDORAではRの検索品質をCompiler出力の品質から切り離さない。

```text
入力
↓
意味HDS-IR
↓
検索焦点・対象・関係・状態・条件
↓
R query
↓
Data取得
↓
独立意味コンパイル
↓
Data HDS-IR
↓
K / J
```

検索件数を増やす前に役割分別・関係方向・条件・不足情報の純度を上げる。

## 7. 選択問題

- 全候補を対称にHDS-IRへ保持する。
- 正解ラベルをCompilerへ渡さない。
- ベンチ固有規則をCompilerへ追加しない。
- 否定・例外・least/most等の選択意図を検索前に保持する。
- 候補内容はDataでありPへ埋め込まない。

## 8. 関係・数量・残差

`A causes B` と `B causes A` を同一視しない。受動表現でも意味方向が確定できる場合は同一の有向関係へ正規化する。

数量と単位を独立座標へ分離し、比較記号・符号・分数・科学記数法を落とさない。

参照先不明、意味同一性未確定、未観測値、矛盾、条件不足、状態遷移端点未固定、有限Projectionによる意味損失は推測で閉じない。

## 9. Failure Signature帰還

Failure Signature Bankはglobal暗黙状態にしない。通常の意味コンパイルはBankを参照せず決定論的である。蓄積時だけ呼出側が明示BankとRun参照を渡す。

改善候補は自動適用しない。反復確認、既存正例・負例・境界例への回帰、権限を持つ上位判断主体の採否を要求する。

## 10. 非責任

公開Compilerは以下を主張しない。

- HDS本体そのもの
- HDSの全理論の完全実装
- HDS本体の最終Gate判定アルゴリズム
- Failure Signature改善候補の自動採用
- Compiler自身の自動自己改変
- 全自然言語の完全解析
- 全言語への対応
- ベンチ正答を知ること
- 外部Dataなしで未知事実を生成すること
- 意味HDS-IRと計算Pの同一性

## 11. 改善優先順位

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
