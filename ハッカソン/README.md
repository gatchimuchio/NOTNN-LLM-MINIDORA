# MINIDORA ハッカソン専用実装 v0.2

[English translation](README.en.md) / [MINIDORA公開README](../README.md)

> **ハッカソンでは「今日のニュースは？ → 要約して」という短い対話を通じて、MINIDORAの外部参照・会話状態・能力Module・応答追跡を一つの製品動作として見せます。**

本ディレクトリはハッカソン提出・デモ用の運用境界を記録します。実装本体は [`../src/minidora/ハッカソン/`](../src/minidora/ハッカソン/) に置き、既存MINIDORA Coreを改変せず能力Moduleとして接続します。

## デモの狙い

見せたいのはニュース要約そのものではありません。

```text
ユーザー入力
↓
必要な能力経路を選択
↓
外部Dataを取得
↓
会話状態へ保持
↓
次の指示で同じDataを再利用
↓
応答成立経路を監査記録へ固定
```

つまり、**最小チャットAIとして成立しながら、なぜその応答になったかを実行経路として追跡できること**をデモします。

## デモシナリオ

```text
> 今日のニュースは？

MINIDORA
- 当日のニュースを外部参照から取得
- 出典を保持
- 会話状態へ保存
- ニュース一覧を返す

> 要約して

MINIDORA
- 直前ニュースを会話状態から再参照
- 取得済みDataだけを対象に抽出・圧縮
- 参照外の新規事実を追加しない
- 要約を返す
```

ニュース→要約の専用経路では、外部LLMによる自由生成を使用しません。

## v0.2成立範囲

- 最低限の基本会話
- 既存MINIDORA Coreへの一般質問委譲
- RSSによる当日主要ニュース取得
- 同一セッションでの「今日のニュースは？ → 要約して」
- 明示文章の決定論的抽出要約
- 応答ごとの `trace_id` と監査root hash
- 入力受理、経路選択、外部参照、文脈参照、能力実行、応答構成、会話状態更新の実経路記録
- 各段階のSHA-256 hash chainによる改変検出
- 前応答の追跡ID・監査root hashを次応答の監査鎖へ接続
- 既存MINIDORA Coreが実行記録APIを持つ場合、`結果 / 参照 / 履歴 / 採否 / 言語計画 / HDS_IR` を監査記録へ保持
- 任意の追記専用JSONL監査保存

## 応答ガバナンス

この実装の「なぜこの応答をしたか」は、AI自身に理由を後付けで文章化させる方式ではありません。

**実際に通過した処理経路そのものを記録します。**

```text
入力受理
↓
経路選択
↓
外部参照 / 文脈参照
↓
能力実行
↓
応答構成
↓
会話状態更新
↓
応答監査root hash
↓
次応答の監査鎖へ前hashを接続
```

### 記録するもの

代表的には次を保持します。

- 入力文
- セッションID
- 経路選択条件と選択規則
- 参照したニュース・識別子・出典
- 使用したModuleと版
- Moduleへの入力と出力
- 会話状態の参照・更新
- MINIDORA Coreへ委譲した場合の公開実行記録
- 最終応答
- 応答状態
- 段階hash / root hash

一般質問を既存MINIDORA Coreへ委譲する場合は、Coreが公開する実行結果・参照・履歴・採否・HDS_IRを同じ監査鎖へ取り込みます。

実行記録APIを持たない代替接続先については、追跡範囲を「モジュール境界」と明記し、内部まで完全追跡済みとは扱いません。

## 改変検出と保存

各イベントは前イベントhashを含めてSHA-256化し、最終応答を含むroot hashを確定します。同一追跡IDへの上書きは拒否します。

`MINIDORA_AUDIT_LOG` を設定すると、1応答1行のJSONLとして `flush + fsync` 付きで追記保存します。

```bash
MINIDORA_AUDIT_LOG=.audit/minidora_hackathon.jsonl python -m minidora.ハッカソン
```

Windows PowerShell例:

```powershell
$env:MINIDORA_AUDIT_LOG = ".audit/minidora_hackathon.jsonl"
python -m minidora.ハッカソン
```

このJSONLは追記運用を前提としますが、OS上のファイル自体をWORM化するものではありません。製品運用ではCloud Logging、DB、オブジェクトロック等の外部永続層へ接続し、必要なら署名・外部anchorを追加します。

## ローカル起動

要件: Python 3.11以上

```bash
python -m pip install -e .
python -m minidora.ハッカソン
```

同一セッション内で次を実行します。

```text
> 今日のニュースは？
> 要約して
```

各応答末尾に `trace_id` と `trace_hash` が表示されます。

ライブラリ利用時は、`ハッカソンチャット.監査台帳.取得(trace_id)` と `検証(trace_id)` で実経路とhash整合を確認できます。

## モジュール構成

| 実装 | 責任 |
|---|---|
| `チャット.py` | 能力経路選択、既存MINIDORA Core委譲、監査接続 |
| `ニュース.py` | RSS外部参照、当日ニュース抽出 |
| `要約.py` | 自由生成を使わない決定論的抽出要約 |
| `会話状態.py` | セッション内履歴・直前ニュース保持、古いニュース文脈の除去 |
| `基本会話.py` | 挨拶・能力説明等の最低限会話 |
| `ガバナンス.py` | 実行経路台帳、段階hash、root hash、JSONL追記保存 |
| `型.py` | ニュース・応答・監査記録の型 |

## 試験

リポジトリ全体:

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
```

ハッカソン専用試験では外部RSSを使わず固定ニュース供給器を注入し、次を再現可能に確認します。

- ニュース→要約の文脈接続
- 応答間の追跡ID・監査hash接続
- 一般質問の基礎Core委譲
- 明示文章要約
- 基本会話
- 別経路へ移行した後の古いニュース文脈除去
- JSONL監査追記
- 各応答のhash chain再検証

## 現在未実装の配信層

v0.2はチャットCoreと監査境界を先に成立させた段階です。次は次の配信・表示層を接続します。

- ブラウザ用チャットUI
- Cloud Run配信境界
- Gemini比較表示
- Cloud Logging / DB / WORM相当の外部監査永続化
- 監査rootへの署名または外部anchor
- 応答画面からのTrace可視化

これらをまだ実装済みとは扱いません。

## 日本語基底

このハッカソン層もMINIDORA本体と同じく、日本語を内部意味正本とします。

英語版 [`README.en.md`](README.en.md) は国際公開用の翻訳であり、日本語版へ意味上従属します。