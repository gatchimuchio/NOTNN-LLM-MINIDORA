"""固定版のGLM重み目録を取得する。旧名入口の委譲先を復元。

JSONは保存済み監査資産と既存ワークフローが使用するv2交換形式を維持する。
内部処理名を日本語とし、Hugging Face・Git LFSの固定名を翻訳しない。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

識別文字 = "MINIDORA-GLM-D4-Audit/2.0"
次頁表現 = re.compile(r'<([^>]+)>;\s*rel="next"')


def JSONを取得(URL: str):
    要求 = urllib.request.Request(URL, headers={"User-Agent": 識別文字, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(要求, timeout=120) as 応答:
        return json.load(応答), 応答.headers.get("Link")


def 文章を取得(URL: str) -> str:
    要求 = urllib.request.Request(URL, headers={"User-Agent": 識別文字, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(要求, timeout=120) as 応答:
        return 応答.read().decode("utf-8", "replace")


def 全頁を取得(URL: str):
    結果, 既読 = [], set()
    while URL:
        if URL in 既読:
            raise RuntimeError("頁取得の循環を検出")
        既読.add(URL)
        資料, リンク = JSONを取得(URL)
        if not isinstance(資料, list):
            raise RuntimeError("ファイル木APIがリストを返していない")
        結果.extend(資料)
        一致 = 次頁表現.search(リンク or "")
        URL = 一致.group(1) if 一致 else None
    return 結果


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
    情報, _ = JSONを取得(f"https://huggingface.co/api/models/{リポジトリ}")
    版 = 情報["sha"]
    木 = 全頁を取得(f"https://huggingface.co/api/models/{リポジトリ}/tree/{版}?recursive=true&expand=true")
    ファイル群 = sorted((項目 for 項目 in 木 if 項目.get("type") == "file" and 項目.get("path", "").endswith(".safetensors")), key=lambda 項目: 項目["path"])
    行群 = []
    for 番号, 項目 in enumerate(ファイル群, 1):
        経路 = 項目["path"]
        LFS = 項目.get("lfs") or {}
        SHA256 = LFS.get("oid") or LFS.get("sha256")
        大きさ = LFS.get("size") or 項目.get("size")
        if not SHA256 or not 大きさ:
            補完SHA, 補完長 = LFS情報を取得(リポジトリ, 版, 経路)
            SHA256, 大きさ = SHA256 or 補完SHA, 大きさ or 補完長
        if not SHA256 or not 大きさ:
            raise RuntimeError(f"上流SHA256または大きさが未確定: {リポジトリ}:{経路}")
        行群.append({"id": f"{番号:04d}", "slug": 略称, "repo": リポジトリ, "mirror_repo": ミラー,
                    "revision": 版, "path": 経路, "sha256": str(SHA256).removeprefix("sha256:"), "size": int(大きさ)})
    if not 行群:
        raise RuntimeError(f"safetensorsが存在しない: {リポジトリ}")
    目録 = {"schema": "minidora.glm.weight_manifest.v2", "repo": リポジトリ, "mirror_repo": ミラー,
            "revision": 版, "slug": 略称, "tree_entries": len(木), "shards": 行群}
    出力 = Path(出力先)
    出力.parent.mkdir(parents=True, exist_ok=True)
    出力.write_text(json.dumps(目録, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{リポジトリ} 固定版={版} 木の項目数={len(木)} safetensors={len(行群)}")


def main():
    解析器 = argparse.ArgumentParser(description="固定版GLM重みの全頁目録を取得")
    解析器.add_argument("--repo", dest="リポジトリ", required=True)
    解析器.add_argument("--mirror-repo", dest="ミラー", required=True)
    解析器.add_argument("--slug", dest="略称", required=True)
    解析器.add_argument("--out", dest="出力先", required=True)
    引数 = 解析器.parse_args()
    目録を作る(引数.リポジトリ, 引数.ミラー, 引数.略称, 引数.出力先)


if __name__ == "__main__":
    main()
