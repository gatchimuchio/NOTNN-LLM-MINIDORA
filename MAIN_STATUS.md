# main正本状態

**基準日：2026-08-18**

## Branch方針

```text
正本branch = main
その他branch = 不許可
```

`.github/workflows/main-only.yml`が、mainへのpushごとにmain以外のGit refを削除する。

## 製品Runtime

製品ソースは`product/`に統合済み。

- 日本語優先Runtime
- SQLite永続化
- BM25／日本語n-gram
- Horn型規則推論
- HDS PASS／SUSPEND／FAIL
- OpenAI互換API
- CLI／Web UI
- 文書投入
- 監査hash chain
- Windows／Linux／Docker
- 製品試験
- K3構造差分ベンチ

## ベンチ結果

| 指標 | MINIDORA製品E2E | K3構造射影核 |
|---|---:|---:|
| status正解 | 7/7 | 7/7 |
| answer正解 | 7/7 | 7/7 |
| 温間中央値 | 7.417 ms | 0.055 ms |
| p95 | 12.229 ms | 0.068 ms |
| 逐次QPS | 124.4 | 17,281.2 |

K3側は実Kimi K3ではなく、公開構造を同一課題へ投影したin-memory非ニューラル参照版。
