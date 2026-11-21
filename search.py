"""search.py - finds a specific file, e.g. "DSB201 week 8".

A file matches when its name, folder or text contains ALL keywords (case-insensitive).
Test:  python search.py <folder> DSB201 week 8
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from duplicates import _safe_hash
from extractor import can_read, get_text
from quick_scan import quick_scan

WORKERS = 8
READ_ALL_LIMIT = 3000   # read every document's text if there are at most this many


def _norm(s):
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def search(folder, keywords, progress=None, files=None):
    keywords = [_norm(k) for k in keywords if k.strip()]
    if not keywords:
        return []
    files = files if files is not None else quick_scan(folder, progress)["files"]

    readable = sum(1 for f in files if can_read(f["path"]))
    read_all = readable <= READ_ALL_LIMIT   # small folder: look inside every document
    matches, to_read = [], []
    for f in files:
        name = _norm(os.path.splitext(f["name"])[0] + " " + f["folder"])
        if all(k in name for k in keywords):
            matches.append(f)
        elif can_read(f["path"]) and (read_all or any(k in name for k in keywords)):
            to_read.append((f, name))   # big drive: only open files that partly match

    total = len(to_read)
    with ThreadPoolExecutor(WORKERS) as pool:
        texts = pool.map(lambda fn: _norm(get_text(fn[0]["path"])), to_read)
        for i, ((f, name), text) in enumerate(zip(to_read, texts), 1):
            if all(k in name + " " + text for k in keywords):
                f["snippet"] = text[:300]
                matches.append(f)
            if progress and (i % 10 == 0 or i == total):
                progress(i, total, "Searching inside documents…")

    # Collapse identical copies into one result, listing the others in "duplicates"
    by_hash = {}
    for f in matches:
        by_hash.setdefault(_safe_hash(f["path"]) or f["path"], []).append(f)
    results = []
    for copies in by_hash.values():
        # main copy: not in Downloads/Desktop, deepest folder
        copies.sort(key=lambda x: (any(p in x["folder"].lower() for p in ("downloads", "desktop")),
                                   -x["folder"].count(os.sep), x["age_days"]))
        main = copies[0]
        main["duplicates"] = [o["path"] for o in copies[1:]]
        results.append(main)
    results.sort(key=lambda x: x["age_days"])
    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search.py <folder> <keywords...>")
        sys.exit(1)
    for f in search(sys.argv[1], sys.argv[2:]):
        print(f"{os.path.join(f['folder'], f['name'])}  ({len(f['duplicates'])} identical copies)")
        for d in f["duplicates"]:
            print(f"    copy: {d}")
