# MINIDORA 汎用core改善1 — 2026-09-01

基準: `docs/SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`  
実装commit: `7a75fa3bd3973836d5b064e152b7dbfa833a35d6`

## 変更

### 1. 同一Data非増幅

同一の意味・関係構造を持つ参照Dataは、出典IDが異なるだけでは複数の意味票へ増幅しない。

```text
同じData × N copies
→ 1つの意味状態
```

異なるDataは従来どおり別状態として保持する。

### 2. 再作用の成立境界保持

再作用時の比較面を「変化候補の上位2件」から、原則として次へ変更した。

```text
現在首位 + 最も強い変化候補
```

現在首位が変化候補なら、次に強い変化候補を使う。これにより、最終成立境界にいる現在首位を比較面から落としたまま下位候補だけを再照合しない。

## 境界

今回追加していないもの:

- 専門領域solver
- benchmark固有規則
- gold / qid / case ID
- 新しいNN / Transformer
- HDSによるwinner selection
- 新しい外部依存

この変更は、分野名・benchmark名・問題固有値を消しても成立する汎用core改善として扱う。

## 検証

適用runnerで次をPASS済み。

```text
repository consistency
日本語基底監査
compileall
unit tests
CLI smoke
```

この文書commitで通常のUbuntu / Windows × Python 3.11–3.14 CIを再実行する。
