# MINIDORA 設計正本ガイド

`設計/` は現行MINIDORA Runtimeの意味境界・責任・受入条件を定める局所正本である。

## 読み順

1. [`02_大規模言語模型成立契約.md`](02_大規模言語模型成立契約.md) — v7→MINIDORA v0.5射影。
2. [`03_日本語命令形P仕様.md`](03_日本語命令形P仕様.md) — 計算P/Data分離。
3. [`25_計算中間表現_実行境界_v1.md`](25_計算中間表現_実行境界_v1.md)
4. [`26_HDS_Compiler_Pipeline_v1_3.md`](26_HDS_Compiler_Pipeline_v1_3.md)
5. [`28_HDS判断主体_MINIDORA出力Gate_v2.md`](28_HDS判断主体_MINIDORA出力Gate_v2.md)
6. [`13_共有言語基底P仕様.md`](13_共有言語基底P仕様.md)
7. [`04_外部参照R仕様.md`](04_外部参照R仕様.md)
8. [`09_公開HDS_Compiler仕様.md`](09_公開HDS_Compiler仕様.md)
9. [`05_完成判定関門.md`](05_完成判定関門.md)

番号は履歴を保持するため振り直さない。

## 上位LLM成立規定

- Repository: https://github.com/gatchimuchio/LLM-Constitutive-Specification
- 版: `2026-08-28-成立規定-7`
- 参照commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`

## 現行構造

```text
MINIDORA v0.5
├─ 厳密LM核      : 言語確率法則.py
├─ 能力模型核    : 模型.py / 模型_v05.py
├─ 計算実行器
├─ HDS Compiler
└─ 後段HDS Gate
```

厳密LM核と能力模型核を同一視しない。

## knowledge choice

既存の正式経路は能力側で維持する。

```text
自然言語 / Data
→ HDS Compiler
→ MINIDORA能力模型核
→ MINIDORA出力
→ HDS判断主体
```

HOLD / REJECT後は差し戻さない。

## 変更規則

- 候補scoreを厳密LM確率へ変換しない。
- GPQAをLM成立証拠へしない。
- 厳密LM成立からLargeを自動導出しない。
- HDS型を厳密LM核へ逆流させない。
- Legacy評価・構文化を現行正本へ無言復帰させない。
- 設計変更時は実装・試験・README・評価解釈を同期する。
