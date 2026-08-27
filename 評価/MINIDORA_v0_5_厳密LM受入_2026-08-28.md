# MINIDORA v0.5 厳密LM受入 — 2026-08-28

## 対象

- `src/minidora/言語確率法則.py`
- `src/minidora/runtime.py`
- 上位規定: `2026-08-28-成立規定-7`
- 上位commit: `debb83e091a705a5eac09ef4fb97a5b36305db6d`
- MINIDORA実装commit: `85f92c64027ba83da44f0dbb05f5efa5dbae3a42`

## 受入内容

サンドボックスで次を確認した。

1. 全条件分布がexact `Fraction`で1へ正規化。
2. 形成済み系列に正の完全系列確率。
3. 未観測文字列もUNK射影により模型標本空間へ入る。
4. EOS確率下限が正。
5. 形成文書順序を変えても同一状態SHA-256。
6. JSON互換辞書化→復元で同一hash / 同一系列確率。
7. 最小模型もUNK/EOS上の厳密確率法則を持つ。
8. sampling非依存・決定論tie-break。
9. Runtimeで厳密LM核と能力模型核を別保持。
10. 候補scoreをLM確率へ流用しない。

サンドボックス結果:

```text
厳密LM単体       8 / 8 PASS
Runtime二核stub  2 / 2 PASS
```

## GitHub全体CI

GitHub Actions run: `33116506964`

対象matrix:

```text
ubuntu-latest × Python 3.11 / 3.12 / 3.13 / 3.14
windows-latest × Python 3.11 / 3.12 / 3.13 / 3.14
```

結果:

```text
8 / 8 jobs PASS
repository consistency = PASS
compileall             = PASS
unit tests             = PASS
v0.4 scale legacy      = PASS
module CLI             = PASS
console CLI            = PASS
```

これにより、v0.5厳密LM追加と二核分離が既存Runtime/knowledge choice/legacy回帰を破壊していないことを、Linux/Windows両方で受入した。

## 非主張

本受入は次を意味しない。

- GPQA高性能
- K3級推論
- Large成立
- 現代LLM呼称適合の完了
- 製品完成

## 判定

```text
STRICT_LM_CORE = PASS
CAPABILITY_CORE = SEPARATE_AND_REGRESSION_PASS
CROSS_PLATFORM_CI = 8/8_PASS
LARGE_STATUS = REOPENED
MODERN_LLM_LABEL = REOPENED
```
