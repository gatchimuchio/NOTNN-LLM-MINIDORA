# NOTNN-LLM-MINIDORA — ミニドラ

> **MINIDORAは、LLMの成立条件・能力作用と現在主流の実装方式を分離し、ニューラルネットワーク／Transformerを中核に使わない方式で再実装する研究・実装プロジェクトです。**

[English](README.en.md) / [製品版](製品版/README.md) / [設計](設計/README.md) / [評価](評価/README.md)

公開版では内部理論の完全定義・固定参照先・理論から実装への完全対応表は公開しません。公開境界は [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md) を正とします。

## 現在地

現行値と履歴系列を分けて扱います。

| 評価系列 | 状態 | GPQA Diamond | 意味 |
|---|---|---:|---|
| 現行MINIDORA中核 | **現行正本** | **40 / 198 (20.20%)** | HDS構文化器Kernelを単一意味正本とし、`HDS駆動コア.選択実行` から直接実測した現行中核 |
| MINIDORA30 | 履歴セーブポイント | 30 / 198 (15.15%) | 2026-09-09の旧模型核系列 |
| MINIDORA80 | 履歴セーブポイント | 80 / 198 (40.40%) | 2026-09-09の旧能力モジュール込み系列 |

2026-09-27の現行中核正本は、GPQA Diamond 198問全数を `LIVE_ONLY` 参照で実測し、**40 / 198**。初期継承状態36正答から最終40正答へ改善し、実行内退行0、最終全候補被覆198/198、一問一問題束形成198/198を確認しています。

固定参照資料・保存済み検索結果・問題別再生束は現行正本性能評価へ使用しません。別run、および独立LIVE参照を使うpaired比較の得点差をコード変更だけの純粋因果差とは扱いません。

MINIDORA80は能力追加方式の履歴実証として保持します。同一run controlled A/Bでは能力モジュールOFF 29 / 198、ON 80 / 198、正答純増+51、退行0でした。これは現行中核40 / 198とは別系列です。

正本:
- [現行正本案内](CURRENT_CANONICAL.md)
- [現行MINIDORA中核 40/198](評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-27.md)
- [評価契約 v3](評価/評価契約_v3.md)
- [開発正本履歴](開発正本履歴.md)

## MINIDORAの構成方針

MINIDORAは次を分離します。

```text
模型核
├─ 非ニューラル言語模型
├─ 汎用能力
├─ 汎用計算
├─ 外部参照
└─ 実行・監査

能力モジュール
├─ 会話
├─ 要約
├─ 抽出
├─ 計算
├─ 知識参照
└─ 追加可能な専門・汎用能力
```

能力追加は模型核の再学習・fine-tuning・大型化と同義ではありません。成立済み模型核の外側へ能力を追加し、不成立時は既存経路へ透過または保留します。

構文化・状態差・再照合等の詳細は、公開範囲で [設計/](設計/)・[構文化/](構文化/)・試験に分離して保持しています。

## 統合運用

インストール:

```bash
python -m pip install -e .
```

統合運用:

```bash
python -m minidora.製品版 --HDS --serve
```

製品版:

```bash
python -m minidora.製品版 --serve
```

HTTP:

```text
POST /api/chat
GET  /api/trace/{trace_id}
GET  /api/capabilities
GET  /health
```

詳細: [製品版README](製品版/README.md)

## 評価と履歴

次を同一視しません。

```text
厳密言語模型成立
!= 推論機構成立
!= 模型核性能
!= 能力モジュール込み性能
!= 製品完成度
!= Large
```

GPQAはLLM定義そのものではなく、同一問題集合で機構差・能力差を観測する評価面として使用します。

過去の作業ログ・旧評価個票はdefault treeへ重複保存しません。採用された開発正本の節目と復元commitは [開発正本履歴](開発正本履歴.md) に集約します。`構文化/` はMINIDORA構築の原観測・構築原料として保全します。

## リポジトリ

| 場所 | 責任 |
|---|---|
| [`src/minidora/`](src/minidora/) | 現行実装 |
| [`tests/`](tests/) | 単体・回帰・受入試験 |
| [`設計/`](設計/) | 公開可能な局所設計・互換境界 |
| [`評価/`](評価/) | 現行正本・現行能力の受入証拠 |
| [`docs/`](docs/) | 現行の補助文書 |
| [`構文化/`](構文化/) | 観測・構文化履歴 |
| [`製品版/`](製品版/) | 製品版案内 |
| [`artifacts/`](artifacts/) | 小さな固定成果物のみ |

全数ベンチの巨大JSON・固定参照束はdefault treeへ置かず、GitHub Actions artifactまたは評価サマリへ分離します。

## 日本語基底

MINIDORAが自ら定義する内部意味は日本語を正本とします。英語その他は外部規格・API・識別子・国際公開等の境界で使用します。

- [日本語基底規定](設計/00_日本語基底規定_v1.md)
- [日本語正本語彙](設計/01_日本語正本語彙_v1.md)
- [参照正本](参照正本.md)

## 検証

```bash
python tools/リポジトリ整合性監査.py
python tools/日本語基底監査.py
python tools/日本語基底詳細監査.py
python tools/公開境界監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -q
```

## ライセンス

- ソースコード・実装: **Apache License 2.0** — [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0)
- 仕様・設計・評価・README等: **CC-BY-4.0** — [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0)
- 適用範囲: [LICENSE](LICENSE)
- 帰属・第三者由来物: [NOTICE](NOTICE)

## Author

**がっちむち♂**
