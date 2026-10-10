# MINIDORA Cloud Run＋Google ADK配備

既存製品のUIとAPIからGoogle ADK 2.11.0の`Workflow/FunctionNode`を通り、同じHDS製品入口を呼ぶ。回答・意味判断・状態保持は既存MINIDORAが担当する。Geminiや外部LLMによる回答生成・フォールバックは使わない。ADK依存の`google-genai`はライブラリ構成上の依存であり、モデル呼出しの証拠ではない。

この文書は再現手順である。配備・実機受入の成立は、実際のCloud Run URLに対する`tools/CloudRun受入.py`の証拠と配備記録で判断する。ローカル成功だけでは第1工程完了にならない。

## 1. 実行境界

- `deploy/Dockerfile`はPython 3.13、ハッシュ付き固定依存、非rootユーザー、単一Pythonプロセスで既存UIを配布する。
- 起動は`python -m minidora.製品版 --HDS --ADK --CloudRun --serve`。`PORT`で`0.0.0.0`へバインドする。
- Cloud Run IAM認証を必須にし、アプリは`MINIDORA_CLOUD_HOSTS`と`MINIDORA_CLOUD_ORIGINS`を別途検査する。Origin・Host検査自体は本人認証ではない。ワイルドカードCORSを使わない。
- 許可Hostは実測した`*.run.app`ホスト、許可Originはその`https://`生成元。初回は`bootstrap.invalid`を設定して実URLの要求を拒否し、サービスURLを取得してから更新する。Cloud Runの既定TCP起動検査を使う。
- 外部読取は無効。API本文上限256,000バイト、チャット入口のレート制限、セッション数の既存上限を維持する。Cloud Run同時実行数1を設定する。
- `min=0`、`max=1`、`min-instances=0`、`max-instances=1`、CPU 1、メモリ1Gi、要求上限60秒。メモリ値はADK依存を含む初期設定であり、実測した必要量としては扱わない。変更には理由と費用影響を記録する。
- 会話と追跡台帳はメモリ内だけで、停止・再起動・新revision・インスタンス交換で失われる。永続化、再起動をまたぐ会話継続、複数インスタンス間同期は未成立。Cloud Loggingは実行証拠であり、会話の復元用台帳ではない。
- 保存領域・Secret・サービスアカウントJSON鍵をコンテナへ渡さない。`.dockerignore`とCloud Build用の許可ファイル限定ステージで構築原料・評価データ・認証ファイルを送信対象から外す。

## 2. 本人が確定する対象

Google Cloudの本人が許可したプロジェクトを実際に確認し、以下をGitHub repository variablesへ設定する。未設定ならワークフローは配備前に停止する。値を推測して選ばない。

