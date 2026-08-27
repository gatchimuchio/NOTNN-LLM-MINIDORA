# MINIDORA 参照正本

## 1. 論理上位契約

MINIDORAの現行上位正本は次である。

- Repository: [gatchimuchio/LLM-Constitutive-Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)
- 版: `2026-08-28-成立規定-7`
- 参照commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`
- 日本語正本: `規定/02_大規模言語模型成立.md`

実装上の参照定数は `src/minidora/規定参照.py` を正とする。

## 2. v7のMINIDORA射影

v7は厳密LMを完全言語状態上の整合した確率法則として扱い、能力・Large・現代LLM呼称と分離する。

MINIDORA v0.5では次を対応させる。

- `src/minidora/言語確率法則.py` — 非ニューラル厳密LM核。
- `src/minidora/模型_v05.py` — v0.4能力模型 + v0.5厳密LM + v7参照の統合facade。
- `src/minidora/模型.py` — v0.4由来の候補・関係評価実装。能力核互換実装として保持。
- `src/minidora/runtime.py` — `言語模型核` と `能力模型核` を分離して統合。

旧 `模型.py` 内のv3参照定数はv0.4互換履歴であり、現行正本参照には使用しない。

## 3. 能力観測基盤

K3、Llama系、その他LLMの構文化は、推論・状態操作等の能力観測に利用する。これらの構造を厳密LM一般の必須部品へ昇格しない。

## 4. HDS

前段HDS Compilerは入力構文化、能力模型核は候補・証拠評価、後段HDSはMINIDORA能力出力の採否を担う。

```text
HDS Compiler
→ MINIDORA能力模型核
→ MINIDORA出力
→ HDS判断主体
```

この経路は能力/knowledge choiceであり、厳密LM法則そのものではない。

## 5. 更新規則

外部正本のmain更新へ自動追従しない。

1. 新版・commitを確認する。
2. サンドボックスで意味影響を監査する。
3. 局所契約・実装・試験を更新する。
4. CIまで通した完成差分だけmainへ還元する。

下流MINIDORAに合わせて上流規定を曲げない。
