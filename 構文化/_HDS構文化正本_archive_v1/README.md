# Open LLM HDS構文化正本アーカイブ

このディレクトリは、HDS構文化だけを行った教師正本を ZIP→base64 分割で保存する。
Layer-0 / P / Adapter / P形成 / 最小化 / 他モデル比較は含まない。

## 対象

- OLMo 3: 242教師 / 22成立関係 / 10未解残差
- LLM360 K2-V2: 225教師 / 20成立関係 / 10未解残差
- Apertus 1.5: 180教師 / 22成立関係 / 20未解残差

Apertus 1.5は2026-08-20時点で詳細technical reportがforthcomingのため、1.5直接資料と1.0継承系列証拠を分離し、未公開領域は未観測として保持した。

## 復元

各モデルの `ARCHIVE_MANIFEST.json` に記載された順で `part*.b64` を連結し、base64 decodeするとZIP正本になる。
ZIP内には分割教師JSONL、`教師全量.jsonl`、source lock、HDS報告、成立関係、監査、未解残差を含む。