| variable | 確定する値 |
|---|---|
| `GCP_PROJECT_ID` | 課金が有効な許可済みproject ID |
| `GCP_REGION` | 許可されたCloud Run / Artifact Registry / Cloud Buildのregion |
| `CLOUD_RUN_SERVICE` | MINIDORA専用のCloud Runサービス名 |
| `GCP_ARTIFACT_REPOSITORY` | 同regionにあるDOCKER形式のArtifact Registry repository名 |
| `GCP_BUILD_BUCKET` | 同projectのCloud Build専用既存bucketの`gs://` URL |
| `GCP_RUNTIME_SERVICE_ACCOUNT` | 権限を付与しない専用実行SAのemail |
| `GCP_BUILD_SERVICE_ACCOUNT` | 専用ビルドSAのemail |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | 専用配備・検査SAのemail |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../locations/global/workloadIdentityPools/.../providers/...` |

実行・ビルド・配備SAは分離する。実行SAにはGoogle Cloud APIを呼ぶ権限を与えない。組織・folderからの継承権限も設定者が確認する。ワークフローはprojectと対象サービスへの直接付与、公開IAM、課金、API、repository形式を検査し、異常時は停止する。

必要APIは`run.googleapis.com`、`artifactregistry.googleapis.com`、`cloudbuild.googleapis.com`、`iamcredentials.googleapis.com`、`sts.googleapis.com`。本人によるログイン・課金アカウントの開設や同意・project選択が必要な場合は代理完了と扱わない。

## 3. IAMとWIF

長期JSON鍵を作らず、GitHub Actions OIDC＋Workload Identity Federationを使う。providerの条件は、実際に確認した数値の`repository_owner_id`と`repository_id`、`assertion.ref == 'refs/heads/main'`、`assertion.event_name == 'workflow_dispatch'`に限定する。repository名の文字列だけでは識別しない。`google.subject=assertion.sub`と必要な数値属性をmappingし、該当repositoryの`principalSet`だけに配備SAへの`roles/iam.workloadIdentityUser`を付与する。

権限は初期構築時に必要な対象へ絞って設定する。projectのOwner / Editorや全SAへの偽装権限を配備SAに与えない。

| 主体 | 必要な範囲 |
|---|---|
| 実行SA | API権限なし。Cloud Runによるstdout/stderr採取はアプリのLogging API権限を要しない |
| ビルドSA | 選択repositoryのArtifact Registry Writer、選択bucketのStorage Object Admin＋Legacy Bucket Reader（Cloud Buildのbucketメタデータ読取）、ビルドログ用権限 |
| 配備SA | Cloud Buildの作成・取得、選択bucketの送信、選択repositoryの読取、対象サービスの配備・IAM変更・検査・ログ読取 |
| 配備SAのSA利用 | 明示した実行SAとビルドSAに対する`roles/iam.serviceAccountUser`だけ |
| WIF主体 | 明示した配備SAへの`roles/iam.workloadIdentityUser`だけ。ID token発行権限を必要なSAに限定 |
| 検証呼出し | 対象サービスの`roles/run.invoker`を配備SAに付与。`allUsers` / `allAuthenticatedUsers`には付与しない |

新規サービスを作る配備権限はprojectで必要になるため、専用projectまたは必要permissionだけのcustom roleを使う。`roles/run.admin`等の既定roleを使う場合も対象projectに限定し、作成後に対象サービスへの範囲縮小を検討する。監査にはproject IAM読取、課金状態読取、API一覧読取が必要。実行SA・組織ポリシーの変更権限は配備ワークフローへ付与しない。

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

## 5. ローカルと実機の受入

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
  python tools/CloudRun受入.py --環境 CloudRun --URL $cloudUrl --配備記録 .venv/cloud-evidence/deployment.json --出力 .venv/cloud-evidence/cloud.json
} finally { Remove-Item Env:MINIDORA_ID_TOKEN }
```

検査はWeb UI、health、capabilities、ADK→HDS算術、同sessionでの再表現、資料登録・比較・条件訂正、サーバ検証と独立hash chain再計算、未知入力の保留または失敗、不正JSON・payload型・空入力・上限超過・別Origin拒否、Cloud Runの未認証拒否を含む。サンプルは既存公開試験の入出力を使う。hashの整合は回答内容の真実性や耐久保存を認定しない。

新revisionへ交換した後は、旧証拠を`--再起動前`で指定して状態境界を実測する。未実測なら証拠に未実施と記録する。URLの存在だけで全受入成立と宣言しない。

## 6. 完了判定

`docs/Codex指示書_CloudRun_ADK接続配備_2026-10-10.md`の完了条件を正とする。本人が許可したproject、認証必須の実Cloud Run URL、ADKの実経路、実HTTPとログ、公開境界・既存機能の確認、GitHub mainの固定SHAが必要。未認証・未配備・未実測の段階は「未完了：阻害条件」と明示する。永続会話が必要な用途は本工程のメモリ限定デモの成立範囲から区分する。

公式資料: [Cloud Run配備CLI](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy)、[Cloud Build送信CLI](https://docs.cloud.google.com/sdk/gcloud/reference/builds/submit)、[ADK 2.0](https://github.com/google/adk-docs/blob/main/docs/2.0/index.md)、[Google GitHub認証Action](https://github.com/google-github-actions/auth)。
