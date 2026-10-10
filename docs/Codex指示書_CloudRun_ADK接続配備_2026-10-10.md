# MINIDORA Codex実行指示書：Google ADK接続・Cloud Run配備（第1工程）

作成日：2026-10-10
対象：`gatchimuchio/NOTNN-LLM-MINIDORA` の現行 `main`
実行担当：Codex
目的：**ミニドラ本体を維持したまま、Google ADKを実際の実行経路へ接続し、Google Cloud Runへ配備・実測検証できる状態を成立させる。**

## 0. 最上位命令とスコープ

- これは新規AI・代替LLMの開発ではない。ハッカソンへ提出する主体は既存の **MINIDORA** である。
- 調査、設計、実装、設定、テスト、クラウド実機検証、必要なドキュメント作成をCodex自身が行う。許可済みの操作についてユーザーへ手作業を転嫁しない。
- 成果は「ローカルでコードを書いた」ではなく、「ADK経由で既存MINIDORAを駆動し、Cloud Runで動作確認できた」で判定する。
- 今回は **Google Cloud接続と配備の第1工程**。ハッカソン提出フォーム送信、紹介記事執筆、動画投稿は今回の対象外。必要なら次工程へ引き継ぐ。
- `AGENTS.md`、`PUBLICATION_BOUNDARY.md`、`CURRENT_CANONICAL.md`、現行実装・テスト・実測を作業前に読み、工程の区切りでも指示書と照合する。現在の `main` が正本。過去の測定を現行最新版の性能として転記しない。
- 既存HDS中核、構文化器、目的保持、学習、再照合、非退行、監査の意味と責任は変更しない。必要最小限の配備・接続修正に限定し、二重の意味判断・第二の実行主体を設けない。
- 適用順は、ユーザー明示指示、`AGENTS.md`、本指示書、局所仕様。矛盾があれば当該箇所を明記して上位指示を守る。

## 1. 作業環境・版管理

- 最初にリポジトリを現物確認する。重点確認：`README.md`、`製品版/README.md`、`src/minidora/製品版/__main__.py`、`src/minidora/製品版/api.py`、`src/minidora/HDS運用/製品.py`、`deploy/Dockerfile`、`deploy/CLOUD_RUN.md`、`.github/workflows/再構築CI.yml`、`tests/`、直近GitHub Actionsログ。
- 実装・修正・通常検証はサンドボックス。GitHubは正本・履歴・反映先であり作業場所ではない。GitHub APIから取得してサンドボックスで検査し、APIから `main` へ直接反映する。`git clone / pull / push` を使わない。新規ブランチ・PRを作らない。
- この標準経路を利用できないCodex実行環境なら、勝手な代替Git運用へ移らず、実行できる部分を進めたうえで境界と必要な操作だけ報告する。
- GitHub Actionsを通常の単体試験代行に使わない。既存CIは最終の実環境受入に用いる。外部実測・重い処理は必要範囲に絞る。
- 直近の既知状況：2026-10-09 UTCの `d88343d` では再構築CIが日本語基底詳細監査の52件で停止、以降の試験は未実行。GPQA正式性能正本は2026-09-27の中核40/198であり10月最新版の性能ではない。最初に最新情報を再観測し、既知状況が変化していれば更新する。

## 2. 作業手順（各段階で指示書を読み直す）

### A. 現況・クラウド権限監査

1. `main` の最新SHA、現行エントリーポイント、RESTエンドポイント、既存Dockerfile、ADK導入状況、サーバのリッスンアドレス、HDS時の同一生成元制限、状態保持、トレースを実測する。
2. `gcloud`、Google Cloudプロジェクト、認証主体、課金有効化、API、Cloud Run、Artifact Registry、Cloud Build、IAM、GitHub Actionsからの認証可否を、アクセス可能な範囲で調べる。プロジェクトID・リージョン・サービスアカウントを推測で作業対象に採用しない。
3. 権限がない場合でもローカル実装・テスト・構成ファイル・再現手順を進める。最後にユーザー本人の操作が必要な **最小の具体的手順** だけ示す。課金アカウント開設・同意・個人認証を代理で完了したと偽らない。
4. 最新のGoogle ADK 2.x、Cloud Run、GitHub Workload Identity Federation公式ドキュメントを確認する。旧ADK 1.xの `BaseAgent._run_async_impl` のみに依存した古い実装例を無検証で流用しない。
5. ハッカソン公式ルールも確認する。Cloud RunとADKを「実際に利用」した証拠を残し、ライブラリの単なる依存追加で済ませない。公式参加者スキル `zenn-dev/hackathon-agent-skills` は必要なら参照し、公式規約との不一致では規約を優先する。

### B. ADK接続の実装

1. 既存のミニドラHDS製品入口を動かす小さなADKアダプターを作り、**実際のチャット要求がADKを通ってHDS側へ達する** 構成にする。ADK 2.xで動く公式サポート範囲の方式を選択する。
2. ADKは入出力・実行統合境界に限定する。MINIDORAと無関係な `LlmAgent`、Geminiや外部LLMによる回答生成・意味判断・フォールバックを導入しない。ADKの状態・セッションが既存HDSの意味正本を上書きしてはならない。
3. 既存 `/api/chat`、`/api/trace/{trace_id}`、`/api/capabilities`、`/health` とWeb UIを極力維持する。既存製品入口にアダプターを接続する方法を優先し、並行する別チャット製品を作らない。
4. ADK通過を実行ログまたは検査用トレースで判定できるようにしつつ、非公開内部理論を公開しない。出力は既存のAPPROVE/SUSPEND/FAIL、出典、ハッシュ監査を継承する。
5. ADK経由と従来の直接実行で、対応済み入力・状態・監査・保留の意味が不意に変わらないことをテストする。

