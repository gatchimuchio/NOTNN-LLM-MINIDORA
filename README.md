# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定・内部意味正本とする、ニューラルネットワークを必要としない言語模型研究実装である。

現行安定版は **v0.5.0**。  
2026-09-01時点の現行セーブポイントは、**最小汎用LLM core + HDS異常時最小介入**で固定する。

## 現行セーブポイント — 2026-09-01

このセーブポイントでは、MINIDORA本体の汎用性能を測るため、専門領域solverをactive pathから外している。

```text
入力
↓
HDS Compiler
↓
意味IR / 計算計画 / Data
↓
MINIDORA能力模型核
↓
必要な場合だけ
  ├─ REFERENCE
  └─ EXISTING_COMPUTE_EXECUTOR
        ↑
       HDS
  異常時のみ最小介入
↓
通常MINIDORAへ復帰
↓
出力
```

固定境界:

- 専門領域solverはMINIDORA本体の汎用能力に数えない。
- 専門領域は必要なら外部モジュールとして接続する。
- 通常経路で旧K3 helperや専門solverを先回り実行しない。
- HDSは回答を生成せず、候補の勝者を選ばない。
- HDSは正常閉包時に完全透過し、未閉包・競合・観測不足等の異常時だけ既存作用を起動する。
- GPQAや特定benchmarkの正答率を上げるための専用規則をcoreへ追加しない。

