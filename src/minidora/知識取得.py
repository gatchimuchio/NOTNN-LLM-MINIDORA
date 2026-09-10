"""必要語の不足に応じて検索・本文取得・抜粋を行う。事実性の採否は行わない。"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Protocol
import unicodedata
from urllib.parse import urlsplit

from .公開本文取得 import 公開URL, 公開本文取得器, 取得本文
from .製品版.型 import 能力結果, 参照資料

知識取得版 = "MINIDORA-知識取得-v0.1"


class 検索供給器(Protocol):
    def 検索(self, query: str, limit: int = 5) -> tuple[参照資料, ...]: ...


class 本文供給器(Protocol):
    def 取得(self, url: str) -> 取得本文: ...


def _照合語(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


@dataclass(frozen=True, slots=True)
class 知識取得要求:
    検索語: str
    必要語: tuple[str, ...]
    最低資料数: int = 1
    最大検索回数: int = 3
    最大候補数: int = 5
    最大取得数: int = 8
    最大資料数: int = 4
    最大抜粋文字数: int = 12000
    優先ホスト: tuple[str, ...] = ()

    def 検証(self) -> None:
        if type(self.検索語) is not str or not self.検索語.strip() or len(self.検索語) > 512:
            raise ValueError("検索語不正")
        if type(self.必要語) is not tuple or not 1 <= len(self.必要語) <= 16:
            raise ValueError("必要語は1〜16語のtuple")
        for word in (self.検索語, *self.必要語):
            if type(word) is not str or not word.strip() or re.search(r"[\x00-\x1f\x7f]", word):
                raise ValueError("検索語・必要語の型または制御文字が不正")
            word.encode("utf-8")
        if any(len(w) > 80 or w != w.strip() for w in self.必要語):
            raise ValueError("必要語の長さまたは前後空白が不正")
        if len({_照合語(w) for w in self.必要語}) != len(self.必要語):
            raise ValueError("必要語重複")
        for name, upper in (("最低資料数", 8), ("最大検索回数", 8), ("最大候補数", 10),
                            ("最大取得数", 32), ("最大資料数", 8), ("最大抜粋文字数", 50000)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= upper:
                raise ValueError(f"{name}範囲不正")
        if not self.最低資料数 <= self.最大資料数 <= self.最大取得数:
            raise ValueError("資料数・取得数の上限矛盾")
        if type(self.優先ホスト) is not tuple or len(self.優先ホスト) > 16:
            raise ValueError("優先ホスト不正")
        for host in self.優先ホスト:
            if type(host) is not str or not host or any(c in host for c in "/?#@:"):
                raise ValueError("優先ホスト不正")
            if urlsplit(公開URL("https://" + host)).hostname != host:
                raise ValueError("優先ホストは正規化済みの完全ホスト名")


def _本文検証(doc: 取得本文, requested: str) -> None:
    if not isinstance(doc, 取得本文) or doc.要求URL != requested:
        raise ValueError("本文の要求先不一致")
    if 公開URL(doc.最終URL) != doc.最終URL:
        raise ValueError("最終URL不正")
    if type(doc.経路) is not tuple or not doc.経路 or doc.経路[0] != requested or doc.経路[-1] != doc.最終URL:
        raise ValueError("本文の取得経路不一致")
    if any(公開URL(u) != u for u in doc.経路) or len(set(doc.経路)) != len(doc.経路):
        raise ValueError("本文の取得経路不正")
    for text in (doc.題名, doc.本文, doc.取得時刻, doc.内容種別, doc.文字コード):
        if type(text) is not str:
            raise ValueError("本文メタデータ型不正")
    if not doc.本文.strip() or doc.本文SHA256 != sha256(doc.本文.encode("utf-8")).hexdigest():
        raise ValueError("本文内容の不一致")
    if not re.fullmatch(r"[0-9a-f]{64}", doc.転送SHA256):
        raise ValueError("転送hash不正")
    if datetime.fromisoformat(doc.取得時刻).utcoffset() is None:
        raise ValueError("取得時刻に時差が必要")
    if type(doc.転送バイト数) is not int or not 0 < doc.転送バイト数 <= 2_000_000:
        raise ValueError("本文サイズ不正")
    if type(doc.除外要素) is not tuple or any(type(x) is not str for x in doc.除外要素):
        raise ValueError("除外記録不正")


def _抜粋(doc: 取得本文, terms: tuple[str, ...], remaining: int) -> tuple[list[dict], set[str]]:
    """抽出本文の段落をそのまま保持。照合はNFKC/casefold部分一致に限定する。"""
    passages, covered = [], set()
    for match in re.finditer(r"[^\n]+", doc.本文):
        text = match[0]
        hits = [w for w in terms if _照合語(w) in _照合語(text)]
        if not hits or len(text) > remaining:
            continue
        passages.append({"開始": match.start(), "終了": match.end(), "本文": text, "一致語": hits})
        remaining -= len(text)
        covered.update(hits)
    return passages, covered


class 知識取得器:
    def __init__(self, 検索: 検索供給器, 本文: 本文供給器 | None = None):
        if not callable(getattr(検索, "検索", None)):
            raise ValueError("検索供給器が必要")
        self.検索 = 検索
        self.本文 = 本文 if 本文 is not None else 公開本文取得器()
        if not callable(getattr(self.本文, "取得", None)):
            raise ValueError("本文供給器が必要")

    def 実行(self, 要求: 知識取得要求, *, 外部読取許可: bool = False,
             停止要求: Callable[[], bool] | None = None) -> 能力結果:
        traces, documents, passages, refs = [], [], [], []
        covered: set[str] = set()
        attempts = 0

        def 結果(成立: bool, 理由: str = "") -> 能力結果:
            data = {"版": 知識取得版, "状態": "合格" if 成立 else "保留",
                    "意味的事実検証": "未実施", "要求": asdict(要求),
                    "不足語": [w for w in 要求.必要語 if w not in covered],
                    "資料": documents, "抜粋": passages, "試行": traces,
                    "本文取得数": attempts, "資料数": len(refs)}
            encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
            if len(encoded) + sum(len(r.本文.encode("utf-8")) for r in refs) > 1_000_000:
                return 能力結果(False, "", 保留理由="取得記録サイズ上限")
            data["記録SHA256"] = sha256(encoded).hexdigest()
            return 能力結果(成立, "\n\n".join(p["本文"] for p in passages) if 成立 else "",
                            根拠=tuple(r.識別子 for r in refs), 参照=tuple(refs), データ=data, 保留理由=理由)

        def 停止() -> bool:
            if 停止要求 is None:
                return False
            value = 停止要求()
            if type(value) is not bool:
                raise ValueError("停止要求型不正")
            return value

        try:
            if not isinstance(要求, 知識取得要求):
                raise ValueError("取得要求型不正")
            要求.検証()
            if type(外部読取許可) is not bool or not 外部読取許可:
                return 能力結果(False, "", 保留理由="外部読取未許可")
            tried_urls, tried_queries, hashes, final_urls = set(), set(), set(), set()
            query = 要求.検索語.strip()
            for round_no in range(要求.最大検索回数):
                if 停止():
                    return 結果(False, "停止要求")
                if query in tried_queries:
                    break
                tried_queries.add(query)
                traces.append({"作用": "検索", "検索語": query, "回": round_no + 1})
                try:
                    candidates = self.検索.検索(query, 要求.最大候補数)
                    if type(candidates) is not tuple:
                        raise ValueError("検索結果型不正")
                except Exception as exc:
                    traces.append({"作用": "検索失敗", "種類": type(exc).__name__})
                    candidates = ()
                if 停止():
                    return 結果(False, "停止要求")
                ordered = []
                for item in candidates[:要求.最大候補数]:
                    try:
                        if not isinstance(item, 参照資料) or type(item.題名) is not str:
                            raise ValueError("検索候補型不正")
                        url = 公開URL(item.URL)
                        priority = urlsplit(url).hostname in 要求.優先ホスト
                        ordered.append((not priority, url, item))
                    except (ValueError, TypeError):
                        traces.append({"作用": "候補除外", "理由": "候補型または公開URL不正"})
                ordered.sort(key=lambda row: row[0])  # 同順位は検索供給器の順序を保持する。
                for _, url, candidate in ordered:
                    if 停止():
                        return 結果(False, "停止要求")
                    if url in tried_urls or url in final_urls:
                        traces.append({"作用": "重複URL", "URL": url})
                        continue
                    if attempts >= 要求.最大取得数 or len(refs) >= 要求.最大資料数:
                        break
                    tried_urls.add(url)
                    attempts += 1
                    try:
                        doc = self.本文.取得(url)
                        _本文検証(doc, url)
                    except Exception as exc:
                        traces.append({"作用": "本文取得失敗", "URL": url, "種類": type(exc).__name__})
                        continue
                    if 停止():
                        return 結果(False, "停止要求")
                    if doc.本文SHA256 in hashes or doc.最終URL in final_urls:
                        traces.append({"作用": "重複資料", "URL": url, "最終URL": doc.最終URL})
                        continue
                    remaining = 要求.最大抜粋文字数 - sum(len(p["本文"]) for p in passages)
                    selected, hits = _抜粋(doc, 要求.必要語, remaining)
                    if not selected:
                        traces.append({"作用": "本文非採用", "URL": url, "理由": "必要語不一致または段落長上限"})
                        continue
                    key = "web:" + sha256((doc.最終URL + "\n" + doc.本文SHA256).encode()).hexdigest()[:24]
                    ref = 参照資料(key, doc.題名 or candidate.題名, "公開HTTPS本文", doc.最終URL, None, doc.本文)
                    refs.append(ref)
                    hashes.add(doc.本文SHA256)
                    final_urls.add(doc.最終URL)
                    covered.update(hits)
                    passages.extend({"参照ID": key, **p} for p in selected)
                    metadata = asdict(doc)
                    del metadata["本文"]
                    metadata["参照ID"] = key
                    metadata["検索語"] = query
                    metadata["優先元一致"] = urlsplit(doc.最終URL).hostname in 要求.優先ホスト
                    metadata["公開時刻"] = None  # 取得時刻や検索スニペットの時刻を記事公開時刻にしない。
                    documents.append(metadata)
                    traces.append({"作用": "本文採用", "URL": url, "一致語": sorted(hits), "参照ID": key})
                    if all(w in covered for w in 要求.必要語) and len(refs) >= 要求.最低資料数:
                        return 結果(True)
                if attempts >= 要求.最大取得数 or len(refs) >= 要求.最大資料数:
                    break
                missing = [w for w in 要求.必要語 if w not in covered]
                query = 要求.検索語.strip() + " " + " ".join(missing or 要求.必要語)
            return 結果(False, "必要語または最低資料数が未充足")
        except Exception as exc:
            # 故障した停止判定器・不正入力から検索や代替回答へ進まない。
            return 能力結果(False, "", 保留理由=f"知識取得契約・制御失敗:{type(exc).__name__}")
