from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "MINIDORA-GLM-D4-Audit/1.0"
RANGE_SIZE = 64 * 1024 * 1024
DTYPE_BYTES = {
    "BOOL": 1, "U8": 1, "I8": 1, "F8_E4M3": 1, "F8_E5M2": 1,
    "I16": 2, "U16": 2, "F16": 2, "BF16": 2,
    "I32": 4, "U32": 4, "F32": 4,
    "I64": 8, "U64": 8, "F64": 8,
}


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def pointer_meta(repo: str, revision: str, path: str):
    qpath = urllib.parse.quote(path, safe="/")
    url = f"https://huggingface.co/{repo}/raw/{revision}/{qpath}"
    text = get_text(url)
    oid = None
    size = None
    for line in text.splitlines():
        if line.startswith("oid sha256:"):
            oid = line.split(":", 1)[1].strip()
        elif line.startswith("size "):
            size = int(line.split()[1])
    return oid, size


def discover(repo: str, mirror_repo: str, slug: str, out_path: str):
    info = get_json(f"https://huggingface.co/api/models/{repo}")
    revision = info["sha"]
    tree = get_json(f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true&expand=true")
    rows = []
    files = [x for x in tree if x.get("type") == "file" and x.get("path", "").endswith(".safetensors")]
    files.sort(key=lambda x: x["path"])
    for idx, item in enumerate(files, 1):
        path = item["path"]
        lfs = item.get("lfs") or {}
        oid = lfs.get("oid") or lfs.get("sha256")
        size = lfs.get("size") or item.get("size")
        if not oid or not size:
            p_oid, p_size = pointer_meta(repo, revision, path)
            oid = oid or p_oid
            size = size or p_size
        if not oid or not size:
            raise RuntimeError(f"upstream SHA/size unresolved: {repo}:{path}")
        oid = str(oid).removeprefix("sha256:")
        rows.append({
            "id": f"{idx:04d}", "slug": slug, "repo": repo, "mirror_repo": mirror_repo,
            "revision": revision, "path": path, "sha256": oid, "size": int(size),
        })
    if not rows:
        raise RuntimeError(f"no safetensors found: {repo}")
    out = {"repo": repo, "mirror_repo": mirror_repo, "revision": revision, "slug": slug, "shards": rows}
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))


def urls_for(spec):
    path = urllib.parse.quote(spec["path"], safe="/")
    repo = spec["repo"]
    rev = spec["revision"]
    mirror = spec.get("mirror_repo")
    urls = [f"https://huggingface.co/{repo}/resolve/{rev}/{path}?download=true"]
    if mirror:
        urls += [
            f"https://modelscope.cn/models/{mirror}/resolve/master/{path}",
            f"https://www.modelscope.cn/models/{mirror}/resolve/master/{path}",
        ]
    return urls


def open_range(url: str, start: int, end: int):
    headers = {
        "User-Agent": UA, "Accept-Encoding": "identity", "Range": f"bytes={start}-{end}",
    }
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=180)


