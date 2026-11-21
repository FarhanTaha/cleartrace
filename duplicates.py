"""duplicates.py - finds identical copies of files.

Fast on big drives: group by size, then hash the first 64 KB, then hash fully.
Test:  python duplicates.py <folder>
"""
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from quick_scan import file_result, quick_scan, walk

WORKERS = 8
MIN_BYTES = 1  # ignore empty files


def file_hash(path, limit=None):
    h = hashlib.sha256()
    read = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            read += len(chunk)
            if limit and read >= limit:
                break
    return h.hexdigest()


def _safe_hash(path, limit=None):
    try:
        return file_hash(path, limit)
    except OSError:
        return None


def _group(files, key_fn, progress, label):
    """Group files by key_fn(path), computed in parallel."""
    groups = {}
    total = len(files)
    with ThreadPoolExecutor(WORKERS) as pool:
        for i, (f, key) in enumerate(zip(files, pool.map(lambda f: key_fn(f["path"]), files)), 1):
            if key:
                groups.setdefault(key, []).append(f)
            if progress and (i % 50 == 0 or i == total):
                progress(i, total, label)
    return [g for g in groups.values() if len(g) > 1]


def find_duplicates(folder, progress=None, files=None):
    files = files if files is not None else quick_scan(folder, progress)["files"]

    by_size = {}
    for f in files:
        if f["size_bytes"] >= MIN_BYTES:
            by_size.setdefault(f["size_bytes"], []).append(f)
    candidates = [f for same in by_size.values() if len(same) > 1 for f in same]

    # 1) quick check: first 64 KB   2) full hash only for files that still match
    partial = _group(candidates, lambda p: _safe_hash(p, 64 * 1024), progress, "Comparing files…")
    maybe = [f for g in partial for f in g]
    full = _group(maybe, _safe_hash, progress, "Confirming identical copies…")

    groups = []
    for files_ in full:
        # same size AND same hash
        by_size_again = {}
        for f in files_:
            by_size_again.setdefault(f["size_bytes"], []).append(f)
        for same in by_size_again.values():
            if len(same) < 2:
                continue
            for f in same:
                f["duplicates"] = [o["path"] for o in same if o is not f]
            groups.append({
                "hash": _safe_hash(same[0]["path"]) or "",
                "size_mb": same[0]["size_mb"],
                "files": same,
                "wasted_mb": round(same[0]["size_bytes"] * (len(same) - 1) / (1024 * 1024), 2),
            })
    groups.sort(key=lambda g: -g["wasted_mb"])
    return groups


def copies_of(path, folder):
    """Return FileResults of identical copies of one file inside folder."""
    target = os.path.abspath(path)
    size = os.path.getsize(target)
    digest = None
    copies = []
    for other, st in walk(folder):
        if os.path.abspath(other) == target or st.st_size != size:
            continue
        digest = digest or file_hash(target)
        if _safe_hash(other) == digest:
            copies.append(file_result(other, folder, st))
    return copies


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    groups = find_duplicates(folder)
    total = sum(g["wasted_mb"] for g in groups)
    print(f"Found {len(groups)} sets of identical files, wasting {total:.2f} MB")
    for g in groups[:20]:
        print(f"  {g['files'][0]['name']} x{len(g['files'])}:")
        for f in g["files"]:
            print(f"     {f['folder']}")
