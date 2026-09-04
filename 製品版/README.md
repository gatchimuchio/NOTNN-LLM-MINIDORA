# MINIDORA Product Prototype v1

> ハッカソン向けの「薄いデモ」ではなく、成立済みMINIDORA Coreへ日常利用向けCapability Moduleを追加し、製品として使えるチャットAIを構成する実装。

## 目的

1. MINIDORAを最低限のチャットAI製品として成立させる。
2. ニュース→要約をデモする。
3. GPQA以外の日常タスクでも、Core再学習なしのModule追加が実効能力増加として成立することを確認する。
4. 全応答について「なぜこの応答になったか」を、後付け説明ではなく実行経路として追跡する。
5. 長期目標としてGPT-4級の一般チャット使用感を目指す。これは現時点の性能同等宣言ではない。

## 構造

```text
Browser / API Client
        ↓
MINIDORA Product Chat
        ↓
Capability Registry
 ├─ 基本会話 Module
 ├─ ニュース Module
 ├─ 要約 Module
 ├─ 文脈変換 Module
 ├─ 情報抽出 Module
 ├─ 計算 Module
 ├─ 知識参照 Module
 └─ 既存 MINIDORA Core
        ↓
Response Composer
        ↓
Governance Ledger
```

能力Moduleは共通契約 `名前 / 版 / 優先度 / 判定 / 実行` を持つ。新能力はレジストリへ登録でき、製品チャットやCoreの再学習を必要としない。

## デモ

```text
今日のニュースは？
↓
RSS外部参照
↓
取得ニュースを表示

3行で要約して
↓
直前の参照本文を要約
↓
参照外事実を追加しない
```

各応答には `trace_id` と `trace_hash` が付与される。

## 起動

```bash
python -m pip install -e .
python -m minidora.製品版 --serve
```

ブラウザで `http://localhost:8080/` を開く。

API:
- `POST /api/chat`
- `GET /api/trace/{trace_id}`
- `GET /api/capabilities`
- `GET /health`

## ガバナンス

監査対象:
- 入力
- 能力候補
- Module選択
- Module版
- Module入力/出力
- 外部参照識別子
- Module不成立時の透過
- 応答構成
- 会話状態更新
- 最終応答

各イベントをSHA-256 hash chainで接続し、前応答のroot hashも次応答へ接続する。

`MINIDORA_AUDIT_LOG` を設定するとJSONLへ追記し、`flush + fsync` まで行う。WORM化・外部署名・外部anchorは配備層の責任であり、現時点のローカルファイルを改変不能と主張しない。

## 能力拡張実証

`tools/製品能力Module実証.py` は同一Coreに対し、Capability ModuleをOFF/ONして日常タスクの差を測る。

サンドボックス段階では代替Coreで機構確認を行う。公開する正式値は、現行MINIDORA Coreへ還元した後に同じランナーを実行して確定する。

## 性能目標

GPT-4級は**開発目標**。現時点で同等性能を主張しない。

到達度は、会話継続、要約、知識参照、比較、推論、計算、変換、検索、コード等の実利用能力を追加し、退行を監査しながら反復測定する。
