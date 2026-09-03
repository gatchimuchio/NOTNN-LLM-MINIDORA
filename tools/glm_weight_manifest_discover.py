from __future__ import annotations

import argparse
import json
import pathlib
import re
import urllib.parse
import urllib.request

UA = "MINIDORA-GLM-D4-Audit/2.0"
NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def request_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r), r.headers.get("Link")


def request_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def all_pages(url: str):
    out = []
    seen = set()
    while url:
        if url in seen:
            raise RuntimeError("pagination loop detected")
        seen.add(url)
        data, link = request_json(url)
        if not isinstance(data, list):
            raise RuntimeError("tree endpoint did not return list")
        out.extend(data)
        m = NEXT_RE.search(link or "")
        url = m.group(1) if m else None
    return out


def pointer_meta(repo: str, revision: str, path: str):
    qpath = urllib.parse.quote(path, safe="/")
    text = request_text(f"https://huggingface.co/{repo}/raw/{revision}/{qpath}")
    oid = None
    size = None
    for line in text.splitlines():
        if line.startswith("oid sha256:"):
            oid = line.split(":", 1)[1].strip()
        elif line.startswith("size "):
            size = int(line.split()[1])
    return oid, size


def discover(repo: str, mirror_repo: str, slug: str, out_path: str):
    info, _ = request_json(f"https://huggingface.co/api/models/{repo}")
    revision = info["sha"]
    tree_url = f"https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true&expand=true"
    tree = all_pages(tree_url)
    files = [x for x in tree if x.get("type") == "file" and x.get("path", "").endswith(".safetensors")]
    files.sort(key=lambda x: x["path"])
    rows = []
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
    manifest = {
        "schema": "minidora.glm.weight_manifest.v2",
        "repo": repo, "mirror_repo": mirror_repo, "revision": revision, "slug": slug,
        "tree_entries": len(tree), "shards": rows,
    }
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{repo} revision={revision} tree_entries={len(tree)} safetensors={len(rows)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--mirror-repo", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    discover(a.repo, a.mirror_repo, a.slug, a.out)


if __name__ == "__main__":
    main()