def stream_one(spec):
    expected_size = int(spec["size"])
    expected_sha = spec["sha256"].lower()
    h = hashlib.sha256()
    header_buf = bytearray()
    header_need = None
    total = 0
    source = None
    started = time.time()
    urls = urls_for(spec)

    for start in range(0, expected_size, RANGE_SIZE):
        end = min(expected_size - 1, start + RANGE_SIZE - 1)
        last_error = None
        chunk_done = False
        for attempt in range(4):
            for url in urls:
                try:
                    with open_range(url, start, end) as r:
                        status = getattr(r, "status", None)
                        data_read = 0
                        while True:
                            block = r.read(8 * 1024 * 1024)
                            if not block:
                                break
                            data_read += len(block)
                            h.update(block)
                            total += len(block)
                            if header_need is None or len(header_buf) < header_need:
                                need_now = (header_need - len(header_buf)) if header_need else (8 - len(header_buf))
                                if need_now > 0:
                                    header_buf.extend(block[:need_now])
                                if header_need is None and len(header_buf) >= 8:
                                    header_len = struct.unpack("<Q", bytes(header_buf[:8]))[0]
                                    if header_len <= 0 or header_len > 512 * 1024 * 1024:
                                        raise RuntimeError(f"invalid safetensors header length: {header_len}")
                                    header_need = 8 + header_len
                                    if len(header_buf) < header_need:
                                        remain = header_need - len(header_buf)
                                        header_buf.extend(block[need_now:need_now + remain])
                                elif header_need and len(header_buf) < header_need:
                                    remain = header_need - len(header_buf)
                                    header_buf.extend(block[need_now:need_now + remain])
                        wanted = end - start + 1
                        if status == 206 and data_read != wanted:
                            raise RuntimeError(f"range short read {data_read} != {wanted}")
                        if status == 200:
                            if start != 0 or data_read != expected_size:
                                raise RuntimeError(f"server ignored Range unexpectedly: status=200 start={start} bytes={data_read}")
                            source = url
                            chunk_done = True
                            break
                        if status != 206:
                            raise RuntimeError(f"unexpected HTTP status {status}")
                        source = url
                        chunk_done = True
                        break
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e} @ {url}"
                    continue
            if chunk_done:
                break
            time.sleep(min(20, 2 ** attempt))
        if not chunk_done:
            raise RuntimeError(f"failed range {start}-{end}: {last_error}")
        if total == expected_size:
            break

    actual_sha = h.hexdigest()
    if total != expected_size:
        raise RuntimeError(f"byte count mismatch: {total} != {expected_size}")
    if actual_sha != expected_sha:
        raise RuntimeError(f"sha256 mismatch: {actual_sha} != {expected_sha}")
    if header_need is None or len(header_buf) < header_need:
        raise RuntimeError("safetensors header incomplete")

    header_len = struct.unpack("<Q", bytes(header_buf[:8]))[0]
    header = json.loads(bytes(header_buf[8:8 + header_len]).decode("utf-8"))
    tensors = []
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        offsets = meta.get("data_offsets")
        if not isinstance(offsets, list) or len(offsets) != 2:
            raise RuntimeError(f"bad offsets: {name}")
        a, b = map(int, offsets)
        dtype = meta.get("dtype")
        shape = meta.get("shape", [])
        n = 1
        for dim in shape:
            n *= int(dim)
        item_bytes = DTYPE_BYTES.get(dtype)
        if item_bytes is not None and (b - a) != n * item_bytes:
            raise RuntimeError(f"tensor byte mismatch: {name}: {b-a} != {n*item_bytes}")
        tensors.append((a, b, name, dtype, shape))
    tensors.sort()
    cursor = 0
    gaps = []
    overlaps = []
    for a, b, name, dtype, shape in tensors:
        if a > cursor:
            gaps.append((cursor, a, name))
        if a < cursor:
            overlaps.append((a, cursor, name))
        cursor = max(cursor, b)
    data_bytes = expected_size - (8 + header_len)
    if cursor < data_bytes:
        gaps.append((cursor, data_bytes, "EOF"))
    if cursor > data_bytes:
        overlaps.append((data_bytes, cursor, "OUT_OF_RANGE"))
    if gaps or overlaps:
        raise RuntimeError(f"payload coverage failure gaps={gaps[:5]} overlaps={overlaps[:5]}")

    return {
        "schema": "minidora.glm.weight_payload_audit.v1",
        "repo": spec["repo"], "revision": spec["revision"], "path": spec["path"],
        "expected_size": expected_size, "bytes_read": total,
        "expected_sha256": expected_sha, "actual_sha256": actual_sha, "sha256_match": True,
        "header_bytes": 8 + header_len, "tensor_count": len(tensors),
        "payload_bytes": data_bytes, "no_gaps": True, "no_overlaps": True, "source_url": source,
        "elapsed_seconds": round(time.time() - started, 3), "status": "PASS",
    }


def audit_shard(spec_json: str, out_dir: str):
    spec = json.loads(spec_json)
    result = stream_one(spec)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{spec['slug']}-{spec['id']}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


def aggregate(manifest_dir: str, result_dir: str, output: str):
    manifests = [json.loads(p.read_text(encoding="utf-8")) for p in pathlib.Path(manifest_dir).glob("*.json")]
    results = [json.loads(p.read_text(encoding="utf-8")) for p in pathlib.Path(result_dir).glob("*.json")]
    expected = {(s["repo"], s["revision"], s["path"]): s for m in manifests for s in m["shards"]}
    got = {(r["repo"], r["revision"], r["path"]): r for r in results}
    missing = sorted([{"repo": k[0], "revision": k[1], "path": k[2]} for k in expected.keys() - got.keys()], key=lambda x:(x["repo"],x["path"]))
    failed = [r for r in results if r.get("status") != "PASS" or not r.get("sha256_match") or not r.get("no_gaps") or not r.get("no_overlaps")]
    by_repo = {}
    for m in manifests:
        repo = m["repo"]
        rr = [r for r in results if r["repo"] == repo and r["revision"] == m["revision"]]
        by_repo[repo] = {
            "revision": m["revision"], "expected_shards": len(m["shards"]), "audited_shards": len(rr),
            "bytes_read": sum(r.get("bytes_read", 0) for r in rr), "tensors": sum(r.get("tensor_count", 0) for r in rr),
            "pass": len(rr) == len(m["shards"]) and all(r.get("status") == "PASS" for r in rr),
        }
    summary = {
        "schema": "minidora.glm.weight_payload_full_audit.v1",
        "status": "PASS" if not missing and not failed and len(got) == len(expected) else "FAIL",
        "expected_shards": len(expected), "audited_shards": len(got),
        "bytes_read": sum(r.get("bytes_read", 0) for r in results),
        "tensor_count": sum(r.get("tensor_count", 0) for r in results),
        "missing": missing, "failed": failed, "models": by_repo,
    }
    pathlib.Path(output).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(output).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit(1)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--repo", required=True); d.add_argument("--mirror-repo", required=True); d.add_argument("--slug", required=True); d.add_argument("--out", required=True)
    a = sub.add_parser("audit-shard")
    a.add_argument("--spec-env", default="SHARD_SPEC"); a.add_argument("--out-dir", required=True)
    g = sub.add_parser("aggregate")
    g.add_argument("--manifest-dir", required=True); g.add_argument("--result-dir", required=True); g.add_argument("--output", required=True)
    args = p.parse_args()
    if args.cmd == "discover":
        discover(args.repo, args.mirror_repo, args.slug, args.out)
    elif args.cmd == "audit-shard":
        audit_shard(os.environ[args.spec_env], args.out_dir)
    else:
        aggregate(args.manifest_dir, args.result_dir, args.output)


if __name__ == "__main__":
    main()
