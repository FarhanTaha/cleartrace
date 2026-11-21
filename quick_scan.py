"""quick_scan.py - lists every file in a folder.

Returns {"files": [FileResult, ...], "summary": {...}}.
Test:  python quick_scan.py <folder>
"""
import os
import sys
import time
from datetime import datetime

SKIP_DIRS = {"venv", ".venv", "node_modules", "__pycache__", ".git",
             "AppData", "Library", "$RECYCLE.BIN", "System Volume Information"}
MAX_FILES = 5000   # keeps scans of huge folders quick

TYPE_GROUPS = {
    "PDFs": {".pdf"},
    "Word docs": {".doc", ".docx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp"},
    "Spreadsheets": {".xls", ".xlsx", ".csv"},
    "Slides": {".ppt", ".pptx"},
    "Text": {".txt", ".md"},
    "Archives": {".zip", ".rar", ".7z"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv"},
}


def file_result(path, root=None):
    """Build one FileResult dict (the shared format from README.md)."""
    st = os.stat(path)
    folder = os.path.dirname(path)
    if root:
        rel = os.path.relpath(folder, os.path.dirname(os.path.abspath(root)))
        folder = rel
    age_days = int((time.time() - st.st_mtime) // 86400)
    return {
        "name": os.path.basename(path),
        "path": os.path.abspath(path),
        "folder": folder,
        "type": os.path.splitext(path)[1].lower() or "(none)",
        "size_mb": round(st.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
        "age_days": age_days,
        "doc_type": "",
        "found": [],
        "snippet": "",
        "duplicates": [],
    }


def list_files(folder):
    """Yield paths of normal (non-hidden, non-system) files under folder."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in SKIP_DIRS]
        for name in filenames:
            if name.startswith(".") or name.startswith("~$") or name in ("desktop.ini", "Thumbs.db"):
                continue
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            yield path
            count += 1
            if count >= MAX_FILES:
                return


def quick_scan(folder):
    files = []
    for path in list_files(folder):
        try:
            files.append(file_result(path, folder))
        except OSError:
            continue

    by_type = {}
    for f in files:
        group = next((g for g, exts in TYPE_GROUPS.items() if f["type"] in exts), "Other")
        by_type[group] = by_type.get(group, 0) + 1

    summary = {
        "folder": os.path.abspath(folder),
        "total_files": len(files),
        "total_size_mb": round(sum(f["size_mb"] for f in files), 1),
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "not_opened_1yr": sum(1 for f in files if f["age_days"] > 365),
    }
    return {"files": files, "summary": summary}


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "demo_folder"
    result = quick_scan(folder)
    s = result["summary"]
    print(f"{s['total_files']} files, {s['total_size_mb']} MB, "
          f"{s['not_opened_1yr']} not changed in over a year")
    for group, n in s["by_type"].items():
        print(f"  {group}: {n}")
