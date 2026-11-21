"""search.py - finds a specific file, e.g. "DSB201 week 8".

A file matches when its name or text contains ALL keywords (case-insensitive).
Test:  python search.py demo_folder DSB201 week 8
"""
import os
import sys

from duplicates import file_hash
from extractor import get_text
from quick_scan import quick_scan

READABLE = {".pdf", ".docx", ".txt", ".md", ".csv"}


def _norm(s):
    return " ".join(s.lower().replace("_", " ").replace("-", " ").split())


def search(folder, keywords):
    keywords = [_norm(k) for k in keywords if k.strip()]
    if not keywords:
        return []
    all_files = quick_scan(folder)["files"]
    matches = []
    for f in all_files:
        name = _norm(os.path.splitext(f["name"])[0] + " " + f["folder"])
        if all(k in name for k in keywords):
            matches.append(f)
            continue
        if f["type"] in READABLE:
            text = _norm(get_text(f["path"]))
            if all(k in name + " " + text for k in keywords):
                f["snippet"] = text[:300]
                matches.append(f)

    # Fill "duplicates" and collapse identical copies into one result
    hashes = {}
    for f in matches:
        try:
            hashes.setdefault(file_hash(f["path"]), []).append(f)
        except OSError:
            pass
    results = []
    for files in hashes.values():
        # keep the copy in the most "organised" folder (deepest path) as main
        files.sort(key=lambda x: (-x["folder"].count(os.sep), x["age_days"]))
        main = files[0]
        main["duplicates"] = [o["path"] for o in files[1:]]
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