詳細: [`docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md)

## 目的

MINIDORA本体は、専門能力を詰め込む箱ではなく、**最小・軽量・単純な一般作用だけで言語模型として成立し、未知入力へ同じ一般作用を適用できる核**を目標とする。

```text
Core = 汎用作用
Data = 外部化可能
専門知識 = 外部参照またはモジュール
専門処理 = 必要時に構文化して接続
HDS = 異常時の最小制御
```

本体へ機能を追加する場合は、少なくとも次を満たす必要がある。

1. benchmark名・分野名・問題名を消しても一般作用として成立する。
2. 既存一般作用の組合せでは表現できない。
3. Dataまたは外部専門モジュールへ分離できない。

## Authority

矛盾時の詳細な優先順位は [`AGENTS.md`](AGENTS.md) を正とする。

最上位理論正本:

- Repository: `https://github.com/gatchimuchio/cognitive-engineering-foundations`
- 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 基底言語・規定言語: 日本語

言語模型成立条件の責任正本:

- Repository: `https://github.com/gatchimuchio/LLM-Constitutive-Specification`
- 版: `2026-08-28-成立規定-8`
- 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

局所規定: [`設計/00_日本語基底規定_v1.md`](設計/00_日本語基底規定_v1.md)

## 現行二核

```text
MINIDORA厳密言語模型
= 完全言語状態上の整合した確率法則

MINIDORA能力模型核
= 候補・証拠・関係評価 / 推論 / 候補選択
```

二つを混同しない。

```text
候補得点
≠ 言語確率

GPQA得点
≠ 言語模型成立

HDS寄与
≠ 言語確率
```

### 厳密言語模型核

`src/minidora/言語確率法則.py` に、非ニューラル・決定論的な有限n-gram / finite-state成立形を実装する。

- `Fraction` による厳密有理数確率。
- NFKC Unicode文字 + `UNK/BOS/EOS`。
- 各接頭辞条件分布を厳密に1へ正規化。
- 系列確率を連鎖則と終端で計算。
- 未観測系列にも正の確率を保持。
- 模型状態を保存・復元可能。
- 同一形成資料なら順序に依存せず同じ状態SHA-256。
- 無作為抽出を必要としない。

言語模型成立の受入は合格済みだが、これは高推論能力やLargeを意味しない。

### 能力模型核

現行標準能力模型核は `src/minidora/能力状態差循環.py`。

観測単位:

```text
状態担体
作用
状態差
後続利用
参照変更
経路変更
計算量変更
再参照
再結合
循環尺度
```

```text
状態の存在
≠ 状態差
≠ 後続利用
≠ 後続作用の実発火
≠ 能力改善
```

局所設計: [`設計/30_MINIDORA能力状態差循環_v1.md`](設計/30_MINIDORA能力状態差循環_v1.md)

## HDS Compiler / 計算実行境界

現行公開HDS Compiler:

```text
Architecture v1.3
Pipeline v1.4
規定言語 = 日本語
基底言語 = 日本語
基底言語コード = ja
```

Compilerは `意味IR / 計算計画 / 作用差分構造` を分離して保持し、後続作用を自動実行せず、候補採否・最終判断もしない。

```text
日本語命令形P
↓
計算中間表現
↓
計算実行境界
↓
計算実行器
```

- [`設計/09_公開HDS_Compiler仕様.md`](設計/09_公開HDS_Compiler仕様.md)
- [`設計/26_HDS_Compiler_Pipeline_v1_4.md`](設計/26_HDS_Compiler_Pipeline_v1_4.md)
- [`設計/29_HDS_Compiler_作用差分構文化_v1_3.md`](設計/29_HDS_Compiler_作用差分構文化_v1_3.md)
- [`設計/25_計算中間表現_実行境界_v1.md`](設計/25_計算中間表現_実行境界_v1.md)

## HDS監督介入

現行active設計は [`設計/32_MINIDORA_HDS監督介入制御_v1.md`](設計/32_MINIDORA_HDS監督介入制御_v1.md)。

標準coreでHDSが外側から起動できる作用は原則として次の二つだけ。

```text
REFERENCE
EXISTING_COMPUTE_EXECUTOR
```

正常閉包時:

```text
HDS介入 = 0
=> 通常MINIDORA結果を完全透過
```

異常時:

```text
未閉包 / 競合 / 観測不足
↓
HDSが既存作用を起動
↓
通常MINIDORAへ復帰
↓
通常再評価
```

旧 `HDS Judgement Subject` 統合案は履歴として保持するが、現行active pathではない。

## 専門モジュール境界

科学・数学・法律・医学・coding等の専門領域は、本体coreへ焼き込まず、必要時に外部モジュールとして接続できる。

リポジトリ内に残る専門solverや旧能力経路は履歴・比較・将来のモジュール資産として保持できるが、**現行標準coreの汎用性能測定には含めない**。

この境界は、専門機能の追加でbenchmark得点だけを上げ、本体の汎用能力と混同することを防ぐために固定する。

## GPQA Diamond — 最小汎用core実測

2026-09-01にGPQA Diamond全198問をcontrolled A/Bで完走した。

| 条件 | 正答 | 全体正答率 | 回答数 | 回答率 |
|---|---:|---:|---:|---:|
| 最小汎用core + HDS異常時最小介入 | 23 / 198 | 11.62% | 124 | 62.63% |
| 同一正式汎用模型核 / HDS非介入 | 19 / 198 | 9.60% | 88 | 44.44% |

差分:

```text
正答差          = +4
正答率差        = +2.02 points
回答数差        = +36
退行case        = 0
専門作用起動    = 0
retrieval空振り = 0
```

測定境界:

- goldはbaseline/current推論後の採点にのみ使用。
- candidate resolutionは正式MINIDORA汎用模型核のみ。
- specialist solverなし。
- supervisory resolverなし。
- HDSによるwinner selectionなし。
- HDSは異常時の安全弁のみ。

詳細: [`評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)

このスコアは現時点の**汎用coreの能力観測値**であり、GPQA専用最適化目標ではない。

## 現在の受入状態

```text
v0.5厳密言語模型核                 = 合格
厳密正規化 / 終端                  = 合格
模型状態保存・復元                  = 合格
二核分離                            = 合格
HDS Compiler Architecture v1.3     = 合格
HDS Compiler Pipeline v1.4         = 合格
能力状態差実発火                    = 合格
HDS正常系完全透過                   = 合格
HDS異常時最小介入                   = 合格
専門solver active path除外          = 合格
GPQA Diamond最小汎用core全198問     = 完走
Large / 現代LLM呼称                = 再監査要
```

```text
厳密言語模型成立
!= 高推論能力
!= GPQA高得点
!= Large
!= 現代LLM呼称適合
```

過去のCI合格を新commitへ無条件継承しない。現行commitごとに再監査する。

## 実行・試験

導入:

```bash
python -m pip install -e .
```

CLI smoke:

```bash
python -m minidora "2+3"
```

全体受入:

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CIはUbuntu / Windows × Python 3.11–3.14を確認する。

GPQA全数測定は重いため、自動push triggerでは実行しない。明示的にGitHub Actionsの `MINIDORA GPQA current measurement` を起動する。

## 文書入口

- [`docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md)
- [`設計/README.md`](設計/README.md)
- [`設計/32_MINIDORA_HDS監督介入制御_v1.md`](設計/32_MINIDORA_HDS監督介入制御_v1.md)
- [`評価/README.md`](評価/README.md)
- [`評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md`](評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)
- [`構文化/README.md`](構文化/README.md)
- [`REFERENCES.md`](REFERENCES.md)

## 履歴境界

旧構文化、旧HDS統合案、旧GPQA測定、旧専門能力実装は削除しない。履歴・比較・将来の外部モジュール候補として保持し、現行active pathへ無言復帰させない。

v0.4の規模測定や過去の`Large`扱いは、v0.5へ自動継承しない。Largeは現行構成で再監査する。

## ライセンス

- **ソースコード、実行系、Compiler、ライブラリ、テスト、ツール、CI・パッケージ設定**: Apache License 2.0 (`Apache-2.0`)
- **仕様、設計、理論、論文、解説、図表、構文化・評価文書、README等**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`)

これはデュアルライセンスではない。適用範囲は `LICENSE`、正式条件は `LICENSE-APACHE-2.0` / `LICENSE-CC-BY-4.0`、帰属は `NOTICE` を参照する。
