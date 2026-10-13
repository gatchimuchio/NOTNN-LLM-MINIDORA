"""固定設定と実describeを照合する。認証・配備・予算初期化は行わない。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from minidora.製品版.Google起動構成 import Google固定設定を読む
from minidora.製品版.api import HTTPBasic許可値


固定設定名 = frozenset({
    "MINIDORA_GOOGLE_PROJECT_ID", "MINIDORA_GOOGLE_SEARCH_APP_ID",
    "MINIDORA_GOOGLE_RUNTIME_SERVICE_ACCOUNT", "MINIDORA_GOOGLE_PUBLIC_HOSTS",
    "MINIDORA_GOOGLE_BUDGET_ID", "MINIDORA_GOOGLE_BUDGET_BUCKET", "MINIDORA_GOOGLE_BUDGET_OBJECT",
    "MINIDORA_GOOGLE_BUDGET_START_UTC", "MINIDORA_GOOGLE_BUDGET_END_UTC", "MINIDORA_GOOGLE_BUDGET_LIMIT",
    "MINIDORA_RETRIEVAL_POLICY"})


def 固定を検査(設定, プロジェクト, リージョン, 実行SA):
    if type(設定) is not dict or set(設定) != 固定設定名 or 設定["MINIDORA_RETRIEVAL_POLICY"] != "auto":
        raise ValueError("固定取得設定の項目又は方針が不一致")
    予算, _, SA = Google固定設定を読む(設定)
    if (プロジェクト != "minidora-507702" or リージョン != "asia-northeast1"
            or プロジェクト != 予算.プロジェクトID or 実行SA != SA):
        raise ValueError("本人が確定した配備対象と固定取得設定が不一致")
    return 予算


def 審査認証を検査(設定):
    鍵 = {"MINIDORA_HTTP_BASIC_USERNAME", "MINIDORA_HTTP_BASIC_PASSWORD_SHA256"}
    if type(設定) is not dict or set(設定) != 鍵:
        raise ValueError("審査用HTTP Basicの固定2項目が必要です")
    HTTPBasic許可値(設定, 必須=True)
    return 設定


def サービスIAMを検査(IAM, *, 審査公開=False):
    if type(審査公開) is not bool:
        raise ValueError("審査公開はbool")
    公開行 = [行 for 行 in IAM.get("bindings", [])
             if set(行.get("members", [])) & {"allUsers", "allAuthenticatedUsers"}]
    if 審査公開:
        if (len(公開行) != 1 or 公開行[0].get("role") != "roles/run.invoker"
                or set(公開行[0].get("members", [])) != {"allUsers"}
                or 公開行[0].get("condition")):
            raise ValueError("承認後の公開IAMはallUsersのrun.invoker一付与に限定します")
    elif 公開行:
        raise ValueError("承認前のサービスIAMは本人認証を維持してください")


def 実行環境(設定, URL="https://bootstrap.invalid", *, 審査認証=None):
    認証 = 審査認証を検査(審査認証)
    値 = urlsplit(URL)
    if (値.scheme != "https" or 値.username or 値.password or 値.port is not None
            or 値.path or 値.query or 値.fragment or not 値.hostname
            or any(not re.fullmatch(r"(?!-)[a-z0-9-]{1,63}(?<!-)", 部分) for 部分 in 値.hostname.split("."))
            or (値.hostname != "bootstrap.invalid" and not 値.hostname.endswith(".run.app"))):
        raise ValueError("配備で取得したCloud Run URLが不正")
    return {**設定, **認証, "MINIDORA_CLOUD_HOSTS": 値.hostname, "MINIDORA_CLOUD_ORIGINS": URL,
            "MINIDORA_HTTP_LOG": "0"}


def 限定IAMを検査(設定, プロジェクトIAM, サービスIAM, バケットIAM, 検索役割, 予算役割, *, 審査公開=False):
    サービスIAMを検査(サービスIAM, 審査公開=審査公開)
    予算, _, SA = Google固定設定を読む(設定)
    実行 = "serviceAccount:" + SA
    期限 = "request.time < timestamp('" + 設定["MINIDORA_GOOGLE_BUDGET_END_UTC"] + "')"
    検索名 = "projects/" + 予算.プロジェクトID + "/roles/minidoraNormalSearch"
    予算名 = "projects/" + 予算.プロジェクトID + "/roles/minidoraSearchBudget"
    for 値, 名前, 権限 in ((検索役割, 検索名, {"discoveryengine.servingConfigs.search", "serviceusage.services.use"}),
                            (予算役割, 予算名, {"storage.objects.get", "storage.objects.create", "storage.objects.delete"})):
        if 値.get("name") != 名前 or 値.get("deleted") or set(値.get("includedPermissions", [])) != 権限:
            raise ValueError("限定roleの実権限が不一致")
    保存式 = ("resource.name == 'projects/_/buckets/" + 予算.保存先.バケット + "/objects/"
              + 予算.保存先.オブジェクト + "' && " + 期限)
    for policy, 名称, 許可役割, 条件 in ((プロジェクトIAM, "project", 検索名, 期限),
                                         (サービスIAM, "service", None, None),
                                         (バケットIAM, "budget", 予算名, 保存式)):
        実行付与 = []
        for 行 in policy.get("bindings", []):
            if set(行.get("members", [])) & {"allUsers", "allAuthenticatedUsers"}:
                if 名称 != "service" or not 審査公開:
                    raise ValueError("公開IAM付与が残存: " + 名称)
            if 実行 in 行.get("members", []):
                実行付与.append(行)
        if 許可役割 is None:
            if 実行付与:
                raise ValueError("実行SAの不要なservice権限が残存")
        elif (len(実行付与) != 1 or 実行付与[0].get("role") != 許可役割
                or 実行付与[0].get("condition", {}).get("expression") != 条件):
            raise ValueError("実行SAの限定role又は期限・object条件が不一致: " + 名称)


def 配備記録(サービス, IAM, 設定, *, 名前, リージョン, 実装SHA, イメージ, 実行SA, 交換前=None,
         審査認証=None, 審査公開=False):
    審査認証を検査(審査認証)
    サービスIAMを検査(IAM, 審査公開=審査公開)
    予算 = 固定を検査(設定, 設定["MINIDORA_GOOGLE_PROJECT_ID"], リージョン, 実行SA)
    if not re.fullmatch(r"[a-f0-9]{40}", 実装SHA):
        raise ValueError("実装SHAが不正")
    revision = サービス["status"]["latestReadyRevisionName"]
    if (not re.fullmatch(r"[1-9][0-9]*", str(サービス["metadata"].get("generation", "")))
            or サービス["status"].get("latestCreatedRevisionName") != revision
            or サービス["status"].get("observedGeneration") != サービス["metadata"].get("generation")
            or not any(行.get("type") == "Ready" and 行.get("status") == "True"
                       for 行 in サービス["status"].get("conditions", []))):
        raise ValueError("最新templateとReady revisionの観測が未一致")
    active = [行 for 行 in サービス["status"]["traffic"] if 行.get("percent", 0)]
    if (サービス["metadata"]["name"] != 名前 or len(active) != 1
            or active[0].get("revisionName") != revision or active[0]["percent"] != 100):
        raise ValueError("指定サービス・revisionへの100% trafficが未成立")
    annotations = サービス["metadata"].get("annotations", {})
    if annotations.get("run.googleapis.com/invoker-iam-disabled") == "true":
        raise ValueError("IAM検査の無効化は許可しません")
    if any("serviceAccount:" + 実行SA in 行.get("members", []) for 行 in IAM.get("bindings", [])):
        raise ValueError("実行SAの不要なservice権限が残存")
    if サービス["metadata"].get("labels", {}).get("minidora-source") != 実装SHA:
        raise ValueError("実サービスの実装SHA表示が不一致")
    template = サービス["spec"]["template"]
    spec = template["spec"]
    revision_annotations = template.get("metadata", {}).get("annotations", {})
    containers = spec.get("containers", [])
    if len(containers) != 1:
        raise ValueError("単一containerが不成立")
    container = containers[0]
    if spec.get("volumes") or container.get("volumeMounts") or any(行.get("valueFrom") for 行 in container.get("env", [])):
        raise ValueError("未承認volume又はSecret参照が残存")
    observed = {"min": int(annotations.get("run.googleapis.com/minScale", "0")),
                "max": int(annotations.get("run.googleapis.com/maxScale", "0")),
                "concurrency": int(spec.get("containerConcurrency", 0))}
    if (observed != {"min": 0, "max": 1, "concurrency": 1}
            or int(revision_annotations.get("autoscaling.knative.dev/minScale", "0")) != 0
            or int(revision_annotations.get("autoscaling.knative.dev/maxScale", "0")) != 1):
        raise ValueError("instance/concurrency境界が不一致")
    limits = container.get("resources", {}).get("limits", {})
    if (spec.get("serviceAccountName") != 実行SA or container.get("image") != イメージ
            or spec.get("timeoutSeconds") != 300 or limits.get("memory") not in ("2Gi", "2048Mi")
            or limits.get("cpu") not in ("1", "1000m")
            or revision_annotations.get("run.googleapis.com/startup-cpu-boost") != "false"
            or revision_annotations.get("run.googleapis.com/cpu-throttling") != "true"):
        raise ValueError("実行SA・image・資源又は要求単位CPUが不一致")
    if (container.get("command") != ["python"]
            or container.get("args") != ["-m", "minidora.製品版", "--HDS", "--ADK", "--基本チャット", "--CloudRun", "--serve"]):
        raise ValueError("ADK/HDS基本チャット起動引数が不一致")
    expected = 実行環境(設定, サービス["status"]["url"], 審査認証=審査認証)
    env_rows = container.get("env", [])
    env = {行["name"]: 行.get("value") for 行 in env_rows}
    if len(env) != len(env_rows) or any(env.get(鍵) != 値 for 鍵, 値 in expected.items()):
        raise ValueError("実URL又はGoogle固定環境設定が不一致")
    if set(env) - set(expected) - {"MINIDORA_ACCEPTANCE_RESTART"}:
        raise ValueError("未確認の環境設定が残存")
    if 交換前 is not None and (revision == 交換前["リビジョン"] or 交換前["実装SHA"] != 実装SHA
                               or 交換前["Google予算設定SHA256"] != 予算.設定SHA256):
        raise ValueError("revision交換又は同版・同予算設定が不成立")
    return {"サービス": 名前, "リージョン": リージョン, "リビジョン": revision,
            "URL": サービス["status"]["url"], "実装SHA": 実装SHA, "認証必須": True,
            "利用者認証": "HTTP Basic", "審査公開": 審査公開, "CloudIAM本人認証必須": not 審査公開,
            "イメージ": container["image"], "実行SA": spec["serviceAccountName"], **observed,
            "要求timeout秒": spec["timeoutSeconds"], "memory": limits["memory"], "CPU": limits["cpu"],
            "起動CPU増強": revision_annotations["run.googleapis.com/startup-cpu-boost"],
            "要求単位CPU": revision_annotations["run.googleapis.com/cpu-throttling"],
            "Google予算設定SHA256": 予算.設定SHA256, "固定環境照合": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--設定", default="deploy/Google取得固定設定.json")
    parser.add_argument("--サービス記録", required=True)
    parser.add_argument("--IAM記録", required=True)
    parser.add_argument("--名前", required=True)
    parser.add_argument("--リージョン", required=True)
    parser.add_argument("--実装SHA", required=True)
    parser.add_argument("--イメージ", required=True)
    parser.add_argument("--実行SA", required=True)
    parser.add_argument("--交換前")
    parser.add_argument("--審査認証設定", required=True, help="usernameとSHA256のみの固定JSON。平文passwordは禁止")
    parser.add_argument("--審査公開", action="store_true", help="ユーザー承認後のallUsers run.invoker状態を検査")
    parser.add_argument("--出力", required=True)
    args = parser.parse_args()
    def 読む(path): return json.loads(Path(path).read_text(encoding="utf-8"))
    value = 配備記録(読む(args.サービス記録), 読む(args.IAM記録), 読む(args.設定),
                     名前=args.名前, リージョン=args.リージョン, 実装SHA=args.実装SHA,
                     イメージ=args.イメージ, 実行SA=args.実行SA, 交換前=読む(args.交換前) if args.交換前 else None,
                     審査認証=読む(args.審査認証設定), 審査公開=args.審査公開)
    Path(args.出力).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
