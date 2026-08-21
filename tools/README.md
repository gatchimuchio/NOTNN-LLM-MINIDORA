# tools

`tools/` は、取得物の同一性確認、公開物inventory、リポジトリ整合性監査など、**開発・監査用の補助ツール**を置く。

Runtime本体は `src/minidora/` であり、`tools/` のスクリプトをMINIDORAの推論Runtime依存として扱わない。

## 現在のツール

- `k3_hf_identity_inventory.py` — K3 Hugging Face公開物の識別・inventory補助。
- `k3_public_artifact_inventory.py` — K3公開artifactのinventory補助。
- `repository_consistency_check.py` — 正本参照、version、主要文書リンク、Layer-0契約の整合性監査。

## 実行

```bash
python tools/repository_consistency_check.py
```

CIでも同じ整合性監査を実行する。
