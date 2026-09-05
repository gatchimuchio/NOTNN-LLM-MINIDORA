# MINIDORA Core freeze candidate — 2026-09-05

状態: 凍結前整合化候補  
基準系列: 2026-09-01 最小汎用Core + HDS異常時安全弁

## 基準履歴

- 旧測定source: `06c0d24f0ce3203ac20d9b85b836fe184f29f49b` — 23 / 198
- 後続測定source: `061d81244058703c1b28ac33191ced83d7381be3` — 24 / 198
- clean record point: `b1fd13ac3ff8bee01c4e74e6f62a9e827f00d4c0`

24点を採る理由は1点高いからではない。23以後の汎用Core改善を含み、同じ責任境界のまま全198問を完走した後続履歴点だからである。23→24の差分はlive retrievalが固定されていないため因果性能差とは扱わない。

## Active Core

```text
HDS Compiler
→ 標準R
→ formal MINIDORA能力Core
→ 正常閉包なら完全透過
→ 未閉包時だけHDS安全弁
   ├ REFERENCE
   └ EXISTING_COMPUTE_EXECUTOR
→ formal Coreへ復帰
```

HDSはMINIDORAの構成制御である。HDS非介入値は診断ablationであり、別製品Coreを意味しない。

## 今回の整合化

- product runtimeとformal benchmarkの選択入口を同一系列へ戻す。
- 統一V3 / adaptive arbitration / final J wrapperは削除せず実験資産へ隔離する。
- K3/GLM由来の有効作用のうち、Core境界を壊さない「局所観測view」をformal Coreの未閉包時だけ回収する。
- 既存APPROVEは完全透過し、SUSPENDだけを追加閉包対象とする。
- benchmark固有規則、gold、qid、専門solverをCoreへ追加しない。

## Freeze gate

凍結には最低限次を要求する。

1. repository consistency / 日本語基底 / compileall / unittest / CLI smoke PASS
2. active runtimeから統一V3/J/adaptive経路へ推移的に到達しない
3. 24系の既存APPROVE完全透過
4. specialist action = 0 のCore測定
5. GPQA Diamond live 198問で24点未満へ退行しない
6. 可能なら25点以上を観測し、性能向上を別途固定Reference replayでも追認する

Core凍結後の新しい専門能力はCapability Moduleへ追加する。