### C. Cloud Run用パッケージ・実機配備

1. 既存 `deploy/Dockerfile` と公開UIを再利用する。単一Cloud Runサービスを優先し、やむを得ないときだけ分離する。なぜ分離が必要か根拠を提示する。
2. Cloud Runの `PORT` と `0.0.0.0` バインドに適合させる。現行の `--HDS --serve` がローカル限定である点を確認し、公開時の認証・Origin・Host検査を別責任として安全に設計する。**セキュリティ制約を単純削除して通してはならない。**
3. まず認証必須の検証環境にデプロイ。公開審査用URLが必要な場合は認証、レート制限、入力上限、外部通信境界、テストユーザー・サンプルデータの扱いを検査してから段階的に対応する。無防備な全公開を既定にしない。
4. 実行用サービスアカウントは最小権限。長期有効なサービスアカウントJSON鍵をGitHub、コード、ログに保存しない。デプロイ自動化が必要なら **GitHub Actions OIDC + Workload Identity Federation** を優先する。リポジトリ識別子、ブランチ等を条件に権限を絞る。
5. デプロイワークフローは初期状態で手動実行 `workflow_dispatch` を優先。通常の `main` プッシュのたびに再デプロイして課金・API枠を消費する構成にしない。
6. 配備前にAPI/Secrets/ネットワーク/公開境界を監査する。Cloud Runは原則 `min-instances=0`、費用暴走を防ぐ `max-instances=1` から始め、値を変更する理由と費用影響を残す。
7. Cloud Runインスタンスのメモリ上の会話状態・監査台帳は再起動やスケールで失われうる。永続化を実装しない場合は「永続」と説明しない。複数リクエスト・再起動での挙動を受入試験で明示する。
8. 既存 `PUBLICATION_BOUNDARY.md` と `tools/公開境界監査.py` を守る。非公開HDS理論、完全対応表、派生教師データ、認証情報、外部参照の秘密値を公開物に混入させない。

### D. 試験・受入

- サンドボックスで関連する単体・回帰・公開境界・日本語基底・構文検査を行う。既存CIの失敗を「ADKの失敗」と誤認せず、原因を別計上する。今回の変更で生じた欠陥は修正する。既存失敗が提出可能性を妨げる場合のみ、必要な範囲で修復する。
- 最小E2E：①Web UI表示、②`/health`、③`/api/capabilities`、④ADK→HDSの`/api/chat`、⑤同じセッションで連続依頼・条件訂正、⑥`/api/trace/{trace_id}` とhash chain検証、⑦未知入力での保留または明示失敗、⑧不正入力・未認証アクセスの拒否。
- ローカルE2EとクラウドE2Eを分けて記録する。クラウドE2Eでは実際に得たURL、Cloud Runのサービス名・リージョン・リビジョン、ログ、実測のHTTP結果を残す。URLは作り話で埋めない。
- 継続会話がCloud Runの起動/停止で失われる場合は未成立項目として明示。デモとして成立する範囲と制限を区分する。
- 最後に変更差分、公開ファイル、権限、使用したAI技術、CI状態、既存機能退行、現時点のクラウド課金設定を確認する。

## 3. 完了条件

次の全項目を満たしたときのみ「第1工程完了」と宣言する。

1. 既存MINIDORAのHDS中核を維持し、ADKが実行要求経路で実際に使用されている。
2. Google Cloud Runに本人が許可したプロジェクト・安全な認証構成でデプロイされ、公開URLまたは認証付き検証URLが実在する。
3. 実際のCloud Run URLでHDS実行、連続依頼、トレース、失敗・保留の受入検査を行い、結果が再現可能である。
4. 既存API、監査、公開境界を無根拠に破壊していない。実施した検査と未実施検査を分けて報告する。
5. GitHub `main` に必要最小限の実装・構成・手順を反映し、コミットSHAを固定している。

条件が満たせなければ **「未完了：阻害条件」** として閉じる。ローカル成功やドライラン成功をクラウド配備成功と言い換えない。

## 4. 出力する最終報告

以下を簡潔に報告する。

- 最新開始SHA → 最終SHA、変更ファイルと変更理由
- ADK実経路とHDS境界、採用したADK/Cloud Runバージョン
- Google Cloudプロジェクトの確認状況（秘匿値は出さない）、サービス名・リージョン・Revision・URL
- 実施済みテストと結果、CI成功/失敗の内訳、実行ログ・証拠への参照
- IAM・Secrets・公開可否・永続化・課金リスク
- ユーザー本人にだけ可能な作業（存在する場合のみ具体的に一括提示）
- 完了／未完了と、その判断根拠
- 第2工程（審査向け最終提出パッケージ）に渡せる残件

**作業を自分で進められる範囲は完了まで進める。認証・権限不足が判明しても、他の可能な作業を止めず、ただし成功は捏造しない。**

## 5. 一次資料

- ハッカソン公式：https://zenn.dev/hackathons/google-cloud-japan-ai-hackathon-vol5
- 参加者向け公式スキル：https://github.com/zenn-dev/hackathon-agent-skills
- ADK 2.0：https://github.com/google/adk-docs/blob/main/docs/2.0/index.md
- ADK Cloud Run：https://github.com/google/adk-docs/blob/main/docs/deploy/cloud-run.md
- Cloud Runソース配備：https://docs.cloud.google.com/run/docs/deploying-source-code
- GitHub Actions WIF：https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines
