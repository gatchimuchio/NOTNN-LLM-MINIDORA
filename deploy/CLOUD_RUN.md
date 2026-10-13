# MINIDORA Cloud Run＋Google ADK配備

既存製品のUIとAPIからGoogle ADK 2.11.0の`Workflow/FunctionNode`を通り、同じHDS製品入口を呼ぶ。回答・意味判断・状態保持は既存MINIDORAが担当する。Geminiや外部LLMによる回答生成・フォールバックは使わない。ADK依存の`google-genai`はライブラリ構成上の依存であり、モデル呼出しの証拠ではない。

この文書は再現手順である。Cloud実機動作の成立範囲は、実URLの配備記録・実応答・出典・ADKと監査の対応で判断する。提出用D03実演と審査用Basicのみの実HTTPS検査は成立したが、`tools/CloudRun受入.py`の全項目、再起動受入、直接ブラウザの資格入力から回答表示までを一括で合格したとは扱わない。ローカル成功だけでは実機成立にならない。

新Cloud Run基本チャットの起動は、`製品版/Google起動構成.py`で固定したGoogle Cloud通常Search・ADC・GCS送信予算を、既存HDSの取得器へ注入する。設定不足・不正・Cloud依存不足は配信前に停止する。構成時には認証・DNS・Search・保存通信を行わず、管理者の`off`でも固定設定検査は省略しない。基本チャットなしの旧Cloud入口とローカル既定のWikipedia取得器は維持する。Google起動接続の局所検査は実Cloud受入とは別である。ADC接続器は`google-auth==2.61.0`を直接固定し、Cloud Runの明示SA又は明示した`authorized_user`ファイルだけを扱う。認証のHTTP開始・受信本文も当回の共有取得制御へ計上し、検索接続前に認証を済ませる。SDKの背景通信を残さないため、固定版の内部API `_set_blocking_regional_access_boundary_lookup()` に依存して境界照会を当回内で実行する。SDK更新時にはこの依存を再確認する。トークン成功応答はBearer型と有限な1〜86,400秒の有効時間を受け付ける。未知ADC・metadataのmTLS/Agent Identity経路は対応外として停止し、公開URLの私有IP拒否は維持する。同期DNSとSDK内の待機を含む厳密な実行時間上限と、再起動をまたぐ総費用制限の保証は未成立である。Google実機の固定構成からSearch・実本文・HDS回答へ至る経路は以下のD03で一回観測したが、一般Web全分野の品質受入とは区別する。

累積検索送信の候補実装は`製品版/検索送信予算.py`である。通常Search供給器は、同じproject/appに束縛した`GCS検索送信予算`を必須とする。管理者の固定設定には予算ID・開始/終了UTC・累積上限（最大1,000）・保存先を含める。設定全体のSHA256と予約数を一つのGCSオブジェクトへ保存し、metadata GET→世代条件付き本文GET→同じ世代条件付きPOSTの成功を確認してから、当回のURL・本文SHA・共有制御に束縛した一回許可を発行する。[GCS条件付き要求](https://docs.cloud.google.com/storage/docs/request-preconditions)に沿って412だけを総2試行で再処理し、他の失敗・結果不明では検索許可を発行しない。確定枠は検索失敗時にも返却せず、コピーによる再送や再起動後の旧許可復元も認めない。保存通信とSearchの要求直前に当回制御と期間を再確認する。

予算保存先はprivate・uniform accessの専用bucketとし、Buildのsource/log保存と分離する。runtimeの権限は固定objectへのget/create/deleteだけに限定する。初期内容は設定の`保存内容(0)`で構成し、管理者が`ifGenerationMatch=0`による初回作成だけを行う。runtimeは欠損を自動初期化せず、破損・設定不一致・期限・上限で停止する。配備、再実行、日付変更でカウンタをresetせず、清掃/lifecycleの削除対象からも期間中は除外する。運用者による有効な過去値への書戻しを単一CASだけで検出する保証はない。

この予約は検索送信数の上限であり、GCS操作・認証・起動・補助HTTP・ログ・保存・転送を含む総請求額の上限ではない。配備候補はBuildを600秒、Runを1CPU/2Gi・要求単位CPU・起動CPU増強なし・min0/max1/concurrency1・要求300秒とし、実観測で照合する。既存クレジット内の有限な実行計画では、最初の小さい配備/検索単位から実SKU・費用・クレジット適用を確認する。保存費用は期限拒否だけでは止まらず、soft-deleteの保持期間を含めた期限前の対象清掃が必要である。Google通常Searchの資源と公開サイト範囲の管理者構成は、実検索・本文取得・HDS内容品質・新Cloud Run受入とは分けて検査する。通常Search資源と予算の初期保存は管理者経路で構成済みで、本人認証を使った開発時の検索・本文取得は確認した。今回の新Cloudでは、固定実行構成から通常Search・本文取得・HDS回答を本人認証のD03で観測した。一般品質Qの全数評価は未成立。審査用Basicだけの実HTTPS応答は後述の範囲で確認し、通常ブラウザの資格入力から回答表示までは未確認である。累積予約の実更新値、実SKU・費用・クレジット適用、総費用の保証はこの実演結果だけから認定しない。管理者経路や局所試験を実機受入へ読み替えない。

検索外送の前には、検索語・必要語に含まれる既知のメール・電話・秘密値形式、人名候補、当回と過去会話で明示された保護値を検査する。停止時は認証・予算予約・Searchを始めない。原入力とHDSの意味処理は保持し、製品応答・参照・監査に安全な公開表現を別途作る。監査はv2で封印し、Cloud入口は旧v1監査の提供を拒否する。未知形式の個人情報を完全に判定する保証はなく、局所検査を一般会話品質・実Cloudの受入へ読み替えない。

## 現在の審査用Cloud実測（2026-10-13、限定D04）

- 実URL：[https://minidora-adk-verify-qp5ojmzmyq-an.a.run.app](https://minidora-adk-verify-qp5ojmzmyq-an.a.run.app)。本人承認後の審査公開構成で、Googleログインは不要、HTTP Basic認証は必須。
- revision：`minidora-adk-verify-judge-d2397cc3fc08-7234f7`、配備main：`d2397cc3fc08330c9be59eb76211299c65f8e0ee`。HDS本体復元点は旧実演と同じ`45a383943df8fc58666689ee8e1e8f90de1c26be`。HTTP認証境界を追加し、HDS判断・ADK配送・検索処理を維持した。
- Cloud Build：`49ceef54-1446-46bf-bc92-cd44254c2eef`、image digest：`sha256:951be8ea0978ff8d08bf14de7fdf8e68ee5c433faade600468b0cd255e8b217d`。1CPU／2Gi、要求300秒、min0／max1／concurrency1を保持。
- 新Basic入口はまず本人OIDC＋Basicで3実応答を確認。その後、対象サービスの`allUsers`へ`roles/run.invoker`一付与だけを追加し、既存IAMとサービス構成を維持した。project・検索資源・予算bucketの公開や他IAM変更は行っていない。
- 公開後は本人OIDCを取得・使用せず、BasicだけでHTTPS検査19件を実行。`8*9`→72（6.078秒）、藻場の実本文回答（14.453秒）、同一会話の引用形式（15.562秒）がAPPROVE。検索1回・本文1件、追質問の追加検索・取得HTTPは0。
- 各応答のADK単一HDS呼出と11項目の技術照合、独立v2監査・Trace対応が成立。UI・静的ファイル・health・capabilitiesの取得を確認し、無資格6入口と誤資格healthは401、別Originは403、不正JSONは400。
- [公開動画](https://youtu.be/q7hF26QBabI)は180秒。旧a38 revisionの本人認証付き実画面と旧図を収録したもので、現在のBasic入口の画面ではない。現在の[構成図](../docs/minidora-cloud-architecture.svg)は新認証境界に更新した。

Basic資格は審査員向け非公開欄で提供し、公開物へ保存しない。旧動画と新Basic非公開IAM時のUI確認は本人認証の中継を使用。公開後は操作環境の直接Basic到達が制限され、中継UI1試行もチャット要求を開始しないまま未成立で終了した。通常ブラウザの資格入力からUI実応答まで、全受入CLI・再起動受入、一般品質Q全数、応募受付は、この有限HTTPS検査だけでは成立としない。既使用題材の実演を初見品質評価へ算入しない。

## 旧a38のCloud実測（2026-10-13、限定D03）

- 実URL：[https://minidora-adk-verify-qp5ojmzmyq-an.a.run.app](https://minidora-adk-verify-qp5ojmzmyq-an.a.run.app)。この旧revisionでの実測時はIAM認証必須、本人認証で確認。審査主体の利用許可・到達性はこの実測の対象外。
- revision：`minidora-adk-verify-v4-a38b793250c1-80e504`。配備main：`a38b793250c1dfa96e49af028fae58235324ddab`、本体コード復元点：`45a383943df8fc58666689ee8e1e8f90de1c26be`。
- 実構成：1CPU／2Gi、要求300秒、min0／max1／concurrency1。Cloud Build image digest：`sha256:ff83a7b03ce75d84fb1ffb8411dd1daf5ba7375314fc40c0b59a193910480af0`。
- 藻場の自然質問は検索1回・実本文1件から回答へ到達。同じ会話の「引用形式にして」は追加検索・取得HTTPが0で成立。`2+3`と`3*7`は5と21、算術後の「詳しく説明して」はSUSPEND。
- 5応答の各11項目の技術照合が成立。ADK 2.11.0 Workflow／FunctionNode、要求ごとのHDS呼出1、独立v2監査と応答・Traceの対応を確認。
- 認証付きUI／health／capabilitiesはHTTP 200、未認証403、別Origin403、不正JSON400。単一実演の範囲であり、一般品質Q全数、再起動受入、審査主体アクセス、動画掲載、応募受付をこの旧実測だけで認定しない。

実入力・応答・出典と所要時間は [README](../README.md) を参照。実演題材は開発時にも扱ったもので、初見独立品質評価には算入しない。

## 1. 実行境界

- `deploy/Dockerfile`はPython 3.13、ハッシュ付き固定依存、非rootユーザー、単一Pythonプロセスで既存UIを配布する。
- 起動は`python -m minidora.製品版 --HDS --ADK --基本チャット --CloudRun --serve`。`PORT`で`0.0.0.0`へバインドする。従来の基本チャット指定なしの入口も維持する。
- 初回配備・受入はCloud Run IAM本人認証を必須にし、アプリもHTTP Basicと`MINIDORA_CLOUD_HOSTS`・`MINIDORA_CLOUD_ORIGINS`を検査する。審査公開は後述の本人承認後の手動modeだけで扱う。Origin・Host検査自体は本人認証ではない。ワイルドカードCORSを使わない。
- 許可Hostは実測した`*.run.app`ホスト、許可Originはその`https://`生成元。初回は`bootstrap.invalid`を設定して実URLの要求を拒否し、サービスURLを取得してから更新する。Cloud Runの既定TCP起動検査を使う。
- 基本チャットの管理者方針は`MINIDORA_RETRIEVAL_POLICY=auto|off`。`--基本チャット`を明示した場合の未設定は`auto`で、公開取得の必要性は既存HDSが判断する。通常HDSの従来の外部読取設定は維持する。基本チャットのAPIでは`external_read`省略は管理者方針に従い、`false`は今回だけ取得禁止、`true`も管理者の`off`を越えない。UIは自動検索の説明と任意の「この質問では外部検索しない」を表示し、CLIでは`--検索しない`で同じ禁止を指定できる。禁止は次の質問へ継承しない。`/api/capabilities`の`公開取得方針`は基本チャットで`auto`又は`off`、通常入口で`null`を返す。ADKはこれらを同じHDSへ配送する。
- ローカル既定の取得器はWikipediaの日本語・英語記事で、新Cloud基本チャットは固定Google構成を要求する。現構成の候補・本文の許可範囲は`www.mext.go.jp`、`www.mhlw.go.jp`、`www.env.go.jp`、`www.stat.go.jp`の4完全ホスト名であり、全Web又は全`go.jp`を許可しない。非Wikipediaの実本文を使う限定的なCloud基本チャット実演は本人認証で成立した。一般品質Q全数は未成立。審査用Basicのみの実HTTPS検査は前記の限定範囲で成立。設定値の変更だけを一般Web検索の成立として扱わない。公開URL・DNS・転送先・容量・時間を検査し、記事は資料として扱う。既取得の採用済み原資料は同じ会話の追質問に利用できる。API本文上限256,000バイト、チャット入口のレート制限、セッション数の既存上限を維持する。Cloud Run同時実行数1を設定する。
- HTTPエラーを送信した後は書込側をhalf-closeし、未読入力を64KiBずつ、総量32MiB・絶対期限2秒まで破棄して接続を終了する。受付上限とは別の拒否処理であり、本文をJSONやHDSへ渡さない。未読本文を残した即時closeによる実機502を修正するための処理で、期限超過や切断までエラー応答配送を保証しない。根拠は[RFC 9112の接続終了](https://www.rfc-editor.org/rfc/rfc9112.html#section-9.6)と[Cloud RunのHTTP/1上限](https://docs.cloud.google.com/run/quotas)。
- `min=0`、`max=1`、`min-instances=0`、`max-instances=1`、CPU 1、新MVP候補のメモリ2Gi、要求上限300秒、受入クライアントのソケット待機上限360秒。配備後の実観測も2Gi・300秒と照合する。旧実機の開始境界はCPU 1・メモリ1Gi・要求上限60秒として別に保全する。2Giは新候補の資源設定であり、Cloudで実測した必要量としては扱わない。変更には理由と費用影響を記録する。
- 会話と追跡台帳はメモリ内だけで、停止・再起動・新revision・インスタンス交換で失われる。永続化、再起動をまたぐ会話継続、複数インスタンス間同期は未成立。Cloud Loggingは実行証拠であり、会話の復元用台帳ではない。
- 保存領域・Secret・サービスアカウントJSON鍵をコンテナへ渡さない。`.dockerignore`とCloud Build用の許可ファイル限定ステージで構築原料・評価データ・認証ファイルを送信対象から外す。

要求上限を60秒から300秒へ延ばす理由は、一般HDSの複数目的を含む初回要求を60秒で切断しないための有限な待機枠を用意することである。開発時の218秒は通常応答と保存復元の合計で、その開発観測と同じ処理のCloud Run所要時間は未測定。cProfileの計装時間を上限の根拠にはしない。300秒・1CPU／2Giの設定で、前記D03実演を固定SHA・revisionに対応付けて観測した。これで厳密な処理停止、一般品質、長時間・複数要求での資源十分性を保証するものではない。T05の元の能力・品質要件は品質トラックQの独立受入として維持し、Cloud実測の開始前条件にはしない。時間設定の変更で能力や性能の合否を読み替えない。

新MVP候補のメモリを1Giから2Giへ増やす理由は、Windowsで保存済み成果の同源検査を1回行った開発観測で、ピーク作業セット1,029,693,440バイト（982MiB）、ピークコミット1,180,835,840バイト（1126MiB）となり、1Giに対する余裕を確認できなかったためである。Windowsの値をCloudのRSS・cgroup使用量やADK全経路の使用量へ読み替えず、2Giでの十分性も未確認とする。[Cloud Runのメモリ仕様](https://docs.cloud.google.com/run/docs/configuring/services/memory-limits)では1vCPUで最大4Giまで設定でき、割当上限を超えたインスタンスは終了する。新候補の2Giでの十分性は、提出用D01/D03で同じ公開固定版の実機観測から判断する。T05の全品質ゲートは品質トラックQとして独立に実施し、その未成立をCloud実測の開始前条件にはしない。メモリ設定を理由に品質基準、採否、入力又は保持条件を緩和しない。

## 2. 本人が確定する対象

Google Cloudの本人が許可したプロジェクトを実際に確認し、以下をGitHub repository variablesへ設定する。未設定ならワークフローは配備前に停止する。値を推測して選ばない。

| variable | 確定する値 |
|---|---|
| `GCP_PROJECT_ID` | 課金が有効な許可済みproject ID |
| `GCP_REGION` | 許可されたCloud Run / Artifact Registry / Cloud Buildのregion |
| `CLOUD_RUN_SERVICE` | MINIDORA専用のCloud Runサービス名 |
| `GCP_ARTIFACT_REPOSITORY` | 同regionにあるDOCKER形式のArtifact Registry repository名 |
| `GCP_BUILD_BUCKET` | 同projectのCloud Build専用既存bucketの`gs://` URL |
| `GCP_RUNTIME_SERVICE_ACCOUNT` | 旧入口はAPI権限なし、新基本チャットは期限付き通常Searchと固定予算objectだけの専用実行SA |
| `GCP_BUILD_SERVICE_ACCOUNT` | 専用ビルドSAのemail |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | 専用配備・検査SAのemail |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../locations/global/workloadIdentityPools/.../providers/...` |
| `MINIDORA_HTTP_BASIC_USERNAME` | 審査用username。ASCII英数字・`.`・`_`・`-`の1〜64文字 |
| `MINIDORA_HTTP_BASIC_PASSWORD_SHA256` | 32byte以上の暗号学的乱数から作るpasswordのSHA256、小文字16進64文字 |

実passwordは公開variablesやコードへ保存せず、受入用のGitHub repository secret `MINIDORA_HTTP_BASIC_PASSWORD` にだけ設定する。workflowは検査stepの秘密環境から読み、URL-safeな43〜128文字と固定SHA256との一致を確認する。受入用のusername/password JSONを`RUNNER_TEMP`へ0600・新規作成限定で置き、`--basic-credentials-file`で受入CLIへ渡す。秘密ファイルはCloud Buildの送信対象・証跡artifactの対象に含めない。コンテナにはusernameとSHA256の二環境値だけを渡す。未設定・不正・不一致ならCloud認証・配備前に停止する。

実行・ビルド・配備SAは分離する。旧入口の実行SAはAPI権限なしを維持する。新基本チャットは通常Searchの`discoveryengine.servingConfigs.search`とquota projectの`serviceusage.services.use`だけをprojectの期限付きcustom roleで認め、固定予算objectのget/create/deleteだけを別bucketの条件付きcustom roleで認める。組織・folderからの継承権限も設定者が確認する。ワークフローはprojectと対象サービスへの直接付与、公開IAM、課金、固定予算bucketの条件付き付与、custom roleの実権限、API、repository形式を検査し、異常時は停止する。

必要APIは`run.googleapis.com`、`artifactregistry.googleapis.com`、`cloudbuild.googleapis.com`、`iamcredentials.googleapis.com`、`sts.googleapis.com`、`discoveryengine.googleapis.com`、`storage.googleapis.com`。本人によるログイン・課金アカウントの開設や同意・project選択が必要な場合は代理完了と扱わない。

新Cloud基本チャットの起動には次の環境変数もすべて必要である。値は起動時に固定し、要求本文やセッションから受け取らない。Cloudでは実行SAだけを使い、ADC自動探索や利用者ファイルへ迂回しない。

| 環境変数 | 契約 |
|---|---|
| `MINIDORA_GOOGLE_PROJECT_ID` / `MINIDORA_GOOGLE_SEARCH_APP_ID` | 固定projectとglobalの通常検索app |
| `MINIDORA_GOOGLE_RUNTIME_SERVICE_ACCOUNT` | 同じprojectの明示実行SA |
| `MINIDORA_GOOGLE_PUBLIC_HOSTS` | 完全ホスト名のカンマ区切り。空白・重複・単一ラベル・ワイルドカード不可 |
| `MINIDORA_GOOGLE_BUDGET_ID` / `MINIDORA_GOOGLE_BUDGET_BUCKET` / `MINIDORA_GOOGLE_BUDGET_OBJECT` | 一つの固定保存先と予算ID |
| `MINIDORA_GOOGLE_BUDGET_START_UTC` / `MINIDORA_GOOGLE_BUDGET_END_UTC` | 秒単位の`YYYY-MM-DDTHH:MM:SSZ`、開始より終了が後 |
| `MINIDORA_GOOGLE_BUDGET_LIMIT` | 1〜1,000の正規整数表記 |

これらとHost/Originを構造化envファイルで配備へ渡す。初回配備、実URLへの更新、受入用の再起動で固定設定を保持し、実env・予算設定SHAと要求した値を照合する。固定値は`deploy/Google取得固定設定.json`に置く。本人が確定した`minidora-507702 / asia-northeast1`と実行SAの一致を配備前に検査し、カンマを含む公開ホスト設定も[envファイル](https://docs.cloud.google.com/run/docs/configuring/services/environment-variables)でそのまま渡す。`tools/CloudRun配備設定.py`は初回・交換後それぞれの実describe、IAM、Ready世代、起動引数、資源、env、予算設定SHAを照合する。予算の初期化・resetは行わない。

### 審査用Basic認証と手動公開mode

Cloud起動時はusernameとpassword SHA256の両方が必須で、片側だけ・空欄・不正値はlisten前に拒否する。全画面・静的ファイル・API・health・未対応HTTP方法をHDS実行前に認証し、資格なし・不正資格は401とBasic challengeを返す。healthの未認証例外は設けず、Cloud Runの起動確認にはTCP probeを使う。Host/Origin・本文256,000byte・既存入力と頻度の制限を維持する。ローカルで二項目とも未設定の場合の従来入口は維持する。

初回配備と実機受入はCloud IAMを非公開のまま維持する。`X-Serverless-Authorization: Bearer`に本人の短期OIDCを、`Authorization: Basic`にアプリ資格を渡す。資格・ヘッダー・tokenをログや証跡へ保存しない。通常workflowは公開IAMを拒否するため、公開済みサービスへ無断再配備しない。

審査公開modeは本人が具体的な実URLと認証方式を承認した後の手動工程である。同じサービスに`allUsers`の`roles/run.invoker`一付与だけを加え、IAM検査自体は有効に保つ。project・検索・予算bucketを公開せず、Basic認証は解除しない。`tools/CloudRun配備設定.py`の`--審査公開`はこの状態の検査用で、IAM変更を実行しない。作業者判断でworkflowへ公開フラグを追加して承認を迂回しない。

今回の公開後実検査でも、下記の配備記録を照合した。公開後の配備記録も`認証必須: true`を保ち、`利用者認証: HTTP Basic`・`審査公開: true`・`CloudIAM本人認証必須: false`を記録する。`tools/CloudRun受入.py --basic-credentials-file`へ権限制限されたusername/password JSONを渡し、Googleログインを持たないブラウザでもHTTPS challenge→資格入力→UI・実応答まで確認する。URLや資格の準備だけでは審査員到達性の成立としない。この公開modeの実機受入は、前記D03本人認証の実測とは別に記録する。

## 3. IAMとWIF

長期JSON鍵を作らず、GitHub Actions OIDC＋Workload Identity Federationを使う。providerの条件は、実際に確認した数値の`repository_owner_id`と`repository_id`、`assertion.ref == 'refs/heads/main'`、`assertion.event_name == 'workflow_dispatch'`に限定する。repository名の文字列だけでは識別しない。`google.subject=assertion.sub`と必要な数値属性をmappingし、該当repositoryの`principalSet`だけに配備SAへの`roles/iam.workloadIdentityUser`を付与する。

権限は初期構築時に必要な対象へ絞って設定する。projectのOwner / Editorや全SAへの偽装権限を配備SAに与えない。

| 主体 | 必要な範囲 |
|---|---|
| 実行SA | 旧入口はAPI権限なし。新基本チャットは期限付き通常Searchと固定予算objectだけ。stdout/stderr採取はアプリのLogging API権限を要しない |
| ビルドSA | 選択repositoryのArtifact Registry Writer、選択bucketのStorage Object Admin＋Legacy Bucket Reader（Cloud Buildのbucketメタデータ読取）、ビルドログ用権限 |
| 配備SA | Cloud Buildの作成・取得、選択bucketの送信、選択repositoryの読取、対象サービスの配備・IAM変更・検査・ログ読取 |
| 配備SAのSA利用 | 明示した実行SAとビルドSAに対する`roles/iam.serviceAccountUser`だけ |
| WIF主体 | 明示した配備SAへの`roles/iam.workloadIdentityUser`だけ。ID token発行権限を必要なSAに限定 |
| 初期非公開配備の検証呼出し | 対象サービスの`roles/run.invoker`を配備SAに付与。通常workflowでは`allUsers` / `allAuthenticatedUsers`に付与しない。本人承認後の審査公開は前節の手動工程に限る |

新規サービスを作る配備権限はprojectで必要になるため、専用projectまたは必要permissionだけのcustom roleを使う。`roles/run.admin`等の既定roleを使う場合も対象projectに限定し、作成後に対象サービスへの範囲縮小を検討する。監査にはproject・service・予算bucketのIAM読取、custom roleの定義読取、課金状態読取、API一覧読取が必要。実行SA・組織ポリシーの変更権限は配備ワークフローへ付与しない。

初期構築は[WIF公式手順](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)と[Cloud Run認証](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)に従う。認証に失敗したら条件や対象の誤りを確認し、JSON鍵や全公開へ迂回しない。

## 4. 手動ワークフロー

GitHub APIで`main`へ反映後、`.github/workflows/CloudRun配備.yml`を`main`に対して`workflow_dispatch`する。pushによる自動再配備は行わない。これは配備と実環境受入専用で、通常の単体試験の代行を含まない。

工程は次のとおり。

1. 確定したvariables、WIF、課金、API、IAM、既存Cloud Runサービスを監査する。
2. `src/`、package metadata、Dockerfile、固定依存だけをステージへ複製し、明示したビルドSAでCloud Buildへ送信する。
3. イメージを認証必須Cloud Runへ配備する。初回の生成元は`bootstrap.invalid`とし、実URL取得後に限定Host/Originへ更新する。
4. 最新ready revisionへtraffic 100%を固定し、実測したURL・サービス・region・revision・SHAを配備記録に保存する。
5. URLをaudienceとする短期ID tokenで実機受入を行う。tokenは環境変数だけに渡し、証拠やログへ出力しない。
6. 既定の`restart_acceptance=true`では新revisionを1回作り、旧traceの404と同sessionの再表現保留を実測する。メモリ状態の喪失を永続成立へ読み替えない。
7. Cloud LoggingとHTTP証拠を14日保持のartifactへ保存する。生成物をdefault treeへ追加しない。

Cloud Build、Artifact Registry、送信bucket、Logging、Cloud Runの課金は別に発生し得る。min 0 / max 1は費用抑制策であり金額の上限ではない。予算通知は必要に応じ本人の課金設定で追加する。常時起動・高負荷・複数instanceへ変更する前に実測と費用を再評価する。

HTTP応答を待つ枠を60秒から300秒へ延ばすことで、要求中のCPU・メモリ利用と費用を増やし得る。新候補の割当メモリを1Giから2Giにするため、同じ課金対象の稼働時間ならメモリのGiB秒は増加する。[Cloud Runの料金](https://cloud.google.com/run/pricing)はメモリ、CPU、要求などの利用量と課金設定によるため、総費用が2倍になるとは断定しない。CPU 1・min 0 / max 1・同時実行数1、IAM・権限・料金方式はこの変更では維持する。HTTPの時間上限はアプリ内部の処理停止や金額上限を保証しない。実機受入では固定SHA・revision・imageと2Gi・300秒設定、実HTTP所要時間、メモリ観測、本文・採否・ADK通過・監査・ログを対応させ、時間切れや不成立をPASSへ変更せず記録する。

## 5. ローカルと実機の受入

Google検索経路の本文供給は、従来の安全な公開HTTPS取得を共有し、`pypdf==6.20.1`によるPDF文字抽出を追加する。原PDFは2 MB以下、60頁以下、抽出文字150,000文字以下、子プロセス8秒以下。頁の内容ストリーム累計と各ストリームの展開には上限を置くが、16 MBをPDF全体の総メモリ上限とは扱わない。Linuxの子はアドレス空間512 MiBにも制限する。解析警告、文字のない頁、暗号化、不正PDF、上限超過は全体を取得失敗とし、欠落した部分本文を採用しない。OCR・図・表の視覚的意味は未対応。抽出方式、原本と抽出本文のSHA256、頁ごとの文字範囲を記録し、意味・条件・回答採否はHDSが判断する。通常の本文取得器は従来のPDF拒否を維持する。

依存固定の更新は`uv 0.13.0`で行う。Python 3.13 / Linux x86_64を解決対象とし、生成後にLinux用wheelがハッシュ付きで取得できることを検証する。

```powershell
uv pip compile deploy/requirements-cloud.in --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --generate-hashes --no-header --output-file deploy/requirements-cloud.txt
python -m pip install --require-hashes -r deploy/requirements-cloud.txt
python -m pip install --no-deps --no-build-isolation .
```

通常のHDSローカル限定入口は維持する。ADK接続のローカルE2Eは別ターミナルで起動し、結果をローカルと明記する。

```powershell
python -m minidora.製品版 --HDS --ADK --serve
python tools/CloudRun受入.py --環境 local --URL http://127.0.0.1:8080 --出力 .venv/cloud-evidence/local.json
```

実機の受入はworkflowの`deployment.json`または実gcloud観測から同形式の記録を作り、本人認証から取得した短期tokenで行う。配備記録の必須項目は`サービス`、`リージョン`、`リビジョン`、`URL`、40桁`実装SHA`、`認証必須: true`。CLIのtokenは表示しない。

```powershell
# GCP_PROJECT_ID・GCP_REGION・CLOUD_RUN_SERVICEは確定済みの環境変数。
$cloudUrl = (& gcloud run services describe $env:CLOUD_RUN_SERVICE --project=$env:GCP_PROJECT_ID --region=$env:GCP_REGION --format='value(status.url)')
if ($LASTEXITCODE -ne 0) { throw 'Cloud Run実URL取得失敗' }
$env:MINIDORA_ID_TOKEN = (& gcloud auth print-identity-token)
if ($LASTEXITCODE -ne 0) { throw '本人ID token取得失敗' }
try {
  python tools/CloudRun受入.py --環境 CloudRun --URL $cloudUrl --配備記録 .venv/cloud-evidence/deployment.json --basic-credentials-file .venv/cloud-evidence/private/basic-credentials.json --出力 .venv/cloud-evidence/cloud.json
} finally { Remove-Item Env:MINIDORA_ID_TOKEN }
```

検査はWeb UI、health、capabilities、ADK→HDS算術、同sessionでの再表現、資料登録・比較・条件訂正、サーバ検証と独立hash chain再計算、未知入力の保留または失敗、不正JSON・payload型・空入力・上限超過・別Origin拒否、Cloud Runの未認証拒否を含む。サンプルは既存公開試験の入出力を使う。hashの整合は回答内容の真実性や耐久保存を認定しない。

新revisionへ交換した後は、旧証拠を`--再起動前`で指定して状態境界を実測する。未実測なら証拠に未実施と記録する。URLの存在だけで全受入成立と宣言しない。

## 6. 完了判定

`docs/Codex指示書_CloudRun_ADK接続配備_2026-10-10.md`の完了条件を正とする。本人が許可したproject、認証必須の実Cloud Run URL、ADKの実経路、実HTTPとログ、公開境界・既存機能の確認、GitHub mainの固定SHAが必要。未認証・未配備・未実測の段階は「未完了：阻害条件」と明示する。永続会話が必要な用途は本工程のメモリ限定デモの成立範囲から区分する。

公式資料: [Cloud Run配備CLI](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy)、[Cloud Build送信CLI](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit)、[ADK 2.0](https://github.com/google/adk-docs/blob/main/docs/2.0/index.md)、[Google GitHub認証Action](https://github.com/google-github-actions/auth)。
