# 配布境界

GitHub側では、閲覧・差分監査できるsource、試験、文書、台帳、結果を正本として保存する。

binary ZIPとwheelはtext-only connector経路で破損させないため、リポジトリへ不完全な分割物を残さない。ローカル検証済み完全成果のSHA-256は次。

```text
K3命令化非ニューラル実装_v0.3.1_日本語版.zip
3dbe572fb83d55924cdc77392c2c0a0f57e875c108b4cffa886a657a34d9b370
```

リポジトリ上のsourceから再構築する。

```bash
python -m pip install -e .
pytest -q
python 操作/配布を検証.py
python -m pip wheel . --no-deps -w dist
```
