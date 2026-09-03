# MINIDORA 設計正本ガイド

`設計/` は現行MINIDORA実行系の意味境界・責任・受入条件を定める局所正本である。

## 最上位理論・言語規定

- 最上位理論正本: `https://github.com/gatchimuchio/cognitive-engineering-foundations`
- 現行参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 規定言語・基底言語: 日本語
- 多言語: 実務上必要な境界のみ例外

局所規定: [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md)

## 言語模型成立規定

- Repository: `https://github.com/gatchimuchio/LLM-Constitutive-Specification`
- 版: `2026-08-28-成立規定-8`
- 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`
- 能力作用構成: `規定/07_能力作用構成.md`

## 現行セーブポイント — 2026-09-01

現行active設計は、**最小汎用LLM core + HDS異常時最小介入**とする。

```text
MINIDORA v0.5
├─ 厳密言語模型核
├─ 能力状態差模型核
├─ HDS Compiler Architecture v1.3 / Pipeline v1.4
├─ 計算実行器
├─ 外部参照R
└─ HDS監督介入制御
      ├─ REFERENCE
      └─ EXISTING_COMPUTE_EXECUTOR
```

HDSは後段の最終採否ラッパーではない。正常閉包時は完全透過し、未閉包・競合・観測不足等の異常時だけ既存作用を起動する。

```text
通常MINIDORA
  ↑      ↓
HDS監督制御
```

HDSへ回答ラベル・候補得点を渡さず、HDS自身が回答生成・winner selectionを行わない。

専門領域solver、旧K3 helper、旧HDS終端・再統合経路は現行標準coreのactive pathへ含めない。必要な専門領域は外部モジュールとして分離する。

セーブポイント記録: [`../docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](../docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md)

## 成立後能力成長 — Module拡張は成立済み

2026-09-02、MINIDORAは**LLMとして成立した後の能力成長方式まで実装・実測済み**となった。

正本として次を固定する。

> **MINIDORAは既にLLMとして成立している。**
>
> **その成立済みCoreを再学習・再訓練・大型化・置換せず、Core外に分離した能力Moduleを追加接続することで、能力を後から増設できる。**
>
> **Module追加は単なる接続機構ではなく、実際の性能向上手段として機能することが外部benchmark上で実測済みである。**
>
> **したがってMINIDORAのシステム能力は、成立時点のCore単体性能へ固定されない。接続するCapability集合を増やすことで継続的に拡張できる。**

GPQA Diamond controlled replayでは、既存科学専門能力群を同一baselineへ接続した結果、次を観測した。

```text
Module OFF = 8 / 198   (4.04%)
Module ON  = 63 / 198  (31.82%)
Module発火 = 55
改善       = 55
退行       = 0
正答差     = +55
```

この実証の意味は「科学Moduleを付けたら点数が上がった」ではない。

```text
成立済みMINIDORA
↓
外部Capabilityを追加
↓
追加能力が発火
↓
実効能力が増える
↓
外部benchmark性能として上昇する
```

という**成立後の能力成長経路そのものが成立した**ことにある。

### 固定有限benchmarkに対する100%到達経路

GPQA Diamondのような固定有限問題集合では、未被覆領域へ正しく作用するModuleを追加し、不発火時の透過性と既存正答を退行させない接続境界を維持する限り、未被覆集合を反復的に縮小できる。

```text
未被覆 U0
↓ Module追加
U1 ⊂ U0
↓ Module追加
U2 ⊂ U1
↓
...
↓
未被覆 = 0
```

したがって、**固定有限benchmarkに限れば、Module被覆を追加し続けることで理論上100%まで到達可能な構成である。**

これは100%実測済みという意味ではない。重要なのは、**100%へ向かう性能向上経路が、Core再学習ではなくCapability Moduleの追加という反復可能な操作として実装上開かれた**ことである。

この値をCore単体性能へ混ぜない。一方で、この差分を単なる過去benchmark記録へ縮退させない。

```text
Core評価系列
!=
Module拡張・成立後能力成長系列
```

詳細:

