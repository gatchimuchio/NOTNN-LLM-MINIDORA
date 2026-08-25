# MINIDORA v0.4 再構成受入記録

日付: 2026-08-26

状態: **構造受入 PASS**

## 1. 対象

MINIDORA v0.4を、次の上流正本へ一方向に適用して再構成した結果を固定する。

- 上流Repository: https://github.com/gatchimuchio/LLM-Constitutive-Specification
- 上流版: `2026-08-26-成立規定-2`
- MINIDORA参照commit: `e94a13ba32208aabd9dc88b6de320872963725be`
- 検証対象MINIDORA commit: `89b88f727d289b1f1b66feb609374feeee6130c6`
- package version: `0.4.0`

MINIDORAを上流成立規定の証人として使わず、上流規定をMINIDORA側へ一方向に適用した。

## 2. 再構成結果

旧 `Layer0` として扱っていた汎用命令インタプリタを、実際の作用に合わせて **計算実行器** へ再分類した。

LLM模型中核は新たに次へ分離した。

```text
対象言語状態
→ 言語対応
→ 文脈付き内部状態
→ 再利用可能な模型側関係
→ 成立差
```

現行実装:

- `src/minidora/模型.py` — LLM模型中核
- `src/minidora/計算実行器.py` — 汎用計算実行
- `src/minidora/layer0.py` — 旧公開API互換窓口
- `src/minidora/runtime.py` — v0.4統合Runtime
- `src/minidora/runtime_v03.py` — v0.3運用経路の履歴互換
- `src/minidora/旧_layer0_v03.py` — v0.3命令器の履歴実装

## 3. HDS境界

今回の再構成ではHDS Compiler本体を先回り改造していない。

現行境界:

```text
HDS-IR != LLM模型中核
HDS-IR != 成立差
HDS-IR != Compute IR
HDS Compiler != LLM成立条件
```

HDS-IRは意味Projection・運用入力・監査履歴として保持する。

次段でCompute IR / ABIを確定し、その後にHDS semantic IRからCompute IRへのloweringとHDS Compiler側の責任を再設計する。

## 4. v0.3履歴

次を削除・改変せず保持した。

- `PROTOTYPE COMPLETE — 2026-08-22`
- 過去GPQA実測
- K3横断構文化・相対化資産
- HDS Compiler既存実装・試験
- v0.3 Runtime
- 旧Layer-0契約

ただし、v0.3の性能値をv0.4模型核の大規模性証拠へ自動転用しない。

## 5. CI受入

GitHub Actions:

- workflow: `MINIDORA 再構築CI`
- run id: `32883059625`
- run number: `480`
- head: `89b88f727d289b1f1b66feb609374feeee6130c6`
- conclusion: **success**

検証行列:

| OS | Python | 結果 |
|---|---:|---|
| Ubuntu | 3.11 | PASS |
| Ubuntu | 3.12 | PASS |
| Ubuntu | 3.13 | PASS |
| Ubuntu | 3.14 | PASS |
| Windows | 3.11 | PASS |
| Windows | 3.12 | PASS |
| Windows | 3.13 | PASS |
| Windows | 3.14 | PASS |

各jobで次を通過した。

1. package install
2. repository consistency audit
3. compileall
4. unit tests
5. `python -m minidora "2+3"`
6. `minidora "2+3"`

## 6. 試験結果

代表jobで **329 tests / OK**。

v0.4新規模型核試験:

- 文脈差が成立差へ到達する — PASS
- 同じ関係を複数文脈へ再利用する — PASS
- 根拠差なしでは一候補へ勝手に確定しない — PASS
- 明示したプログラム言語体系を扱える — PASS
- Runtimeから模型核入口へ到達できる — PASS

旧運用回帰:

- K3相当構造試験 `47 / 47` — PASS
- 公開HDS Compiler v1.2試験 — PASS
- 主体主幹 — PASS
- 外部参照R — PASS
- HDS-IR replay / K / J経路 — PASS
- CLI smoke — `5です。`

## 7. 受入判定

### 合格

- 上流LLM成立規定の参照版・commit固定
- LLM模型中核と計算実行器の分離
- 模型核のHDS / Layer0非依存
- 言語対応・文脈付き内部状態・模型側関係・成立差の実装
- 根拠なし確定禁止
- 自然言語以外の明示言語体系を扱える境界
- v0.3運用経路との後方互換
- Linux / Windows全CI行列

### 未完

- v0.4の状態域規模再測定
- v0.4の関係域規模再測定
- v0.4の共有適用規模再測定
- Compute IR / ABI
- HDS semantic IR → Compute IR lowering
- HDS Compilerの新境界への再設計

## 8. 結論

**MINIDORA v0.4の構造再構成は受入PASS。**

これは、上流「大規模言語模型成立規定」に沿った模型核・運用境界の再構成が実装・回帰試験・Linux/Windows CIで閉じたことを意味する。

一方で、**v0.4が「大規模」であることの再測定は未完**である。旧GPQA等を無言転用せず、別評価として扱う。

次の設計工程は **Compute IR / ABIの確定** とする。HDS Compiler更新はその後に行う。
