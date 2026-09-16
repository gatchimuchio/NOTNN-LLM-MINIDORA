"""重みを範囲取得し、SHA256とsafetensorsの区間被覆を監査する。

旧実装の取得・検証条件を保持し、日本語の委譲先を復元したもの。
JSONは保存済み監査資産と既存ワークフローが使用するv1交換形式を維持する。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import urllib.parse
import urllib.request

識別文字 = "MINIDORA-GLM-D4-Audit/1.0"
範囲長 = 64 * 1024 * 1024
型別長 = {
    "BOOL": 1, "U8": 1, "I8": 1, "F8_E4M3": 1, "F8_E5M2": 1,
    "I16": 2, "U16": 2, "F16": 2, "BF16": 2, "I32": 4, "U32": 4,
    "F32": 4, "I64": 8, "U64": 8, "F64": 8,
}


def JSONを取得(URL: str):
    要求 = urllib.request.Request(URL, headers={"User-Agent": 識別文字, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(要求, timeout=120) as 応答:
        return json.load(応答)


def 文章を取得(URL: str) -> str:
    要求 = urllib.request.Request(URL, headers={"User-Agent": 識別文字, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(要求, timeout=120) as 応答:
        return 応答.read().decode("utf-8", "replace")


def LFS情報を取得(リポジトリ: str, 版: str, 経路: str):
    符号化経路 = urllib.parse.quote(経路, safe="/")
    文章 = 文章を取得(f"https://huggingface.co/{リポジトリ}/raw/{版}/{符号化経路}")
    SHA256 = 大きさ = None
    for 行 in 文章.splitlines():
        if 行.startswith("oid sha256:"):
            SHA256 = 行.split(":", 1)[1].strip()
        elif 行.startswith("size "):
            大きさ = int(行.split()[1])
    return SHA256, 大きさ


def 目録を作る(リポジトリ: str, ミラー: str, 略称: str, 出力先: str):
    情報 = JSONを取得(f"https://huggingface.co/api/models/{リポジトリ}")
    版 = 情報["sha"]
    木 = JSONを取得(f"https://huggingface.co/api/models/{リポジトリ}/tree/{版}?recursive=true&expand=true")
    行群 = []
    ファイル群 = sorted((項目 for 項目 in 木 if 項目.get("type") == "file" and 項目.get("path", "").endswith(".safetensors")), key=lambda 項目: 項目["path"])
    for 番号, 項目 in enumerate(ファイル群, 1):
        経路 = 項目["path"]
        LFS = 項目.get("lfs") or {}
        SHA256, 大きさ = LFS.get("oid") or LFS.get("sha256"), LFS.get("size") or 項目.get("size")
        if not SHA256 or not 大きさ:
            補完SHA, 補完長 = LFS情報を取得(リポジトリ, 版, 経路)
            SHA256, 大きさ = SHA256 or 補完SHA, 大きさ or 補完長
        if not SHA256 or not 大きさ:
            raise RuntimeError(f"上流SHA256または大きさが未確定: {リポジトリ}:{経路}")
        行群.append({"id": f"{番号:04d}", "slug": 略称, "repo": リポジトリ, "mirror_repo": ミラー,
                    "revision": 版, "path": 経路, "sha256": str(SHA256).removeprefix("sha256:"), "size": int(大きさ)})
    if not 行群:
        raise RuntimeError(f"safetensorsが存在しない: {リポジトリ}")
    出力 = {"repo": リポジトリ, "mirror_repo": ミラー, "revision": 版, "slug": 略称, "shards": 行群}
    Path(出力先).parent.mkdir(parents=True, exist_ok=True)
    Path(出力先).write_text(json.dumps(出力, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(行群, ensure_ascii=False, separators=(",", ":")))


def URL群(仕様):
    経路 = urllib.parse.quote(仕様["path"], safe="/")
    リポジトリ, 版, ミラー = 仕様["repo"], 仕様["revision"], 仕様.get("mirror_repo")
    群 = [f"https://huggingface.co/{リポジトリ}/resolve/{版}/{経路}?download=true"]
    if ミラー:
        群 += [f"https://modelscope.cn/models/{ミラー}/resolve/master/{経路}",
               f"https://www.modelscope.cn/models/{ミラー}/resolve/master/{経路}"]
    return 群


def 範囲を取得(URL: str, 始点: int, 終点: int):
    ヘッダ = {"User-Agent": 識別文字, "Accept-Encoding": "identity", "Range": f"bytes={始点}-{終点}"}
    return urllib.request.urlopen(urllib.request.Request(URL, headers=ヘッダ), timeout=180)


def 断片を監査(仕様):
    期待長, 期待SHA = int(仕様["size"]), 仕様["sha256"].lower()
    算出器 = hashlib.sha256()
    ヘッダ列 = bytearray()
    必要長 = None
    総量 = 0
    出典 = None
    開始時刻 = time.time()
    候補URL = URL群(仕様)
    for 始点 in range(0, 期待長, 範囲長):
        終点 = min(期待長 - 1, 始点 + 範囲長 - 1)
        最後の例外, 区間完了 = None, False
        for 試行 in range(4):
            for URL in 候補URL:
                try:
                    with 範囲を取得(URL, 始点, 終点) as 応答:
                        状態 = getattr(応答, "status", None)
                        読取量 = 0
                        while True:
                            塊 = 応答.read(8 * 1024 * 1024)
                            if not 塊:
                                break
                            読取量 += len(塊)
                            算出器.update(塊)
                            総量 += len(塊)
                            if 必要長 is None or len(ヘッダ列) < 必要長:
                                今回必要 = (必要長 - len(ヘッダ列)) if 必要長 else (8 - len(ヘッダ列))
                                if 今回必要 > 0:
                                    ヘッダ列.extend(塊[:今回必要])
                                if 必要長 is None and len(ヘッダ列) >= 8:
                                    ヘッダ長 = struct.unpack("<Q", bytes(ヘッダ列[:8]))[0]
                                    if ヘッダ長 <= 0 or ヘッダ長 > 512 * 1024 * 1024:
                                        raise RuntimeError(f"safetensorsのヘッダ長不正: {ヘッダ長}")
                                    必要長 = 8 + ヘッダ長
                                    if len(ヘッダ列) < 必要長:
                                        残量 = 必要長 - len(ヘッダ列)
                                        ヘッダ列.extend(塊[今回必要:今回必要 + 残量])
                                elif 必要長 and len(ヘッダ列) < 必要長:
                                    残量 = 必要長 - len(ヘッダ列)
                                    ヘッダ列.extend(塊[今回必要:今回必要 + 残量])
                        要求長 = 終点 - 始点 + 1
                        if 状態 == 206 and 読取量 != 要求長:
                            raise RuntimeError(f"範囲読取量不足: {読取量} != {要求長}")
                        if 状態 == 200:
                            if 始点 != 0 or 読取量 != 期待長:
                                raise RuntimeError(f"Rangeが無視された: 状態=200 始点={始点} バイト数={読取量}")
                            出典, 区間完了 = URL, True
                            break
                        if 状態 != 206:
                            raise RuntimeError(f"予期しないHTTP状態: {状態}")
                        出典, 区間完了 = URL, True
                        break
                except Exception as 例外:
                    最後の例外 = f"{type(例外).__name__}: {例外} @ {URL}"
            if 区間完了:
                break
            time.sleep(min(20, 2 ** 試行))
        if not 区間完了:
            raise RuntimeError(f"範囲取得失敗 {始点}-{終点}: {最後の例外}")
        if 総量 == 期待長:
            break
    実測SHA = 算出器.hexdigest()
    if 総量 != 期待長:
        raise RuntimeError(f"バイト数不一致: {総量} != {期待長}")
    if 実測SHA != 期待SHA:
        raise RuntimeError(f"sha256不一致: {実測SHA} != {期待SHA}")
    if 必要長 is None or len(ヘッダ列) < 必要長:
        raise RuntimeError("safetensorsヘッダ不完全")
    ヘッダ長 = struct.unpack("<Q", bytes(ヘッダ列[:8]))[0]
    ヘッダ = json.loads(bytes(ヘッダ列[8:8 + ヘッダ長]).decode("utf-8"))
    テンソル群 = []
    for 名称, 情報 in ヘッダ.items():
        if 名称 == "__metadata__":
            continue
        オフセット = 情報.get("data_offsets")
        if not isinstance(オフセット, list) or len(オフセット) != 2:
            raise RuntimeError(f"オフセット不正: {名称}")
        a, b = map(int, オフセット)
        型, 形状 = 情報.get("dtype"), 情報.get("shape", [])
        要素数 = 1
        for 次元 in 形状:
            要素数 *= int(次元)
        要素長 = 型別長.get(型)
        if 要素長 is not None and b - a != 要素数 * 要素長:
            raise RuntimeError(f"テンソル長不一致: {名称}: {b-a} != {要素数*要素長}")
        テンソル群.append((a, b, 名称, 型, 形状))
    テンソル群.sort()
    現位置, 欠落, 重複 = 0, [], []
    for a, b, 名称, 型, 形状 in テンソル群:
        if a > 現位置:
            欠落.append((現位置, a, 名称))
        if a < 現位置:
            重複.append((a, 現位置, 名称))
        現位置 = max(現位置, b)
    本体長 = 期待長 - (8 + ヘッダ長)
    if 現位置 < 本体長:
        欠落.append((現位置, 本体長, "EOF"))
    if 現位置 > 本体長:
        重複.append((本体長, 現位置, "OUT_OF_RANGE"))
    if 欠落 or 重複:
        raise RuntimeError(f"本体の被覆失敗 欠落={欠落[:5]} 重複={重複[:5]}")
    # 保存済み監査交換形式v1の固定鍵。内部の出典概念をこの原語へ移さない。
    return {
        "schema": "minidora.glm.weight_payload_audit.v1",
        "repo": 仕様["repo"], "revision": 仕様["revision"], "path": 仕様["path"],
        "expected_size": 期待長, "bytes_read": 総量,
        "expected_sha256": 期待SHA, "actual_sha256": 実測SHA, "sha256_match": True,
        "header_bytes": 8 + ヘッダ長, "tensor_count": len(テンソル群),
        "payload_bytes": 本体長, "no_gaps": True, "no_overlaps": True, "source_url": 出典,
        "elapsed_seconds": round(time.time() - 開始時刻, 3), "status": "PASS",
    }


def 断片監査を保存(仕様JSON: str, 出力先: str):
    仕様 = json.loads(仕様JSON)
    結果 = 断片を監査(仕様)
    出力 = Path(出力先)
    出力.mkdir(parents=True, exist_ok=True)
    経路 = 出力 / f"{仕様['slug']}-{仕様['id']}.json"
    経路.write_text(json.dumps(結果, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(結果, ensure_ascii=False))


def 全数を集計(目録保存先: str, 結果保存先: str, 出力先: str):
    目録群 = [json.loads(経路.read_text(encoding="utf-8")) for 経路 in Path(目録保存先).glob("*.json")]
    結果群 = [json.loads(経路.read_text(encoding="utf-8")) for 経路 in Path(結果保存先).glob("*.json")]
    期待群 = {(断片["repo"], 断片["revision"], 断片["path"]): 断片 for 目録 in 目録群 for 断片 in 目録["shards"]}
    取得群 = {(結果["repo"], 結果["revision"], 結果["path"]): 結果 for 結果 in 結果群}
    欠落 = sorted([{"repo": 鍵[0], "revision": 鍵[1], "path": 鍵[2]} for 鍵 in 期待群.keys() - 取得群.keys()], key=lambda 項目: (項目["repo"], 項目["path"]))
    失敗 = [結果 for 結果 in 結果群 if 結果.get("status") != "PASS" or not 結果.get("sha256_match") or not 結果.get("no_gaps") or not 結果.get("no_overlaps")]
    リポジトリ別 = {}
    for 目録 in 目録群:
        リポジトリ = 目録["repo"]
        対象群 = [結果 for 結果 in 結果群 if 結果["repo"] == リポジトリ and 結果["revision"] == 目録["revision"]]
        リポジトリ別[リポジトリ] = {
            "revision": 目録["revision"], "expected_shards": len(目録["shards"]), "audited_shards": len(対象群),
            "bytes_read": sum(結果.get("bytes_read", 0) for 結果 in 対象群),
            "tensors": sum(結果.get("tensor_count", 0) for 結果 in 対象群),
            "pass": len(対象群) == len(目録["shards"]) and all(結果.get("status") == "PASS" for 結果 in 対象群),
        }
    要約 = {
        "schema": "minidora.glm.weight_payload_full_audit.v1",
        "status": "PASS" if not 欠落 and not 失敗 and len(取得群) == len(期待群) else "FAIL",
        "expected_shards": len(期待群), "audited_shards": len(取得群),
        "bytes_read": sum(結果.get("bytes_read", 0) for 結果 in 結果群),
        "tensor_count": sum(結果.get("tensor_count", 0) for 結果 in 結果群),
        "missing": 欠落, "failed": 失敗, "models": リポジトリ別,
    }
    Path(出力先).parent.mkdir(parents=True, exist_ok=True)
    Path(出力先).write_text(json.dumps(要約, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(要約, ensure_ascii=False, indent=2))
    if 要約["status"] != "PASS":
        raise SystemExit(1)


def main():
    from 標準入出力 import 標準出力をUTF8化

    標準出力をUTF8化()
    解析器 = argparse.ArgumentParser(description="GLM重みの範囲取得・同一性・被覆監査")
    副命令 = 解析器.add_subparsers(dest="命令", required=True)
    探索 = 副命令.add_parser("discover")
    探索.add_argument("--repo", dest="リポジトリ", required=True)
    探索.add_argument("--mirror-repo", dest="ミラー", required=True)
    探索.add_argument("--slug", dest="略称", required=True)
    探索.add_argument("--out", dest="出力先", required=True)
    監査 = 副命令.add_parser("audit-shard")
    監査.add_argument("--spec-env", dest="仕様環境変数", default="SHARD_SPEC")
    監査.add_argument("--out-dir", dest="出力先", required=True)
    集計 = 副命令.add_parser("aggregate")
    集計.add_argument("--manifest-dir", dest="目録保存先", required=True)
    集計.add_argument("--result-dir", dest="結果保存先", required=True)
    集計.add_argument("--output", dest="出力先", required=True)
    引数 = 解析器.parse_args()
    if 引数.命令 == "discover":
        目録を作る(引数.リポジトリ, 引数.ミラー, 引数.略称, 引数.出力先)
    elif 引数.命令 == "audit-shard":
        断片監査を保存(os.environ[引数.仕様環境変数], 引数.出力先)
    else:
        全数を集計(引数.目録保存先, 引数.結果保存先, 引数.出力先)


if __name__ == "__main__":
    main()
