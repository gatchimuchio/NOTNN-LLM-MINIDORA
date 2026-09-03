# docs

`docs/` は、MINIDORAの個別実装・接続経路を説明する**補助文書**を置く。

現行設計の正本は [`../設計/`](../設計/) であり、`docs/` の記述が設計正本と食い違う場合は、まず不整合として扱う。

## 現在の文書

- [`SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md`](SAVEPOINT_2026-09-01_MINIMAL_GENERIC_CORE.md) — 最小汎用LLM core + HDS異常時最小介入を再開地点として固定したセーブポイント。
- [`HDS_IR_NATIVE_K3.md`](HDS_IR_NATIVE_K3.md) — HDS-IRからK3相当能力核へ直接接続する旧経路の補助記録。現行標準coreのactive pathではない。

## 境界

- 設計契約 → `設計/`
- 観測・再構成成果 → `構文化/`
- 実測・baseline → `評価/`
- 固定取得物・派生成果 → `artifacts/`
- 実装 → `src/minidora/`

補助文書を追加するときは、どの設計正本を説明しているかを明示する。
