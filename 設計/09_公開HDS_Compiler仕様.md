# 公開HDS Compiler仕様

## 1. 位置づけ

`src/minidora/hds_compiler_v1.py` をMINIDORAの公開標準HDS Compiler正本とする。`src/minidora/hds_compiler.py` は基礎意味Projection互換層として保持する。

公開対象は自然言語→HDS意味IRの有限Projection、作用差分構文化、公開Failure Signature再利用契約、計算降下境界である。HDS本体の非公開導出規則・最終判断機構ではない。

現行版:

- Meaning/Audit Architecture: `v1.3`
- Pipeline: `v1.4`

## 2. 言語

- 規定言語: 日本語
- 基底言語: 日本語
- 基底言語コード: `ja`
- 多言語: 外部API、規格、Data、原文照合等で実務上必要な表層のみ

外国語表層を内部作用名・状態名・関係名の正本へしない。

## 3. 意味Compiler責任

入力から観測できる範囲で次を射影する。

1. 原文 / 正規化文 / 入力言語コード
2. 対象 / 主題 / 関係 / 作用 / 方向
3. 状態 / 属性 / 条件 / 文脈 / 目的
4. 否定 / 反転 / 数量 / 単位 / 共参照 / 残差
5. 状態遷移図
6. 定義 / 前提 / 射程 / 不確実性
7. Failure Signature候補 / Checklist / 監査参照候補
8. 認知世界差分 / 旧世界保持 / 再解釈要求
9. **作用差分構造: 作用 / 状態差 / 後続利用 / 未閉包**

未知情報を補完して確定しない。

## 4. Architecture v1.3

v1.2までのFailure Signature帰還を維持し、状態遷移図から作用差分構造を追加生成する。

```text
作用A
→ 前状態X / 後状態Y
→ 状態差Δ(X,Y)
→ Yを入力状態に持つ別作用B
→ 後続利用候補
```

後続利用はBの発火・採用・実行を意味しない。追加条件は未評価のまま保持する。

詳細は [`29_HDS_Compiler_作用差分構文化_v1_3.md`](29_HDS_Compiler_作用差分構文化_v1_3.md)。

## 5. Pipeline v1.4

`意味コンパイル()` を意味正本入口とする。

```text
意味HDS-IR
計算計画
作用差分構造
   ↓ 別フィールドで並列保持
HDSコンパイル束
```

計算降下は作用差分構造を自動実行命令へ変えない。

詳細は [`26_HDS_Compiler_Pipeline_v1_4.md`](26_HDS_Compiler_Pipeline_v1_4.md)。

## 6. Architecture履歴

- v1: `10_HDS_Compiler_Architecture_v1.md`
- v1.1: `11_HDS_Compiler_Architecture_v1_1.md`
- v1.2: `12_HDS_Compiler_Architecture_v1_2.md`
- v1.3: 本書 + `29_HDS_Compiler_作用差分構文化_v1_3.md`

旧版は履歴として保持する。

## 7. 選択問題・外部参照

全候補を対称に保持し、正解ラベル・ベンチ固有規則をCompilerへ入れない。外部参照の検索焦点・対象・関係・条件を意味IRから生成する。

## 8. Failure Signature帰還

Bankは明示注入し、通常コンパイルの隠れ状態にしない。改善候補は自動適用しない。

## 9. 非責任

公開Compilerは次を行わない。

- HDS本体の最終判断
- 状態差から後続作用の自動発火
- 候補採否
- 記憶正本更新
- 外界作用
- Failure Signature改善候補の自己承認
- 未知事実の捏造
- 意味IRと計算Pの同一化

## 10. 改善方向

次段は作用差分構造を能力実行系へ接続し、状態差が実際に後続作用集合・参照・候補状態を変えるかを制御実験で確認する。Compiler段階では発火数を目的化しない。
