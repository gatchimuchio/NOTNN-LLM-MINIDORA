# 完全成果バンドル

GitHubへのバイナリ転送時の破損を防ぐため、完全ZIPをBase64テキストへ分割して格納している。

## 復元

リポジトリ直下で実行する。

```bash
python 成果バンドル/復元.py
```

復元されるファイル：

```text
NOTNN-LLM-MINIDORA_成果バンドル_20260818.zip
```

正しいSHA-256：

```text
777073b9f6b1d4ff299b971c11ee695f89f9b4db6476f26d02a5be4aab536d4f
```

`復元.py`はBase64復号後にSHA-256を検証し、不一致ならZIPを書き出さず失敗する。

## 展開と検証

```bash
unzip NOTNN-LLM-MINIDORA_成果バンドル_20260818.zip -d /tmp/notnn-llm
cd /tmp/notnn-llm
make test-all
```

ZIP内には日本語の解析文書、統合設計、K3／Llama 3／DeepSeek V3.2／Qwen3.6の参照実装、全モデル比較、検証結果、出典固定台帳、用語集を収録している。
