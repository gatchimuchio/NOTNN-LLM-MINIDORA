# MINIDORA SAVEPOINT — 2026-09-01 最小汎用LLM core

状態: 確定セーブポイント  
基底言語: 日本語

## 1. 目的

この文書は、専門領域能力を通常経路から分離し、MINIDORA本体の汎用性能だけを測定可能にした時点を再開基準として固定する。

このセーブポイント以後の変更は、ここを比較基準とする。

## 2. 固定した履歴点

- 最小汎用core復帰: `49cf51b94fa2628d1eb944d5a0ee3dccdbce6ac7`
- GPQA測定source: `06c0d24f0ce3203ac20d9b85b836fe184f29f49b`
- GPQA実測記録: `a8dee905b0984f63e9fdffe04a30684d4df00bc1`
- 実測workflow run: `33408451266`

この文書を含む整理commitを、文書導線・評価導線まで含めた再開地点とする。

## 3. Active architecture

```text
入力
↓
HDS Compiler
↓
意味IR / 計算計画 / Data
↓
MINIDORA能力模型核
↓
通常閉包ならそのまま出力
↓ 未閉包・競合・観測不足等
HDS
├─ REFERENCE
└─ EXISTING_COMPUTE_EXECUTOR
↓
通常MINIDORAへ復帰
↓
通常再評価
```

厳密言語模型核は能力模型核と分離して保持する。

## 4. 固定境界

1. MINIDORAはLLMとして扱い、AGI全体設計を本体責務へ持ち込まない。
2. 本体coreは最小・軽量・単純な汎用作用を優先する。
3. 専門領域solverはactive pathへ自動接続しない。
4. 専門領域は必要なら外部モジュール化する。
5. benchmark固有規則・qid・gold・case IDを推論へ利用しない。
6. HDSは回答生成・winner selection・後段採否ラッパーを行わない。
7. HDSは正常閉包時に完全透過する。
8. HDS標準介入作用は `REFERENCE` と `EXISTING_COMPUTE_EXECUTOR` に限定する。
9. 旧K3 helper、旧HDS統合経路、専門solverは履歴・比較資産として保持できるが、現行coreへ無言復帰させない。
10. GPQA得点を言語模型成立証拠へ読み替えない。

## 5. LLM最低成立

現行厳密言語模型核は、完全言語状態空間、持続模型状態、整合した言語確率法則、終端、保存・復元の受入を通している。

責任正本:

- `https://github.com/gatchimuchio/LLM-Constitutive-Specification`
- 版: `2026-08-28-成立規定-8`
- commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

```text
厳密言語模型成立
!= 高推論能力
!= GPQA高得点
!= Large
```

Largeは別途再監査する。

## 6. GPQA Diamond実測

GPQA Diamond 198問 controlled A/B:

```text
current = 最小汎用core + HDS異常時最小介入
        = 23 / 198
        = 11.616161616161616%

baseline = 同一正式汎用模型核 / HDS非介入
         = 19 / 198
         = 9.595959595959595%

差 = +4問 / +2.0202020202020208 points
```

補助値:

```text
current answered = 124
baseline answered = 88
specialist actions = 0
retrieval empty = 0
HDS intervention cases = 108
regressed cases = 0
```

正本実測記録: [`../評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](../評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)

## 7. 再開規則

今後の汎用能力改善は、次を満たす変更を優先する。

- 分野名を消しても成立する。
- 問題固有値を消しても成立する。
- 同じ一般作用が複数領域へ作用する。
- 専門DataはcoreではなくDataまたは外部モジュールへ置ける。
- 変更後にこのセーブポイントとのcontrolled比較ができる。

スコアが上がっても専門機能追加だけならcore改善とは数えない。スコアが一時的に下がっても、汎用境界を守るための分離は退行とは扱わない。

## 8. 検証基準

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

GPQA全数測定は明示実行とし、通常pushでは自動起動しない。
