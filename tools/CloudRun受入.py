"""公開HTTP契約を実URLで検査する。ローカル結果とCloud Run実測を区別する。"""
from __future__ import annotations

import argparse
from base64 import b64encode
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4


監査仕様版 = "MINIDORA-PRODUCT-GOVERNANCE-v1"
安全監査仕様版 = "MINIDORA-PRODUCT-GOVERNANCE-v2"


class 転送禁止(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def ハッシュ(値):
    return sha256(json.dumps(値, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")).hexdigest()


def 監査を検証(記録):
    """製品v1/v2の明示された交換契約から独立に再計算し、元記録は変換しない。"""
    try:
        版 = 記録["仕様版"]
        if (版 not in (監査仕様版, 安全監査仕様版)
                or not isinstance(記録["イベント"], list) or not 記録["イベント"]):
            return False
        前 = "0" * 64
        for 番号, 行 in enumerate(記録["イベント"], 1):
            if type(行["番号"]) is not int or 行["番号"] != 番号 or 行["前ハッシュ"] != 前:
                return False
            材料 = {"spec": 版, "追跡": 記録["追跡ID"], "n": 番号,
                    "stage": 行["段階"], "モジュール": 行["モジュール"], "version": 行["版"],
                    "input": 行["入力"], "output": 行["出力"], "証拠": 行["根拠"], "prev": 前}
            if ハッシュ(材料) != 行["ハッシュ"]:
                return False
            前 = 行["ハッシュ"]
        材料 = {"spec": 版, "追跡": 記録["追跡ID"], "session": 記録["セッションID"],
                "started": 記録["開始時刻"], "input": 記録["入力文"], "経路": 記録["経路"],
                "response": 記録["最終応答"], "status": 記録["状態"],
                "prev_response": 記録["前応答ハッシュ"], "last_event": 前}
        return ハッシュ(材料) == 記録["ルートハッシュ"]
    except (KeyError, TypeError, ValueError):
        return False


def 基本認証を読む(場所):
    """私有JSONのusername/passwordを読む。資格・符号化値は報告へ保存しない。"""
    try:
        値 = json.loads(Path(場所).read_text(encoding="utf-8"))
        名前, パスワード = 値["username"], 値["password"]
        if (type(名前) is not str or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", 名前)
                or type(パスワード) is not str or not パスワード):
            raise ValueError
        ヘッダ = "Basic " + b64encode((名前 + ":" + パスワード).encode("utf-8")).decode("ascii")
        if len(ヘッダ) > 1024:
            raise ValueError
        return ヘッダ, パスワード
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        raise ValueError("Basic資格ファイルは有効なusername/passwordを持つ私有JSONが必要") from None


def 身元tokenを読む(場所=None):
    try:
        値 = Path(場所).read_text(encoding="utf-8").strip() if 場所 else os.environ.get("MINIDORA_ID_TOKEN", "")
    except (OSError, UnicodeError):
        raise ValueError("OIDC tokenファイルを読めません") from None
    if 値 and not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", 値):
        raise ValueError("短期OIDC ID tokenを指定")
    return 値


def 認証ヘッダ(基本認証, 身元token, *, 認証=True, Basic状態="normal"):
    if not 認証:
        return {}
    ヘッダ = {}
    if 基本認証:
        if Basic状態 == "normal":
            ヘッダ["Authorization"] = 基本認証
        elif Basic状態 == "wrong":
            # NULを含むusernameは実設定の許可範囲外。正規資格を再利用しない。
            ヘッダ["Authorization"] = "Basic " + b64encode(b"\x00:invalid").decode("ascii")
        elif Basic状態 != "omit":
            raise ValueError("Basic検査状態が不正")
        if 身元token:
            ヘッダ["X-Serverless-Authorization"] = "Bearer " + 身元token
    elif 身元token:
        ヘッダ["Authorization"] = "Bearer " + 身元token
    return ヘッダ


def 秘密を伏せる(文, 秘密):
    for 値 in 秘密:
        if 値:
            文 = 文.replace(値, "[認証資格非表示]")
    return 文


def ADK通過か(応答):
    値 = 応答.get("metadata", {}).get("ADK", {})
    return (値.get("ライブラリ") == "google-adk" and 値.get("版") == "2.11.0"
            and 値.get("実行方式") == "Workflow/FunctionNode" and 値.get("通過") is True
            and 値.get("HDS呼出数") == 1 and bool(値.get("実行ID"))
            and 値.get("追跡ID") == 応答.get("追跡_id"))


def 条件を要求(条件, 理由):
    if not 条件:
        raise ValueError(理由)


def 配備を読む(場所, URL, *, 基本認証=False):
    値 = json.loads(Path(場所).read_text(encoding="utf-8"))
    必須 = {"サービス", "リージョン", "リビジョン", "URL", "実装SHA", "認証必須"}
    if not 必須 <= 値.keys() or any(not 値[鍵] for 鍵 in 必須):
        raise ValueError("配備記録の必須情報が不足")
    if 値["URL"].rstrip("/") != URL or 値["認証必須"] is not True:
        raise ValueError("配備記録と検査URL又は認証構成が不一致")
    if not re.fullmatch(r"[a-f0-9]{40}", 値["実装SHA"]):
        raise ValueError("配備記録の実装SHAが不正")
    認証欄 = {"利用者認証", "審査公開", "CloudIAM本人認証必須"}
    if 認証欄 & 値.keys():
        if (not 認証欄 <= 値.keys() or 値["利用者認証"] != "HTTP Basic" or not 基本認証
                or type(値["審査公開"]) is not bool or type(値["CloudIAM本人認証必須"]) is not bool
                or 値["CloudIAM本人認証必須"] is not (not 値["審査公開"])):
            raise ValueError("配備記録のBasic/IAM認証境界が不一致")
    return 値


def main():
    解析器 = argparse.ArgumentParser(description=__doc__)
    解析器.add_argument("--URL", required=True)
    解析器.add_argument("--環境", choices=("local", "CloudRun"), required=True)
    解析器.add_argument("--配備記録", help="実gcloud describeとIAM検査から作ったJSON")
    解析器.add_argument("--再起動前", help="異なるrevisionに配備する前の本受入JSON")
    解析器.add_argument("--出力", required=True)
    解析器.add_argument("--basic-credentials-file", type=Path, help="私有username/password JSON。資格は出力しない")
    解析器.add_argument("--token-file", type=Path, help="私有の短期OIDC token。省略時はMINIDORA_ID_TOKENを使用")
    引数 = 解析器.parse_args()
    URL = 引数.URL.rstrip("/")
    解析 = urlsplit(URL)
    if 解析.username or 解析.password or 解析.query or 解析.fragment or 解析.path:
        解析器.error("URLは認証情報・パス・query・fragmentなしの生成元に限定")
    クラウド = 引数.環境 == "CloudRun"
    if クラウド:
        if (解析.scheme != "https" or 解析.port is not None or not 解析.hostname
                or not 解析.hostname.endswith(".run.app")
                or any(not re.fullmatch(r"(?!-)[a-z0-9-]{1,63}(?<!-)", 部分) for 部分 in 解析.hostname.split("."))):
            解析器.error("CloudRun実測は実在するhttps://*.run.app生成元を指定")
        if not 引数.配備記録:
            解析器.error("CloudRun実測には配備記録が必要")
    elif 解析.scheme != "http" or 解析.hostname not in {"127.0.0.1", "localhost"}:
        解析器.error("local検査はhttp://127.0.0.1又はlocalhostに限定")
    try:
        基本認証, パスワード = 基本認証を読む(引数.basic_credentials_file) if 引数.basic_credentials_file else ("", "")
        配備 = 配備を読む(引数.配備記録, URL, 基本認証=bool(基本認証)) if クラウド else None
        IAM必須 = クラウド and 配備.get("CloudIAM本人認証必須", True)
        身元token = 身元tokenを読む(引数.token_file) if IAM必須 else ""
        if IAM必須 and not 身元token:
            raise ValueError("非公開CloudRun実測には短期OIDC ID tokenが必要")
        if クラウド and not IAM必須 and not 基本認証:
            raise ValueError("審査公開CloudRun実測にはBasic資格ファイルが必要")
    except (OSError, ValueError, TypeError) as 例外:
        解析器.error(str(例外))
    記録 = {"版": "MINIDORA-CloudRun受入-v1", "環境": 引数.環境, "URL": URL,
            "開始UTC": datetime.now(timezone.utc).isoformat(), "配備": 配備,
            "検査": [], "永続化": "未実装。インスタンス交換で会話・追跡を失う。"}
    記録["認証方式"] = ("HTTP Basic+Cloud Run IAM" if 基本認証 and IAM必須 else
                          "HTTP Basic" if 基本認証 else "Cloud Run IAM" if IAM必須 else "local")
    秘密 = tuple(値 for 値 in (パスワード, 基本認証, 基本認証.removeprefix("Basic "), 身元token) if 値)
    開く = build_opener(転送禁止()) if クラウド else build_opener(ProxyHandler({}), 転送禁止())

    def HTTP(経路, 内容=None, *, 生=None, 認証=True, 生成元=None, Basic状態="normal"):
        ヘッダ = 認証ヘッダ(基本認証, 身元token, 認証=認証, Basic状態=Basic状態)
        if 生成元 is not None:
            ヘッダ["Origin"] = 生成元
        本体 = json.dumps(内容, ensure_ascii=False).encode("utf-8") if 内容 is not None else 生
        if 本体 is not None:
            ヘッダ["Content-Type"] = "application/json"
        要求 = Request(URL + 経路, data=本体, headers=ヘッダ)
        try:
            with 開く.open(要求, timeout=360) as 応答:
                状態, 型, 実体 = 応答.status, 応答.headers.get("Content-Type", ""), 応答.read(1_000_001)
        except HTTPError as 例外:
            状態, 型, 実体 = 例外.code, 例外.headers.get("Content-Type", ""), 例外.read(1_000_001)
        if len(実体) > 1_000_000:
            raise ValueError("受信上限超過")
        本文 = 実体.decode("utf-8")
        本体 = json.loads(本文) if "application/json" in 型 else 本文
        表示 = json.dumps(本体, ensure_ascii=False) if isinstance(本体, (dict, list)) else str(本体)
        if any(値 in 表示 for 値 in 秘密):
            raise ValueError("応答に認証資格が含まれたため保存禁止")
        return 状態, 本体

    def 検査(名前, 処理):
        try:
            成立, 観測 = 処理()
            記録["検査"].append({"項目": 名前, "成立": bool(成立), "観測": 観測})
        except (URLError, TimeoutError, OSError, ValueError, TypeError, KeyError, AttributeError) as 例外:
            記録["検査"].append({"項目": 名前, "成立": False,
                                   "観測": {"失敗": type(例外).__name__, "理由": 秘密を伏せる(str(例外), 秘密)}})

    def GET検査(経路, 判定):
        状態, 本体 = HTTP(経路)
        return 状態 == 200 and 判定(本体), {"HTTP": 状態}

    検査("Web UI", lambda: GET検査("/", lambda 本体: isinstance(本体, str) and "<html" in 本体.lower()))
    検査("health", lambda: GET検査("/health", lambda 本体: 本体.get("ok") is True))
    検査("capabilities", lambda: GET検査("/api/capabilities", lambda 本体: bool(本体.get("capabilities"))))
    会話ID = "cloud-accept-" + uuid4().hex
    算術ID = "cloud-arithmetic-" + uuid4().hex
    記録["再起動検査用"] = {"セッションID": 算術ID}
    前ハッシュ = {}

    def チャット検査(入力, ID, *, 状態群=("APPROVE",), 含む=(), 含まない=()):
        状態, 応答 = HTTP("/api/chat", {"message": 入力, "session_id": ID}, 生成元=URL)
        条件を要求(状態 == 200, f"chat HTTP={状態}")
        条件を要求(応答["session_id"] == ID, "会話ID不一致")
        条件を要求(応答["status"] in 状態群, "採否状態不一致")
        条件を要求(応答["経路"] == "HDS通常運用" and ADK通過か(応答), "ADKからHDSの通過証拠が不成立")
        条件を要求(all(文 in 応答["response"] for 文 in 含む), "要求した内容が応答にない")
        条件を要求(all(文 not in 応答["response"] for 文 in 含まない), "失効した内容が応答に残存")
        追跡状態, 追跡 = HTTP("/api/trace/" + 応答["追跡_id"])
        条件を要求(追跡状態 == 200 and 追跡["valid"] is True, "追跡取得又はサーバ側監査検証が不成立")
        監査 = 追跡["追跡"]
        条件を要求(監査を検証(監査), "独立ハッシュ再計算が不一致")
        条件を要求(監査["追跡ID"] == 応答["追跡_id"], "追跡と応答のIDが不一致")
        条件を要求(監査["セッションID"] == ID and 監査["入力文"] == 入力, "追跡の入力又は会話IDが不一致")
        条件を要求(監査["ルートハッシュ"] == 応答["追跡_hash"], "追跡と応答のハッシュが不一致")
        条件を要求(監査["最終応答"] == 応答["response"] and 監査["状態"] == 応答["status"], "追跡と応答の内容が不一致")
        条件を要求(監査["前応答ハッシュ"] == 前ハッシュ.get(ID, ""), "会話応答間のハッシュ連鎖が不一致")
        前ハッシュ[ID] = 応答["追跡_hash"]
        if ID == 算術ID:
            記録["再起動検査用"]["追跡ID"] = 応答["追跡_id"]
        return True, {"HTTP": 状態, "追跡HTTP": 追跡状態, "状態": 応答["status"],
                      "応答": 応答["response"], "追跡ID": 応答["追跡_id"],
                      "監査ハッシュ": 応答["追跡_hash"], "前応答ハッシュ": 監査["前応答ハッシュ"],
                      "イベント数": len(監査["イベント"]), "独立ハッシュ検証": True,
                      "ADK": 応答["metadata"]["ADK"]}

    検査("ADKからHDS算術", lambda: チャット検査("2+3", 算術ID, 含む=("5",)))
    検査("連続依頼の再表現", lambda: チャット検査("詳しく説明して", 算術ID, 含む=("5",)))
    検査("資料A登録", lambda: チャット検査('資料「A」を登録:{"売上":75,"費用":50,"単位":"円"}', 会話ID))
    検査("資料B登録", lambda: チャット検査('資料「B」を登録:{"売上":60,"費用":40,"単位":"円"}', 会話ID))
    検査("同一会話の売上比較", lambda: チャット検査("この2つの売上を比較して", 会話ID, 含む=("-15円",)))
    検査("条件訂正", lambda: チャット検査("訂正:属性は費用です", 会話ID,
                                         含む=("-10円", "50円"), 含まない=("75円",)))
    検査("未知入力", lambda: チャット検査("未対応の能力を発明して", "cloud-unknown-" + uuid4().hex,
                                           状態群=("SUSPEND", "FAIL")))

    def 拒否検査(内容=None, *, 生=None, 生成元=URL):
        状態, 本体 = HTTP("/api/chat", 内容, 生=生, 生成元=生成元)
        return 400 <= 状態 < 500, {"HTTP": 状態, "拒否理由": 本体.get("error") if isinstance(本体, dict) else None}

    検査("不正JSON拒否", lambda: 拒否検査(生=b"{"))
    検査("不正payload型拒否", lambda: 拒否検査(生=b"[]"))
    検査("空入力拒否", lambda: 拒否検査({"message": "", "session_id": 会話ID}))
    検査("入力上限拒否", lambda: 拒否検査(生=b"x" * 256_001))
    検査("別Origin拒否", lambda: 拒否検査({"message": "2+3"}, 生成元="https://example.invalid"))
    if クラウド:
        def 未認証():
            観測 = []
            for 経路 in ("/", "/health", "/api/capabilities", "/api/trace/" + 記録["再起動検査用"]["追跡ID"]):
                状態, _ = HTTP(経路, 認証=False)
                観測.append({"経路": 経路, "HTTP": 状態})
            状態, _ = HTTP("/api/chat", {"message": "2+3"}, 認証=False)
            観測.append({"経路": "/api/chat", "HTTP": 状態})
            return all(行["HTTP"] in (401, 403) for 行 in 観測), 観測
        検査("未認証アクセス拒否", 未認証)
    else:
        記録["クラウド限定検査"] = "IAM未認証拒否・配備・再起動は未実施"
    if 基本認証:
        def Basic拒否(状態名):
            観測 = []
            経路群 = ("/", "/health", "/api/capabilities",
                      "/api/trace/" + 記録["再起動検査用"].get("追跡ID", "0" * 32), "/api/chat")
            for 経路 in 経路群:
                状態, _ = HTTP(経路, {"message": "2+3"} if 経路 == "/api/chat" else None,
                               生成元=URL, Basic状態=状態名)
                観測.append({"経路": 経路, "HTTP": 状態})
            return all(行["HTTP"] == 401 for 行 in 観測), 観測
        検査("Basic未指定拒否", lambda: Basic拒否("omit"))
        検査("Basic誤資格拒否", lambda: Basic拒否("wrong"))
    if 引数.再起動前:
        def 再起動検査():
            前回 = json.loads(Path(引数.再起動前).read_text(encoding="utf-8"))
            条件を要求(クラウド and 前回["環境"] == "CloudRun" and 前回["URL"] == URL, "再起動前後の実環境が不一致")
            条件を要求(前回["受入成立"] is True, "再起動前の受入が未成立")
            条件を要求(前回["配備"]["リビジョン"] != 配備["リビジョン"], "リビジョンが交換されていない")
            旧 = 前回["再起動検査用"]
            状態, _ = HTTP("/api/trace/" + 旧["追跡ID"])
            会話状態, 応答 = HTTP("/api/chat", {"message": "詳しく説明して", "session_id": 旧["セッションID"]}, 生成元=URL)
            成立 = 状態 == 404 and 会話状態 == 200 and 応答["status"] == "SUSPEND" and ADK通過か(応答)
            return 成立, {"旧リビジョン": 前回["配備"]["リビジョン"], "新リビジョン": 配備["リビジョン"],
                          "旧追跡HTTP": 状態, "再表現HTTP": 会話状態, "再表現状態": 応答["status"],
                          "会話永続成立": False, "観測": "新revisionでは旧会話・追跡を継承しない"}
        検査("インスタンス交換の状態境界", 再起動検査)
    else:
        記録["再起動実測"] = "未実施。再起動前の本JSONと新revisionで--再起動前を指定する。"
    記録["終了UTC"] = datetime.now(timezone.utc).isoformat()
    記録["受入成立"] = all(行["成立"] for 行 in 記録["検査"])
    記録["クラウド実測成立"] = クラウド and 記録["受入成立"]
    出力 = Path(引数.出力)
    出力.parent.mkdir(parents=True, exist_ok=True)
    出力.write_text(json.dumps(記録, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"環境": 引数.環境, "受入成立": 記録["受入成立"], "検査数": len(記録["検査"]),
                      "失敗": [行["項目"] for 行 in 記録["検査"] if not 行["成立"]], "証拠": str(出力)}, ensure_ascii=False))
    return 0 if 記録["受入成立"] else 1


if __name__ == "__main__":
    sys.exit(main())
