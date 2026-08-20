# HDS構文化アーカイブ正本

このディレクトリは、GitHub Connector経由で大規模構文化物を欠損なく保存するためのbyte-exact archive payloadである。

各モデルの `partNN.b64` をファイル名順に連結し、Base64 decodeすると、そのモデルのHDS構文化正本ZIPを復元できる。

```bash
cat part*.b64 | base64 -d > model.zip
sha256sum model.zip
unzip model.zip
```

ZIP内には README / MANIFEST / source_lock / 教師JSONL全件 / HDS成立関係 / HDS適合監査 / 未解残差が含まれる。

本工程は構文化のみであり、Layer-0 / P / Adapter / P形成 / 最小化 / 実装写像 / モデル間比較は含まない。
