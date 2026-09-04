# Cloud Run 配備境界

製品版は標準ライブラリHTTPサーバのみで起動し、`PORT` 環境変数を使用する。

Dockerfileは `deploy/Dockerfile`。

重要:
- 本番で `MINIDORA_CORS_ORIGIN` を必要なOriginへ限定する。
- `MINIDORA_AUDIT_LOG` のコンテナローカル保存を永続監査と見なさない。
- 永続監査はCloud Logging / DB / Object Lock等へ接続する。
- 公開前にRSS/Wikipedia等の外部利用条件・可用性を確認する。
