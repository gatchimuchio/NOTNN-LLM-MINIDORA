#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi-K3 公開weightを保存せずに全数走査し、HDS日本語意味構文へ変換するストリーム・コンパイラ。

重要:
- shard全体をローカル保存しない。
- HTTP Rangeでsafetensorsを小ブロック読みし、読んだ生データは即時破棄する。
- 各tensorは全payloadをSHA-256と数値統計へ通し、意味構文 + provenance + coverageだけ残す。
- 数値単独に語彙的意味を捏造しない。意味はtensorの接続関係・条件・数値状態として保持する。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests

HF_REPO = "moonshotai/Kimi-K3"
HF_REVISION = "c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721"
SHARD_COUNT = 96
DEFAULT_BLOCK = 64 * 1024 * 1024


def jdump(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def shard_name(i: int) -> str:
    if not 1 <= i <= SHARD_COUNT:
        raise ValueError(f"shard must be 1..{SHARD_COUNT}: {i}")
    return f"model-{i:05d}-of-{SHARD_COUNT:06d}.safetensors"


def resolve_url(filename: str, revision: str) -> str:
    return f"https://huggingface.co/{HF_REPO}/resolve/{revision}/{filename}?download=true"


class RangeError(RuntimeError):
    pass


@dataclass
class RangeResult:
    data: bytes
    total_size: int
    etag: Optional[str]
    repo_commit: Optional[str]
    final_url: str


def get_range(session: requests.Session, url: str, start: int, end: int, retries: int = 8) -> RangeResult:
    if end < start:
        raise ValueError((start, end))
    want = end - start + 1
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            r = session.get(
                url,
                headers={
                    "Range": f"bytes={start}-{end}",
                    "Accept-Encoding": "identity",
                    "User-Agent": "K3-HDS-Stream-Compiler/6.0",
                },
                timeout=(30, 180),
                allow_redirects=True,
            )
            if r.status_code != 206:
                raise RangeError(f"Range GET must be 206, got {r.status_code}; len={len(r.content)} final={r.url}")
            cr = r.headers.get("Content-Range", "")
            m = re.fullmatch(r"bytes\s+(\d+)-(\d+)/(\d+)", cr)
            if not m:
                raise RangeError(f"bad Content-Range: {cr!r}")
            got_start, got_end, total = map(int, m.groups())
            if got_start != start or got_end != end:
                raise RangeError(f"range mismatch wanted={start}-{end} got={got_start}-{got_end}")
            data = r.content
            if len(data) != want:
                raise RangeError(f"length mismatch wanted={want} got={len(data)}")
            return RangeResult(
                data=data,
                total_size=total,
                etag=r.headers.get("ETag") or r.headers.get("X-Linked-Etag"),
                repo_commit=r.headers.get("X-Repo-Commit"),
                final_url=r.url,
            )
        except Exception as e:
            last = e
            if attempt + 1 == retries:
                break
            time.sleep(min(2 ** attempt, 30))
    raise RangeError(f"range GET failed after {retries} attempts: {last}")


PRINCIPLE_FAMILIES: Dict[str, Dict[str, Any]] = {
    "P-EMBED": {
        "認知世界": "外部token住所と内部連続状態の対応関係として暫定形成する。",
        "原理質問": "何が離散tokenをK3内部状態として作用可能にしているのか。",
        "開放並列場": ["単なる索引表", "語彙意味の固定表", "文脈処理へ入る初期状態写像"],
        "原理分別": "値単体が語義ではなく、token住所×内部次元の関係係数として入力状態を成立させる。",
        "崩壊条件": "token住所対応または内部次元対応を変えると同一入力状態が成立しない。",
    },
    "P-LMHEAD": {
        "認知世界": "内部状態から外部token候補への表出関係として暫定形成する。",
        "原理質問": "何が内部状態を次token候補の比較可能な値へ変換しているのか。",
        "開放並列場": ["語彙表の逆写像", "単なる線形層", "次token候補形成の表出写像"],
        "原理分別": "内部次元とtoken住所の関係係数が候補値形成を成立させる。",
        "崩壊条件": "内部次元/token住所の対応を変えると同じ候補順位形成が成立しない。",
    },
    "P-NORM": {
        "認知世界": "次の比較・変換前に内部状態の尺度関係を整える作用として暫定形成する。",
        "原理質問": "何が層間で状態尺度の暴走を抑え、後段の関係比較を成立させるのか。",
        "開放並列場": ["単なる数値安定化", "学習済み再尺度化", "後段処理条件の形成"],
        "原理分別": "状態成分の相対尺度を条件化することで後段演算を同一座標系で成立させる。",
        "崩壊条件": "尺度係数または正規化規則を変えると後段への入力関係が変わる。",
    },
    "P-ATTN-Q": {
        "認知世界": "現在状態から参照要求を形成する関係として暫定形成する。",
        "原理質問": "何が現在状態から『何を参照するか』の条件を作るのか。",
        "開放並列場": ["単なる投影", "位置情報の変換", "参照要求の形成"],
        "原理分別": "現在状態の成分を参照比較用の問合せ座標へ写すことで参照選択を成立させる。",
        "崩壊条件": "問合せ写像を変えると同じ状態でも参照対象関係が変わる。",
    },
    "P-ATTN-KV": {
        "認知世界": "参照候補側の照合鍵・取得値を形成する関係として暫定形成する。",
        "原理質問": "何が過去/周辺状態を参照可能な候補として住所化し、取得内容を保持するのか。",
        "開放並列場": ["圧縮投影", "照合鍵形成", "取得値形成", "共有潜在表現"],
        "原理分別": "候補状態を照合座標と取得座標へ写し、問合せとの関係比較と内容回収を成立させる。",
        "崩壊条件": "鍵/値写像を変えると同じ候補状態の参照適合度または取得内容が変わる。",
    },
    "P-ATTN-O": {
        "認知世界": "参照結果を主内部状態へ帰還させる関係として暫定形成する。",
        "原理質問": "何が参照結果を次の内部状態へ作用可能に戻しているのか。",
        "開放並列場": ["単なる出力投影", "head統合", "参照結果の状態帰還"],
        "原理分別": "参照空間の結果をモデル主状態座標へ戻すことで次処理への作用を成立させる。",
        "崩壊条件": "帰還写像を変えると同じ参照結果でも次状態への作用が変わる。",
    },
    "P-KDA": {
        "認知世界": "系列履歴の保持・更新・読出しを条件化する状態遷移として暫定形成する。",
        "原理質問": "何が現在入力と旧系列状態から次系列状態を成立させるのか。",
        "開放並列場": ["attention近似", "畳み込み的履歴", "ゲート付き状態更新"],
        "原理分別": "現在入力に応じて保持/書込/読出しの関係を変えることで有限状態の系列継続を成立させる。",
        "崩壊条件": "ゲート・状態写像・履歴混合規則を変えると同じ系列から同じ次状態が成立しない。",
    },
    "P-MOE-ROUTER": {
        "認知世界": "現在状態から専門変換候補を選ぶ条件形成として暫定形成する。",
        "原理質問": "何が896専門候補のうち現在状態に作用させる経路を分けるのか。",
        "開放並列場": ["分類器", "負荷分散器", "状態依存の作用経路選択器"],
        "原理分別": "状態×専門候補の適合関係を形成し、top-k条件と組み合わさって局所作用経路を成立させる。",
        "崩壊条件": "適合写像または選択条件を変えると同じ入力でも通過expert集合が変わる。",
    },
    "P-MOE-LATENT": {
        "認知世界": "7168主状態と3584 routed-expert潜在状態の境界変換として暫定形成する。",
        "原理質問": "何が大きな主状態を専門変換可能な潜在状態へ接続し、再び主状態へ戻すのか。",
        "開放並列場": ["圧縮目的だけの投影", "専門処理の共通入口/出口", "低次元潜在境界"],
        "原理分別": "主状態と専門潜在状態の非同一座標系を橋渡しし、巨大MoEを成立可能にする境界関係。",
        "崩壊条件": "入口/出口写像または潜在次元関係を変えるとexpert変換と主状態が接続しない。",
    },
    "P-MOE-EXPERT": {
        "認知世界": "選択されたexpert内部の学習済み状態変換として暫定形成する。",
        "原理質問": "何が同じ入力状態に対して専門ごとに異なる変換結果を成立させるのか。",
        "開放並列場": ["単なる巨大パラメータ分割", "冗長な並列MLP", "条件選択される専門変換族"],
        "原理分別": "expert固有の係数関係が、routerで選ばれた条件下だけ局所状態変換として作用する。",
        "崩壊条件": "expert係数・expert住所・routerとの対応を変えると同じ専門作用は成立しない。",
    },
    "P-SHARED-EXPERT": {
        "認知世界": "router選択に依存せず共通に作用する専門変換として暫定形成する。",
        "原理質問": "何が入力ごとの専門選択とは別に共通知識変換を常時保持するのか。",
        "開放並列場": ["通常MLP", "専門系の補助", "全入力共通の変換経路"],
        "原理分別": "選択expertと並列に共通変換を持つことで、入力横断の基底作用を維持する。",
        "崩壊条件": "共有経路を除く/変更するとrouter非依存の共通作用が失われる。",
    },
    "P-DENSE-MLP": {
        "認知世界": "単一層内の非線形状態変換として暫定形成する。",
        "原理質問": "何が参照以外の状態成分変換を成立させるのか。",
        "開放並列場": ["単なる線形投影対", "特徴展開/圧縮", "非線形状態変換"],
        "原理分別": "展開・活性化・帰還の係数関係により参照とは異なる局所状態変換を成立させる。",
        "崩壊条件": "投影または活性化関係を変えると同じ入力から同じ変換状態が成立しない。",
    },
    "P-VISION": {
        "認知世界": "画像/動画媒体を内部視覚状態へ写す関係として暫定形成する。",
        "原理質問": "何が画素媒体をK3内部で比較・統合できる状態へ変えるのか。",
        "開放並列場": ["画像特徴抽出器", "tokenizer相当", "視覚状態形成器"],
        "原理分別": "空間/時間パッチと視覚内部次元の関係を形成し、媒体差を内部状態へ射影する。",
        "崩壊条件": "patch/位置/視覚変換関係を変えると同じ媒体から同じ視覚状態が成立しない。",
    },
    "P-MM-PROJ": {
        "認知世界": "視覚内部状態と言語主状態の境界接続として暫定形成する。",
        "原理質問": "何が異なる内部表現系を同一系列処理へ接続可能にするのか。",
        "開放並列場": ["次元合わせ", "情報圧縮", "異種媒体状態の共通化境界"],
        "原理分別": "視覚側状態を言語側7168次元関係へ写すことで同じ系列中で作用可能にする。",
        "崩壊条件": "境界写像を変えると視覚状態の言語系列への意味作用が変わる。",
    },
    "P-OTHER": {
        "認知世界": "名称・形状・周辺実装から確定できない内部作用量として暫定保持する。",
        "原理質問": "この数値関係は何を成立させているのか。",
        "開放並列場": ["主作用量", "補助係数", "圧縮/実装上の付随状態", "名称規約と実作用の不一致"],
        "原理分別": "現在の観測だけでは一意確定しないため、数値・座標・接続名を失わずHDS適合不能として保持する。",
        "崩壊条件": "実装側の参照箇所を追加観測するまで原理確定しない。",
    },
}


def principle_for_tensor(name: str) -> str:
    n = name.lower()
    if "embed_tokens" in n or ".embedding" in n:
        return "P-EMBED"
    if "lm_head" in n:
        return "P-LMHEAD"
    if "vision_tower" in n or "vision_model" in n:
        return "P-VISION"
    if "mm_projector" in n or ".projector" in n:
        return "P-MM-PROJ"
    if "shared_expert" in n:
        return "P-SHARED-EXPERT"
    if "routed_expert_down_proj" in n or "routed_expert_up_proj" in n or "routed_expert_norm" in n:
        return "P-MOE-LATENT"
    if ".experts." in n or "block_sparse_moe.experts" in n:
        return "P-MOE-EXPERT"
    if "block_sparse_moe.gate" in n or "router" in n:
        return "P-MOE-ROUTER"
    if "linear_attn" in n or ".kda" in n or "short_conv" in n:
        return "P-KDA"
    if any(x in n for x in ("q_proj", "q_a_proj", "q_b_proj", ".query")):
        return "P-ATTN-Q"
    if any(x in n for x in ("kv_a_proj", "kv_b_proj", "k_proj", "v_proj", ".key", ".value")):
        return "P-ATTN-KV"
    if any(x in n for x in ("o_proj", "out_proj")) and ("attn" in n or "attention" in n):
        return "P-ATTN-O"
    if "norm" in n:
        return "P-NORM"
    if any(x in n for x in ("mlp", "up_proj", "down_proj", "gate_proj")):
        return "P-DENSE-MLP"
    return "P-OTHER"


def parse_coordinates(name: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    m = re.search(r"(?:^|\.)layers\.(\d+)(?:\.|$)", name)
    if m:
        out["layer"] = int(m.group(1))
    m = re.search(r"(?:^|\.)experts\.(\d+)(?:\.|$)", name)
    if m:
        out["expert"] = int(m.group(1))
    for w in ("w1", "w2", "w3"):
        if f".{w}." in name:
            out["expert_projection"] = w
    if name.endswith("weight_packed"):
        out["physical_encoding"] = "MXFP4 packed code (U8 container, 2 x 4-bit code per byte)"
    elif name.endswith("weight_scale"):
        out["physical_encoding"] = "MXFP4 group scale code (uint8)"
    return out


DTYPE_INFO: Dict[str, Tuple[str, int]] = {
    "BOOL": ("?", 1), "U8": ("u1", 1), "I8": ("i1", 1), "U16": ("<u2", 2), "I16": ("<i2", 2),
    "U32": ("<u4", 4), "I32": ("<i4", 4), "U64": ("<u8", 8), "I64": ("<i8", 8),
    "F16": ("<f2", 2), "F32": ("<f4", 4), "F64": ("<f8", 8), "BF16": ("BF16", 2),
}


@dataclass
class TensorStats:
    name: str
    dtype: str
    shape: List[int]
    start: int
    end: int
    sha256: Any = field(default_factory=hashlib.sha256)
    bytes_seen: int = 0
    byte_hist: np.ndarray = field(default_factory=lambda: np.zeros(256, dtype=np.int64))
    numeric_count: int = 0
    finite_count: int = 0
    nonfinite_count: int = 0
    zero_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    numeric_sum: float = 0.0
    numeric_sumsq: float = 0.0
    numeric_min: float = math.inf
    numeric_max: float = -math.inf
    tail: bytes = b""
    nibble_hist: Optional[np.ndarray] = None

    def __post_init__(self) -> None:
        if self.name.endswith("weight_packed"):
            self.nibble_hist = np.zeros(16, dtype=np.int64)

    def update(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.sha256.update(chunk)
        self.bytes_seen += len(chunk)
        b = np.frombuffer(chunk, dtype=np.uint8)
        self.byte_hist += np.bincount(b, minlength=256)
        if self.nibble_hist is not None:
            self.nibble_hist += np.bincount(b & 0x0F, minlength=16)
            self.nibble_hist += np.bincount(b >> 4, minlength=16)
        info = DTYPE_INFO.get(self.dtype)
        if not info:
            return
        npdtype, itemsize = info
        raw = self.tail + chunk
        usable = len(raw) - (len(raw) % itemsize)
        if usable == 0:
            self.tail = raw
            return
        body, self.tail = raw[:usable], raw[usable:]
        if npdtype == "BF16":
            u = np.frombuffer(body, dtype="<u2").astype(np.uint32)
            a = (u << 16).view(np.float32)
        else:
            a = np.frombuffer(body, dtype=npdtype)
        af = a.astype(np.float64)
        self.numeric_count += int(af.size)
        finite = np.isfinite(af)
        self.finite_count += int(finite.sum())
        self.nonfinite_count += int((~finite).sum())
        if finite.any():
            x = af[finite]
            self.zero_count += int((x == 0).sum())
            self.positive_count += int((x > 0).sum())
            self.negative_count += int((x < 0).sum())
            self.numeric_sum += float(x.sum(dtype=np.float64))
            self.numeric_sumsq += float(np.square(x, dtype=np.float64).sum(dtype=np.float64))
            self.numeric_min = min(self.numeric_min, float(x.min()))
            self.numeric_max = max(self.numeric_max, float(x.max()))

    def finish(self) -> Dict[str, Any]:
        if self.tail:
            raise ValueError(f"unaligned numeric tail for {self.name}: {len(self.tail)} bytes")
        if self.bytes_seen != self.end - self.start:
            raise ValueError(f"tensor byte coverage mismatch {self.name}: {self.bytes_seen} != {self.end - self.start}")
        hist = self.byte_hist
        probs = hist[hist > 0].astype(np.float64) / max(self.bytes_seen, 1)
        entropy = float(-(probs * np.log2(probs)).sum()) if probs.size else 0.0
        rec: Dict[str, Any] = {
            "payload_bytes": self.bytes_seen,
            "payload_sha256": self.sha256.hexdigest(),
            "raw_byte_min": int(np.flatnonzero(hist)[0]) if self.bytes_seen else None,
            "raw_byte_max": int(np.flatnonzero(hist)[-1]) if self.bytes_seen else None,
            "raw_byte_entropy_bits": entropy,
        }
        if self.numeric_count:
            n = self.finite_count
            mean = self.numeric_sum / n if n else None
            var = max(self.numeric_sumsq / n - mean * mean, 0.0) if n and mean is not None else None
            rec["numeric"] = {
                "element_count": self.numeric_count, "finite_count": self.finite_count,
                "nonfinite_count": self.nonfinite_count, "zero_count": self.zero_count,
                "positive_count": self.positive_count, "negative_count": self.negative_count,
                "min": None if self.numeric_min == math.inf else self.numeric_min,
                "max": None if self.numeric_max == -math.inf else self.numeric_max,
                "mean": mean, "std": math.sqrt(var) if var is not None else None,
            }
        if self.nibble_hist is not None:
            rec["mxfp4_code_histogram_0_15"] = [int(x) for x in self.nibble_hist]
        return rec


def tensor_semantic_record(shard: str, tensor: TensorStats, stats: Dict[str, Any], data_base: int) -> Dict[str, Any]:
    pid = principle_for_tensor(tensor.name)
    coords = parse_coordinates(tensor.name)
    expected_bytes = tensor.end - tensor.start
    status = "HDS適合" if pid != "P-OTHER" else "HDS適合不能"
    anomaly: List[str] = []
    num = stats.get("numeric") or {}
    if num.get("nonfinite_count", 0):
        anomaly.append("非有限値を観測")
    if num and num.get("element_count") and num.get("zero_count") == num.get("finite_count"):
        anomaly.append("全有限要素が0")
    if stats.get("raw_byte_entropy_bits", 0.0) == 0.0 and expected_bytes:
        anomaly.append("payload全byteが同値")
    reopen = bool(anomaly) or pid == "P-OTHER"
    physical = coords.get("physical_encoding")
    local = (
        f"{tensor.name} の全 {expected_bytes} byteを実読し、{pid} の成立関係に局所接続した。"
        "値単独を語彙へ置換せず、座標・shape・dtype・数値分布・実payload hashを同時保持する。"
    )
    if physical:
        local += f" 物理符号化は {physical} として保持する。"
    return {
        "source": {
            "repo": HF_REPO, "revision": HF_REVISION, "shard": shard, "tensor": tensor.name,
            "dtype": tensor.dtype, "shape": tensor.shape,
            "payload_range_in_safetensors": [data_base + tensor.start, data_base + tensor.end],
            "payload_range_relative": [tensor.start, tensor.end],
        },
        "coordinates": coords,
        "observed": stats,
        "HDS": {
            "status": status, "原理族": pid, "局所適用": local,
            "結果帰還": anomaly or ["全payload走査上の異常兆候なし"], "総再開放": reopen,
        },
        "日本語意味構文": {
            "対象": tensor.name, "成立関係": PRINCIPLE_FAMILIES[pid]["原理分別"],
            "条件": f"K3 revision {HF_REVISION} / {shard} / dtype={tensor.dtype} / shape={tensor.shape}",
            "作用量": "実payload全値。個々の値は当該座標で上記関係へ寄与する学習済み係数または物理符号。",
            "崩壊条件": PRINCIPLE_FAMILIES[pid]["崩壊条件"],
            "未確定": "値単独の語彙的意味は確定しない。実装参照と状態関係を超えて意味を捏造しない。",
        },
    }


def scan_shard(shard_index: int, out_path: Path, audit_path: Path, block_size: int,
               max_payload_bytes: Optional[int], allow_partial: bool, revision: str) -> int:
    global HF_REVISION
    HF_REVISION = revision
    shard = shard_name(shard_index)
    url = resolve_url(shard, revision)
    s = requests.Session()

    first = get_range(s, url, 0, 7)
    header_len = struct.unpack("<Q", first.data)[0]
    if header_len <= 1 or header_len > 512 * 1024 * 1024:
        raise ValueError(f"implausible safetensors header length: {header_len}")
    header_rr = get_range(s, url, 8, 8 + header_len - 1)
    if header_rr.total_size != first.total_size:
        raise ValueError("remote size changed while reading header")
    header = json.loads(header_rr.data)
    entries: List[Tuple[int, int, str, Dict[str, Any]]] = []
    metadata = header.get("__metadata__")
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        a, b = map(int, meta["data_offsets"])
        entries.append((a, b, name, meta))
    entries.sort(key=lambda x: (x[0], x[1], x[2]))
    if not entries:
        raise ValueError("no tensors in shard")
    gaps: List[List[int]] = []
    overlaps: List[Dict[str, Any]] = []
    cursor = 0
    for a, b, name, _ in entries:
        if a > cursor:
            gaps.append([cursor, a])
        if a < cursor:
            overlaps.append({"tensor": name, "start": a, "previous_end": cursor})
        cursor = max(cursor, b)
    payload_len = cursor
    data_base = 8 + header_len
    expected_file_size = data_base + payload_len
    trailing_or_mismatch = first.total_size - expected_file_size

    scan_limit = payload_len if max_payload_bytes is None else min(payload_len, max_payload_bytes)
    partial = scan_limit < payload_len
    file_hash = hashlib.sha256()
    file_hash.update(first.data)
    file_hash.update(header_rr.data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    tensors_completed = 0
    payload_scanned = 0
    tensor_payload_scanned = 0
    unassigned_payload = 0
    unknown_hds = 0

    with gzip.open(out_path, "wt", encoding="utf-8") as out:
        out.write(jdump({"kind": "HDS原理族定義", "source": {"repo": HF_REPO, "revision": revision}, "principles": PRINCIPLE_FAMILIES}) + "\n")
        out.write(jdump({
            "kind": "safetensors_header_observation",
            "source": {"repo": HF_REPO, "revision": revision, "shard": shard},
            "remote_total_bytes": first.total_size, "header_length": header_len,
            "header_sha256": hashlib.sha256(header_rr.data).hexdigest(), "metadata": metadata,
            "tensor_count": len(entries), "payload_bytes_expected_from_header": payload_len,
            "gaps": gaps, "overlaps": overlaps, "file_size_minus_header_derived": trailing_or_mismatch,
            "HDS": "物理shard境界は意味境界と仮定せず、headerをtensor住所関係として観測する。",
        }) + "\n")

        idx = 0
        active: Optional[TensorStats] = None
        block_start = 0
        while block_start < scan_limit:
            block_end = min(block_start + block_size, scan_limit)
            rr = get_range(s, url, data_base + block_start, data_base + block_end - 1)
            if rr.total_size != first.total_size:
                raise ValueError("remote size changed during payload scan")
            block = rr.data
            file_hash.update(block)
            payload_scanned += len(block)
            local = 0
            while local < len(block):
                absolute_payload_pos = block_start + local
                while idx < len(entries) and entries[idx][1] <= absolute_payload_pos:
                    a, b, name, meta = entries[idx]
                    if active is not None and active.name == name:
                        stats = active.finish()
                        rec = tensor_semantic_record(shard, active, stats, data_base)
                        if rec["HDS"]["status"] != "HDS適合":
                            unknown_hds += 1
                        out.write(jdump({"kind": "tensor_HDS日本語意味構文", **rec}) + "\n")
                        tensors_completed += 1
                        active = None
                    idx += 1
                if idx >= len(entries):
                    rest = block[local:]
                    unassigned_payload += len(rest)
                    local = len(block)
                    continue
                a, b, name, meta = entries[idx]
                if absolute_payload_pos < a:
                    take = min(len(block) - local, a - absolute_payload_pos)
                    unassigned_payload += take
                    local += take
                    continue
                if active is None:
                    active = TensorStats(name=name, dtype=str(meta.get("dtype")), shape=list(meta.get("shape", [])), start=a, end=b)
                elif active.name != name:
                    raise RuntimeError(f"active tensor mismatch {active.name} != {name}")
                take = min(len(block) - local, b - absolute_payload_pos)
                seg = block[local:local + take]
                active.update(seg)
                tensor_payload_scanned += take
                local += take
                absolute_payload_pos += take
                if absolute_payload_pos == b:
                    stats = active.finish()
                    rec = tensor_semantic_record(shard, active, stats, data_base)
                    if rec["HDS"]["status"] != "HDS適合":
                        unknown_hds += 1
                    out.write(jdump({"kind": "tensor_HDS日本語意味構文", **rec}) + "\n")
                    tensors_completed += 1
                    active = None
                    idx += 1
            block_start = block_end
            print(jdump({"shard": shard, "payload_scanned": payload_scanned, "payload_target": scan_limit, "tensors_completed": tensors_completed}), flush=True)

        partial_active = None
        if active is not None:
            partial_active = {
                "tensor": active.name, "bytes_seen": active.bytes_seen,
                "tensor_bytes": active.end - active.start, "partial_sha256": active.sha256.hexdigest(),
            }

    complete = (
        not partial and not gaps and not overlaps and trailing_or_mismatch == 0 and unassigned_payload == 0
        and payload_scanned == payload_len and tensor_payload_scanned == payload_len
        and tensors_completed == len(entries) and active is None
    )
    smoke_ok = (
        partial and allow_partial and payload_scanned == scan_limit and unassigned_payload == 0
        and not overlaps and trailing_or_mismatch == 0
    )
    audit = {
        "source": {
            "repo": HF_REPO, "revision": revision, "shard": shard, "url": url,
            "repo_commit_header": first.repo_commit, "etag": first.etag,
        },
        "remote_total_bytes": first.total_size, "header_bytes_scanned": 8 + header_len,
        "payload_bytes_expected": payload_len, "payload_bytes_scanned": payload_scanned,
        "tensor_payload_bytes_scanned": tensor_payload_scanned,
        "tensor_count_expected": len(entries), "tensor_count_completed": tensors_completed,
        "gaps": gaps, "overlaps": overlaps, "unassigned_payload_bytes": unassigned_payload,
        "trailing_or_size_mismatch_bytes": trailing_or_mismatch, "HDS適合不能tensor数": unknown_hds,
        "partial": partial, "partial_active_tensor": partial_active,
        "file_sha256_if_complete": file_hash.hexdigest() if complete else None,
        "coverage": {"payload_ratio": payload_scanned / payload_len if payload_len else 1.0, "全byte実読": complete},
        "PASS": complete, "SMOKE_PASS": smoke_ok,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2), flush=True)
    if complete or smoke_ok:
        return 0
    return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--block-size", type=int, default=DEFAULT_BLOCK)
    ap.add_argument("--max-payload-bytes", type=int)
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--revision", default=HF_REVISION)
    args = ap.parse_args()
    return scan_shard(args.shard, args.out, args.audit, args.block_size, args.max_payload_bytes, args.allow_partial, args.revision)


if __name__ == "__main__":
    raise SystemExit(main())
