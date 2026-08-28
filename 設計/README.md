# MINIDORA 設計正本ガイド

`設計/` は現行MINIDORA実行系の意味境界・責任・受入条件を定める局所正本である。

## 最上位理論・言語規定

本プロジェクトの最上位理論正本は `https://github.com/gatchimuchio/cognitive-engineering-foundations` とする。

- 現行参照commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- 規定言語: 日本語
- 原則: 日本語で理論生成・定義・構造化・監査・改訂を行い、実務上必要な場合だけ多言語を例外使用する。

MINIDORA側では [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md) を局所射影正本とする。

## 読み順

1. [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md)
2. [`02_大規模言語模型成立契約.md`](02_大規模言語模型成立契約.md)
3. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md)
4. [`13_共有言語基底P仕様_v0_4.md`](13_共有言語基底P仕様_v0_4.md)
5. [`14_外部言語_日本語意味射影仕様_v0_4.md`](14_外部言語_日本語意味射影仕様_v0_4.md)
6. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md)
7. [`29_HDS_Compiler_作用差分構文化_v1_3.md`](29_HDS_Compiler_作用差分構文化_v1_3.md)
8. [`26_HDS_Compiler_Pipeline_v1_4.md`](26_HDS_Compiler_Pipeline_v1_4.md)
9. [`25_計算中間表現_実行境界_v1.md`](25_計算中間表現_実行境界_v1.md)
10. [`28_HDS判断主体_MINIDORA出力Gate_v2.md`](28_HDS判断主体_MINIDORA出力Gate_v2.md)
11. [`04_外部参照R仕様.md`](04_外部参照R仕様.md)
12. [`05_完成判定関門.md`](05_完成判定関門.md)

旧 `26_HDS_Compiler_Pipeline_v1_3.md`、言語基底v0.3文書等は履歴参照とする。

## 言語模型成立規定

- Repository: `https://github.com/gatchimuchio/LLM-Constitutive-Specification`
- 版: `2026-08-28-成立規定-7`
- 参照commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`

## 現行構造

```text
MINIDORA v0.5
├─ 厳密言語模型核
├─ 能力模型核
├─ 計算実行器
├─ HDS Compiler Architecture v1.3 / Pipeline v1.4
└─ 後段HDS判断門
```

## HDS Compiler境界

Compilerは意味・監査・作用差分構造を生成するが、後続作用を実行せず、最終採否もしない。

```text
意味IR
計算計画
作用差分構造
→ 並列保持
```

## 変更規則

- 日本語を内部意味正本とする。
- 外国語は実務上必要な外部互換境界だけで使う。
- 外部語から内部概念名を決めない。
- 状態差の存在と後続作用の実発火を同一視しない。
- 候補得点を厳密言語模型確率へ変換しない。
- GPQAを言語模型成立証拠へしない。
- HDS型を厳密言語模型核へ逆流させない。
- Legacy評価・構文化・Compiler互換を現行正本へ無言復帰させない。
- 設計変更時は実装・試験・README・評価解釈を同期する。
