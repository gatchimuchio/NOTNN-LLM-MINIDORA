# MINIDORA 参照正本

## 1. 最上位理論正本

- Repository: [gatchimuchio/cognitive-engineering-foundations](https://github.com/gatchimuchio/cognitive-engineering-foundations)
- 参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 基底言語・規定言語: 日本語

主参照:
- `00_認知工学とは何か_v0_3_ja_en.md`
- `01_情報工学における言語基底論_v0_3_ja_en.md`
- `PUBLICATION_POLICY.md`

日本語で理論・意味構造・規定を成立させ、実務上やむを得ない外部境界のみ多言語を例外使用する。

## 2. 言語模型成立条件の責任正本

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版: `2026-08-28-成立規定-8`
- 参照commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`
- 日本語正本: `規定/02_大規模言語模型成立.md`
- 能力作用構成: `規定/07_能力作用構成.md`

実装上の参照定数は `src/minidora/規定参照.py` を正とする。

## 3. v8のMINIDORA射影

厳密言語模型:

```text
完全言語状態空間
+ 持続模型状態
→ 整合した言語確率法則
```

能力作用観測:

```text
状態担体 / 作用 / 状態差 / 後続利用 /
参照変更 / 経路変更 / 計算量変更 /
再参照 / 再結合 / 循環尺度
```

両者を混同しない。

対応実装:
- `src/minidora/言語確率法則.py` — 厳密言語模型核。
- `src/minidora/模型.py` — 能力模型核互換実装。
- `src/minidora/hds_compiler_v1.py` — 公開HDS Compiler Architecture v1.3 / Pipeline v1.4。
- `src/minidora/hds_compiler_action_delta.py` — 作用→状態差→後続利用の有限構文化。
- `src/minidora/runtime.py` — 二核統合実行系。

## 4. 日本語基底の局所正本

- `設計/00_日本語基底規定_v1.md`
- `設計/13_共有言語基底P仕様_v0_4.md`
- `設計/14_外部言語_日本語意味射影仕様_v0_4.md`

```text
規定言語 = 日本語
基底言語 = 日本語
内部意味正本 = 日本語
外部言語 = 実務上必要な互換表層
```

`ja / en / zh` は外部互換用識別コード。

## 5. 能力観測基盤

現行K3除外横断構文化:
- `構文化/言語模型横断_日本語基底作用構文化_v3/`

旧v2は履歴として保存する。

## 6. HDS Compiler

```text
Architecture v1.3
Pipeline v1.4
```

Compilerは意味・監査・作用差分構造を生成するが、後続作用を発火せず、候補採否もしない。

```text
意味IR
計算計画
作用差分構造
→ 並列保持
```

## 7. 循環再帰

認知工学正本、言語模型成立規定、構文化、HDS Compiler、MINIDORA、実測は責任を分ける。一方向の固定上流下流ではない。

新観測が既存切り出しを崩す場合、必要な正本・前提まで再開放する。

## 8. 更新規則

1. 新版・commitを確認する。
2. 日本語正本として意味影響を監査する。
3. 局所契約・実装・試験を更新する。
4. 実測差を取得する。
5. 他の正本・構文化・実装へ影響するなら相互に再開放する。
6. CIまで通した完成差分だけmainへ還元する。

実装都合だけを理由に理論正本を曲げない。
