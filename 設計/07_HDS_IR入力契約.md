# HDS-IR入力契約 v0.4境界

## 1. 目的

HDS-IRを、MINIDORA v0.4のLLM模型中核と混同せず、意味Projection・運用入力・監査履歴の境界として扱う。

公開HDS Compilerの実装はこの段階では変更しない。

## 2. 現行位置

```text
外部入力
  ↓
公開HDS Compiler
  ↓
HDS-IR
  ↓
運用Adapter
  ├─ 参照要求 / 選択問題 / 意味条件
  └─ 互換命令計画 → 計算実行器

別系統:
対象言語状態
  ↓ 言語対応
MINIDORA模型核
  ↓
成立差
```

HDS-IR経路と模型核経路は接続し得るが、同一物ではない。

## 3. 非同一性

次を固定する。

```text
HDS-IR != LLM模型中核
HDS-IR != 成立差
HDS-IR != Compute IR
HDS Compiler != LLM成立条件
```

HDSによる意味Projectionが有用であることと、大規模言語模型成立規定の普遍条件であることを混同しない。

## 4. HDS-IRが保持する情報

現行HDS-IRは少なくとも次を保持できる。

- 原文 / 正規化文
- 入力言語 / 出力言語
- HDS座標
- HDS関係
- HDS残差
- HDS意味作用
- 由来・暫定性・再開放条件
- 互換運用用の実行核 / 初期状態 / 参照要求

固定した最終HDSスキーマを宣言しない。

## 5. 互換実行核

v0.3由来のHDS-IR実行核は、現在 `日本語命令形P → 計算実行器` の互換運用経路として保持する。

```text
HDS-IR.手順
→ 計算実行器
```

これをLLM模型関係と呼ばない。

実行核が閉包していない、意味損失残差がある、未確定値を確定要求している場合は、従来どおり実行へ昇格させない。

## 6. 模型核への将来接続

次段でCompute IRを確定した後、HDS意味Projectionから模型核へ必要な情報だけをloweringする。

予定境界:

```text
HDS semantic IR
        ↓ lowering
Compute IR
   ├─ 言語状態 / 文脈条件
   ├─ 模型関係入力
   ├─ 候補状態
   └─ 計算作用
        ↓
MINIDORA模型核 / 計算実行器
```

この仕様が確定する前にHDS Compilerの意味責任を模型核へ押し込まない。

## 7. PとData

既存原則は維持する。

```text
P    = どう処理するか
Data = 何を意味し、何について処理するか
```

言い換え、属性、時点、範囲等のData差を命令Pとして増殖させない。

## 8. Rとの接続

RはHDS座標等から検索要求を形成できる。取得Dataを模型側関係の内部知識と自動同一視しない。

検索結果は外部Dataであり、模型核へ利用する場合は明示した言語状態・文脈・関係入力へ変換する境界が必要である。

## 9. HDS Compiler

標準公開Compilerと外部Compilerは既存 `HDSコンパイラProtocol` を維持する。

v0.4模型核再構成ではCompiler本体の大規模改変を行わない。Compute IR確定後に、semantic frontendとcompute lowering backendの責任を再監査する。

## 10. 受入条件

- HDS-IRをLLM模型中核と呼ばない。
- 旧Layer0実行核を計算実行器へ再分類する。
- HDS-IR未閉包時の保留を維持する。
- HDS Compilerの公開境界を維持する。
- 次段Compute IRが未確定であることを明示する。
- 日本語を内部規定言語とする。
