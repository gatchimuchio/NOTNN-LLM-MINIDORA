# tools

`tools/` は、取得物の同一性確認、公開物inventory、リポジトリ整合性監査など、**開発・監査用の補助ツール**を置く。

Runtime本体は `src/minidora/` であり、`tools/` のスクリプトをMINIDORAの推論Runtime依存として扱わない。

## 現在のツール

| Tool | 役割 | 追加依存 |
|---|---|---|
| `repository_consistency_check.py` | 正本参照、version、主要文書リンク、Layer-0契約の整合性監査 | なし |
| `k3_hf_identity_inventory.py` | K3 Hugging Face固定revisionのファイル同一性inventory | `huggingface_hub` |
| `k3_public_artifact_inventory.py` | K3固定revisionの公開artifact inventory | `huggingface_hub` |

## リポジトリ整合性監査

```bash
python tools/repository_consistency_check.py
```

CIでも同じ監査をLinux / Windows × Python 3.11–3.14で実行する。

## K3 inventory

K3 inventoryは外部サービスへアクセスする開発用処理のため、Runtime依存から分離する。必要な場合だけ追加依存を導入する。

```bash
python -m pip install huggingface_hub
python tools/k3_hf_identity_inventory.py --out /tmp/k3-hf-identities.json
python tools/k3_public_artifact_inventory.py --out /tmp/k3-public-artifacts.json
```

両ツールは指定した出力先へJSONを書くだけで、ブランチ作成・commit・pushを自動実行しない。

旧 `chappie/k3-hds-stream-v6` 専用GitHub Actionsは、対象ブランチ消滅後に無効な自動化となったため削除した。固定済み成果物や構文化履歴は削除せず保持する。
