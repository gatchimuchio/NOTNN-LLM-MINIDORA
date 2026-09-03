# MINIDORA 能力Module拡張境界 v1

## 1. 位置づけ

本書は、MINIDORAにおける**能力Module拡張**の責任境界を定める。

2026-09-02のGPQA Diamond controlled replayにより、能力Module接続による能力拡張は設計仮説ではなく実装・実測済みとなった。

したがって以後、次を現行MINIDORAの成立特性として扱う。

> **MINIDORAは、Coreを再学習・再訓練・大型化せず、Core外に分離した能力Moduleを接続することで実効能力を追加できる。**

成立証拠:

- [`../評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md`](../評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [`../評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md`](../評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)

---

## 2. 基本責任分離

```text
Core      = 汎用作用
Data      = 外部化可能
Knowledge = 外部参照可能
Module    = 分離可能な能力
Compute   = 汎用計算
HDS       = 制御
```

能力ModuleはCoreの一部として無条件に内部化しない。

Moduleは、特定の入力条件で追加の作用を提供し、成立条件を満たした場合だけ結果へ寄与する。

```text
入力
 ↓
MINIDORA Core
 ↓
必要な能力が外部Moduleに存在
 ↓
Module発火
 ↓
作用結果
 ↓
通常MINIDORAへ接続
```

---

## 3. 成立済みの拡張形式

2026-09-02に次の形式が実測された。

```text
同一baseline / 同一Core
        │
        ├─ Module OFF → baseline結果
        │
        └─ Module ON
             ├─ Module成立 → Module由来結果
             └─ Module不成立 → baseline結果を完全継承
```

この形式により、能力増加の原因をModule発火へ局所化できる。

### 実測

```text
GPQA Diamond 198問
Module OFF = 8 / 198   (4.04%)
Module ON  = 63 / 198  (31.82%)
Module発火 = 55
改善       = 55
退行       = 0
```

この数値をCore単体性能として扱わない。

この数値の設計上の意味は、**Module接続によって能力差を実際に作れることが確認された**点にある。

---

## 4. Module追加とCore変更の区別

次を混同しない。

```text
Module接続による能力追加
!=
Coreの汎用能力改善
```

Module接続でbenchmark scoreが上がっても、その上昇をCore単体性能へ帰属しない。

一方で、Module由来の差がcontrolled A/Bで確認された場合、その差は**モジュール拡張可能性の成立証拠**として保持する。

---

## 5. 再学習の位置づけ

少なくとも2026-09-02に実証した科学能力群では、能力追加のために次を必要としなかった。

- NN再学習
- Transformer追加学習
- Core全体の再訓練
- 重み更新
- Core大型化

したがってMINIDORAでは、

```text
能力追加 = 再学習
```

を必要条件としない。

能力追加経路として、

```text
Core + Module接続
```

が実装上成立済みである。

---

## 6. Module成立条件

能力Moduleは少なくとも次を満たす。

1. Module自身の責任範囲が明示される。
2. 発火条件が入力から決まる。
3. gold answer・benchmark正答表・問題番号を推論に使わない。
4. Moduleが成立しない場合、勝手な候補選択を行わない。
5. Module不発火時に通常MINIDORAへ透過できる。
6. Module由来の結果を監査可能な理由または作用識別子で追跡できる。
7. Module込み性能をCore単体性能へ混同しない。

---

## 7. 非目標

本書は次を要求しない。

- すべての専門能力をCoreへ統合すること
- benchmarkを100%にすること
- Moduleを増やし続けること
- GPQA専用solverを作ること
- 任意Moduleが自動的に一般化すること

目的はscore最大化ではなく、**能力をCoreから分離したまま追加できる構造を保持すること**である。

---

## 8. 変更禁止境界

ユーザーの明示指示なしに、次を行わない。

- 「専門solverはCore性能ではない」という理由だけで、モジュール拡張成立証拠そのものを削除する。
- Module実証を単なる過去benchmark高得点記録へ縮退させる。
- Module接続経路を「benchmark hack」と一括して消す。
- 成立済みのModule拡張可能性を未実証の将来構想へ戻す。

Core単体性能とModule拡張性能は**分離して両方保持する**。

```text
Core評価系列
+
Module拡張成立系列
```

どちらか一方を残すために、もう一方を削除してはならない。

---

## 9. 正本結論

> **MINIDORAの能力Module拡張経路は成立済みである。**
>
> **能力ModuleをCore外に分離し、必要時に接続することで、Core全体の再学習を行わず実効能力を追加できることがGPQA Diamond上で実測された。**
>
> **この成立事実とCore単体の汎用性能評価は別系列として保持する。**