- [`35_MINIDORA_能力Module拡張境界_v1.md`](35_MINIDORA_能力Module拡張境界_v1.md) — 成立後能力成長方式・Module拡張・固定有限benchmarkの100%到達経路の局所正本。
- [`../評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](../評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md) — 実測根拠。

## 読み順

1. [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md)
2. [`02_大規模言語模型成立契約.md`](02_大規模言語模型成立契約.md)
3. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md)
4. [`13_共有言語基底P仕様_v0_4.md`](13_共有言語基底P仕様_v0_4.md)
5. [`14_外部言語_日本語意味射影仕様_v0_4.md`](14_外部言語_日本語意味射影仕様_v0_4.md)
6. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md)
7. [`29_HDS_Compiler_作用差分構文化_v1_3.md`](29_HDS_Compiler_作用差分構文化_v1_3.md)
8. [`26_HDS_Compiler_Pipeline_v1_4.md`](26_HDS_Compiler_Pipeline_v1_4.md)
9. [`30_MINIDORA能力状態差循環_v1.md`](30_MINIDORA能力状態差循環_v1.md)
10. [`32_MINIDORA_HDS監督介入制御_v1.md`](32_MINIDORA_HDS監督介入制御_v1.md)
11. [`35_MINIDORA_能力Module拡張境界_v1.md`](35_MINIDORA_能力Module拡張境界_v1.md)
12. [`25_計算中間表現_実行境界_v1.md`](25_計算中間表現_実行境界_v1.md)
13. [`04_外部参照R仕様.md`](04_外部参照R仕様.md)
14. [`05_完成判定関門.md`](05_完成判定関門.md)

## HDS Compiler境界

Compilerは意味・監査・作用差分構造を生成するが、後続作用を実行せず、最終採否もしない。

```text
意味IR
計算計画
作用差分構造
→ 並列保持
```

## 能力状態差循環

現行標準能力模型核は [`30_MINIDORA能力状態差循環_v1.md`](30_MINIDORA能力状態差循環_v1.md) を局所正本とする。

状態差がなければ再作用しない。同一参照証拠を段階名だけ変えて再加点しない。

HDS監督制御では、同一Dataの候補集合縮小だけで新しい票を作らず、実観測または作業状態が変化した場合だけ通常MINIDORAの再評価へ進む。

## 能力作用観測単位

v8観測単位:

```text
状態担体 / 作用 / 状態差 / 後続利用 /
参照変更 / 経路変更 / 計算量変更 /
再参照 / 再結合 / 循環尺度
```

Compiler v1.3は作用・状態差・後続利用を構文化し、MINIDORA能力系とHDS監督制御が責任分離して次作用へ接続する。

## Legacy

旧版は削除せず履歴として保持する。

特に次は現行active設計ではない。

- [`28_HDS判断主体_MINIDORA出力Gate_v2.md`](28_HDS判断主体_MINIDORA出力Gate_v2.md)
- [`31_MINIDORA_HDS統合判断主体_v1.md`](31_MINIDORA_HDS統合判断主体_v1.md)
- 旧K3 helper / graph / direct relation / candidate reconcileの通常経路先行実行
- 専門領域solverによる通常経路先行解決

ここでいう「通常経路先行解決をactive coreへ含めない」は、能力Module拡張経路そのものを否定しない。Module拡張・成立後能力成長系列は [`35_MINIDORA_能力Module拡張境界_v1.md`](35_MINIDORA_能力Module拡張境界_v1.md) に従って別責任として保持する。

Legacyを現行正本へ無言復帰させない。

## 変更規則

- 日本語を内部意味正本とする。
- 外国語は実務上必要な外部互換境界だけで使う。
- 状態差の存在と後続作用の実発火を同一視しない。
- 状態差がないのに再作用回数を増やさない。
- 同一証拠を別名で再加点しない。
- 候補得点を厳密言語模型確率へ変換しない。
- GPQAを言語模型成立証拠へしない。
- benchmark固有規則をcoreへ追加しない。
- 専門領域は原則として外部モジュールへ分離する。
- **Core単体評価とModule拡張・成立後能力成長評価を混同しない。**
- **ModuleがCore性能ではないことを理由に、Module拡張成立証拠を削除しない。**
- **成立済みのModule拡張可能性を未実証の将来構想へ戻さない。**
- **Module実証を「科学Moduleでscoreが上がった」だけの説明へ縮退させない。**
- **成立済みMINIDORAの能力上限を、特定時点のCore単体scoreへ固定しない。**
- **固定有限benchmarkに対する100%到達経路の意味を、100%実測の有無だけで削除・否定しない。**
- HDS型を厳密言語模型核へ逆流させない。
- HDSへ回答ラベル・候補得点を渡さない。
- HDSが回答を生成・選択しない。
- 設計変更時は実装・試験・README・評価解釈を同期する。
