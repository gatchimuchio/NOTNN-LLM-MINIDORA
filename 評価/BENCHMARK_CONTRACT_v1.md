# MINIDORA Benchmark Contract v1 — SUPERSEDED

状態: **履歴 / 非現行**

このv1は2026-09-09に [`BENCHMARK_CONTRACT_v2.md`](BENCHMARK_CONTRACT_v2.md) へ置換された。

v1ではGPQAの固定ReplayとLIVE E2Eを分離していたが、ユーザー明示指示により現行方針をさらに変更した。

```text
2026-09-09以後
GPQA固定参照Data = 禁止
GPQA正本性能     = LIVE E2Eのみ
```

したがってv1に存在した `GPQA-FIXED-REPLAY`、C2固定Replay、固定入力hashによるGPQA直接比較は、**新しい正本GPQA測定へ使用しない**。

Core37 `37/198` 等の過去Replay値は当時の履歴として残るが、現行正本性能ではない。

現行正本:

- [`BENCHMARK_CONTRACT_v2.md`](BENCHMARK_CONTRACT_v2.md)
- [`../CURRENT_CANONICAL.md`](../CURRENT_CANONICAL.md)
- [`GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md`](GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
