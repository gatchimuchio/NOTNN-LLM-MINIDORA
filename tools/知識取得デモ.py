"""SearXNG検索または明示URLからLIVE本文を取得する。固定回答は内蔵しない。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minidora.公開本文取得 import 公開URL
from minidora.知識取得 import 知識取得器, 知識取得要求
from minidora.製品版.型 import 参照資料
from minidora.製品版.検索 import SearXNG検索供給器


class _指定URL:
    """利用者の取得先指定。検索実行や保存済み本文の代替ではない。"""
    def __init__(self, urls):
        self.urls = tuple(公開URL(u) for u in urls)

    def 検索(self, query, limit=5):
        return tuple(参照資料(f"指定:{i}", u, "利用者指定URL", u) for i, u in enumerate(self.urls[:limit]))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--検索語", required=True)
    parser.add_argument("--必要語", nargs="+", required=True)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--searxng", default=None)
    parser.add_argument("--外部読取許可", action="store_true")
    args = parser.parse_args()
    try:
        request = 知識取得要求(args.検索語, tuple(args.必要語))
        request.検証()
        if args.url and args.searxng:
            raise ValueError("URL指定と検索接続先の同時指定は不可")
        provider = _指定URL(args.url) if args.url else SearXNG検索供給器(args.searxng)
        result = 知識取得器(provider).実行(request, 外部読取許可=args.外部読取許可)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"取得方式": "指定URL" if args.url else "SearXNG検索", "成立": result.成立,
                      "本文": result.本文, "保留理由": result.保留理由,
                      "参照": [r.辞書化() for r in result.参照], "記録": result.データ}, ensure_ascii=False, indent=2))
    return 0 if result.成立 else 2


if __name__ == "__main__":
    raise SystemExit(main())
