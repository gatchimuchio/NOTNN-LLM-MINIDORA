# NOTNN-LLM-MINIDORA — ミニドラ

MINIDORAは、日本語を基底・規定・内部意味正本とする非ニューラルネットワーク型の言語模型研究実装である。

現行版は **v0.5.0**。

## 最上位理論と言語規定

本プロジェクトの最上位理論正本は [`cognitive-engineering-foundations`](https://github.com/gatchimuchio/cognitive-engineering-foundations) とする。

- 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 基底言語・規定言語: 日本語

```text
日本語で対象化・差異化・関係化
→ 日本語で理論・設計・構文化・監査を成立
→ 日本語正本を保持
→ 実務上やむを得ない外部境界のみ多言語を例外使用
```

外部API、規格、固有名、URL、言語コード、国際公開等に必要な外国語・英字は外部互換として認めるが、第二基底・並列正本・内部意味の主語にはしない。

局所規定: [`設計/00_日本語基底規定_v1.md`](設計/00_日本語基底規定_v1.md)

## 言語模型成立条件

責任正本は [`LLM-Constitutive-Specification`](https://github.com/gatchimuchio/LLM-Constitutive-Specification)。

- 版: `2026-08-28-成立規定-8`
- 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

v8の厳密言語模型中核:

```text
完全言語状態空間
+ 持続模型状態
→ 整合した言語確率法則
```

局所条件から完全法則への接続は成立形の監査対象であり、特定のニューラル構造・自己回帰方式を普遍必須にしない。

## v0.5の二核

```text
[厳密言語模型核]
完全言語状態空間
+ 持続模型状態
→ 厳密に正規化された条件分布
→ 連鎖則 + 終端
→ 完全系列確率

[能力模型核]
質問 / 候補 / 資料
→ 関係・証拠・候補差
→ 候補選択
```

候補得点をsoftmax等で確率へ変換して言語模型確率と読み替えない。

## 厳密言語模型核

`src/minidora/言語確率法則.py` に非ニューラル・決定論的な有限n-gram / finite-state成立形を実装する。方式名は外部互換名として保持する。

- Python標準ライブラリのみ。
- `Fraction` による厳密有理数確率。
- NFKC Unicode文字 + `UNK/BOS/EOS`。
- 加算平滑化。
- 各接頭辞条件分布は厳密に1へ正規化。
- 系列確率は連鎖則と終端で計算。
- 全文脈で終端確率に正の下限。
- 模型状態を保存・復元可能。
- 同一形成資料なら順序に依存せず同じSHA-256。
- 無作為抽出なし。

`最小厳密言語模型()` は厳密言語模型法則の最小成立確認だけを担い、能力やLargeを意味しない。

## 能力作用構成

構成定義v8とK3除外横断構文化v3では、能力作用を次へ分別する。

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
状態が存在する
≠ 状態が後続利用される
≠ 後続作用が実発火する
```

これらを厳密言語模型成立条件へ混入しない。

## HDS Compiler

現行公開HDS Compiler:

```text
Architecture v1.3
Pipeline v1.4
規定言語 = 日本語
基底言語 = 日本語
基底言語コード = ja
```

v1.3は状態遷移から、

```text
作用
→ 状態差
→ 後続利用
```

を並列構文化する。後続利用は「後状態が次作用の入力状態条件を満たす」ことだけを意味し、次作用の発火・採用・実行をCompilerが決めない。

Pipeline v1.4は、

```text
意味IR
計算計画
作用差分構造
```

を別フィールドで保持する。作用差分構造を計算Pへ自動降下しない。

- [`設計/09_公開HDS_Compiler仕様.md`](設計/09_公開HDS_Compiler仕様.md)
- [`設計/29_HDS_Compiler_作用差分構文化_v1_3.md`](設計/29_HDS_Compiler_作用差分構文化_v1_3.md)
- [`設計/26_HDS_Compiler_Pipeline_v1_4.md`](設計/26_HDS_Compiler_Pipeline_v1_4.md)

## 日本語基底

現行共有言語基底はv0.4。

```text
規定言語 = 日本語
基底言語 = 日本語
基底言語コード = ja
```

`ja / en / zh` 等は外部互換識別コードであり、内部意味正本ではない。

- [`設計/13_共有言語基底P仕様_v0_4.md`](設計/13_共有言語基底P仕様_v0_4.md)
- [`設計/14_外部言語_日本語意味射影仕様_v0_4.md`](設計/14_外部言語_日本語意味射影仕様_v0_4.md)

## 現行横断構文化

K3を除く10模型の現行横断観測:

- [`構文化/言語模型横断_日本語基底作用構文化_v3/`](構文化/言語模型横断_日本語基底作用構文化_v3/)

旧 `構文化/LLM横断_状態差作用構文化_v2/` は履歴として保持する。

## 能力・Large・呼称

```text
厳密言語模型成立
!= 高推論能力
!= GPQA高得点
!= Large
!= 現代LLM呼称適合
```

`Large`、`LLM`、`GPQA` は外部名称として保持する。

## 現在の受入状態

```text
v0.5厳密言語模型核          = 合格
厳密正規化 / 終端           = 合格
模型状態保存・復元           = 合格
二核分離                     = 合格
日本語基底規定               = 現行v0.4
HDS Compiler作用差分構文化   = Architecture v1.3
HDS Compiler責任分離         = Pipeline v1.4
GPQA / 推論能力              = 別評価
Large / 現代LLM呼称         = 再監査要
```

過去のCI合格を新commitへ無条件継承せず、正本更新ごとにUbuntu / Windows × Python 3.11–3.14を確認する。

## 試験

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

## 文書入口

- [`設計/README.md`](設計/README.md)
- [`設計/00_日本語基底規定_v1.md`](設計/00_日本語基底規定_v1.md)
- [`REFERENCES.md`](REFERENCES.md)
- [`構文化/README.md`](構文化/README.md)
- [`評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md`](評価/MINIDORA_v0_5_厳密LM受入_2026-08-28.md)

## ライセンス

- **ソースコード、実行系、Compiler、ライブラリ、テスト、ツール、CI・パッケージ設定**: Apache License 2.0 (`Apache-2.0`)
- **仕様、設計、理論、論文、解説、図表、構文化・評価文書、README等**: Creative Commons Attribution 4.0 International (`CC-BY-4.0`)

これはデュアルライセンスではない。適用範囲は `LICENSE`、正式条件は `LICENSE-APACHE-2.0` / `LICENSE-CC-BY-4.0`、帰属は `NOTICE` を参照する。
