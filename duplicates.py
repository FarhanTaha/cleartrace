"""duplicates.py - finds identical copies of files.

Step 1: group files by size (cheap). Step 2: SHA-256 only files that share a size.
Test:  python duplicates.py demo_folder
"""
import hashlib
import os
import sys

from quick_scan import file_result, list_files, quick_scan


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(folder):
    by_size = {}
    for f in quick_scan(folder)["files"]:
        if f["size_mb"] == 0 and os.path.getsize(f["path"]) == 0:
            continue  # empty files are all "identical"; ignore them
        by_size.setdefault(os.path.getsize(f["path"]), []).append(f)

    groups = []
    for same_size in by_size.values():
        if len(same_size) < 2:
            continue
        by_hash = {}
        for f in same_size:
            try:
                by_hash.setdefault(file_hash(f["path"]), []).append(f)
            except OSError:
                continue
        for digest, files in by_hash.items():
            if len(files) < 2:
                continue
            for f in files:
                f["duplicates"] = [o["path"] for o in files if o is not f]
            size = files[0]["size_mb"]
            groups.append({
                "hash": digest,
                "size_mb": size,
                "files": files,
                "wasted_mb": round(size * (len(files) - 1), 2),
            })
    groups.sort(key=lambda g: -g["wasted_mb"])
    return groups


def copies_of(path, folder):
    """Return FileResults of identical copies of one file inside folder."""
    target = os.path.abspath(path)
    size = os.path.getsize(target)
    digest = None
    copies = []
    for other in list_files(folder):
        if os.path.abspath(other) == target or os.path.getsize(other) != size:
            continue
        digest = digest or file_hash(target)
        if file_hash(other) == digest:
            copies.append(file_result(other, folder))
    return copies


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "demo_folder"
    groups = find_duplicates(folder)
    total = sum(g["wasted_mb"] for g in groups)
    print(f"Found {len(groups)} sets of identical files, wasting {total:.2f} MB")
    for g in groups:
        print(f"  {g['files'][0]['name']} x{len(g['files'])}:")
        for f in g["files"]:
            print(f"     {f['folder']}")
