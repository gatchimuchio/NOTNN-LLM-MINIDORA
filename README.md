# NOTNN-LLM-MINIDORA — ミニドラ

> **MINIDORAは、LLMの成立条件・能力作用と現在主流の実装方式を分離し、ニューラルネットワーク／Transformerを中核に使わない方式で再実装する研究・実装プロジェクトです。**

[English](README.en.md) / [製品版](製品版/README.md) / [設計](設計/README.md) / [評価](評価/README.md)

公開版では内部理論の完全定義・固定参照先・理論から実装への完全対応表は公開しません。公開境界は [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md) を正とします。

## 現在地

評価系列は混同せず並立させます。

| 評価系列 | 現行正本 | GPQA Diamond | 意味 |
|---|---|---:|---|
| 模型核 | **MINIDORA30** | **30 / 198 (15.15%)** | 模型核のLIVE E2E性能 |
| 模型核 + 科学能力モジュール | **MINIDORA80** | **80 / 198 (40.40%)** | 能力モジュール込みシステム性能 |
| 統合実行系 | 別系列 | 個別受入 | MINIDORA30 / 80の値を無言転記しない |

2026-09-09以後、GPQA正本性能評価では固定参照資料を禁止し、実行時に新規取得する `LIVE_ONLY` 参照を使います。

MINIDORA80の同一run controlled A/B:

```text
能力モジュール OFF = 29 / 198 (14.65%)
能力モジュール ON  = 80 / 198 (40.40%)
正答純増           = +51
能力モジュール発火 = 55
発火正答           = 55 / 55
退行               = 0
```

GPQAスコアという限定軸では原論文のGPT-4ベースライン39%と同じ約40%帯ですが、評価条件は完全同一ではなく、GPT-4との総合能力同等を意味しません。

正本:
- [現行正本案内](CURRENT_CANONICAL.md)
- [MINIDORA30 E2E正本](評価/GPQA_Diamond_MINIDORA30_E2E_正本_2026-09-09.md)
- [MINIDORA80 E2E正本](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md)
- [評価契約](評価/評価契約_v2.md)
- [HDS-MINIDORA受入正本](評価/HDS_MINIDORA_受入正本_2026-09-17.md)

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

## 評価の読み方

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

過去のReplay・旧セーブポイント・失敗実測は削除せず [評価/](評価/) と [docs/](docs/) に履歴として保持します。ただし固定Replayを現行GPQA性能へ再利用しません。

代表履歴:
- [能力状態差循環 GPQA実測](評価/MINIDORA_v0_5_能力状態差循環_GPQA_2026-08-28.md)
- [科学専門能力 Replay](評価/GPQA_Diamond_既存科学専門能力_Replay_2026-09-02.md)
- [能力モジュール拡張境界](設計/35_MINIDORA_能力Module拡張境界_v1.md)
- [能力モジュール拡張成立実証](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)

## リポジトリ

| 場所 | 責任 |
|---|---|
| [`src/minidora/`](src/minidora/) | 現行実装 |
| [`tests/`](tests/) | 単体・回帰・受入試験 |
| [`設計/`](設計/) | 公開可能な局所設計・互換境界 |
| [`評価/`](評価/) | 現行正本・履歴評価 |
| [`docs/`](docs/) | 補助文書・セーブポイント |
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
