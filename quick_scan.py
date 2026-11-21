"""quick_scan.py - lists every file in a folder or drive.

Returns {"files": [FileResult, ...], "summary": {...}}.
Test:  python quick_scan.py <folder>
       python quick_scan.py --drives
"""
import os
import string
import sys
import time
from datetime import datetime

# Folders never worth scanning (system files, apps, caches)
SKIP_DIRS = {
    # Windows
    "windows", "program files", "program files (x86)", "programdata", "appdata",
    "$recycle.bin", "system volume information", "recovery", "msocache", "$windows.~bt",
    "$windows.~ws", "perflogs", "intel", "amd", "nvidia",
    # Mac / Linux
    "library", "system", "applications", "private", "usr", "bin", "sbin", "etc", "dev",
    "proc", "sys", "var", "opt", "cores", "snap", "boot", "lib", "lib64", "run", "tmp",
    # developer build output (regenerated automatically, never personal files)
    "node_modules", "__pycache__", "venv", ".venv", "site-packages", ".git",
    "obj", "target", "__macosx",
}
MAX_FILES = 200_000   # safety cap for whole drives

TYPE_GROUPS = {
    "PDFs": {".pdf"},
    "Word docs": {".doc", ".docx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp"},
    "Spreadsheets": {".xls", ".xlsx", ".csv"},
    "Slides": {".ppt", ".pptx"},
    "Text": {".txt", ".md"},
    "Archives": {".zip", ".rar", ".7z"},
    "Videos": {".mp4", ".mov", ".avi", ".mkv"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg"},
}


def list_drives():
    """Drives the user can pick: C:\\, D:\\, USBs... (Windows) or / and /Volumes/* (Mac)."""
    if os.name == "nt":
        return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    drives = ["/"]
    for base in ("/Volumes", "/media", "/mnt"):
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                path = os.path.join(base, name)
                if os.path.isdir(path) and not os.path.islink(path):
                    drives.append(path)
    return drives


def _label(folder):
    """Short name for the scanned folder, e.g. "Downloads" or "C:"."""
    folder = os.path.abspath(folder)
    return os.path.basename(folder.rstrip("\\/")) or folder.rstrip("\\/") or folder


def file_result(path, root=None, st=None):
    """Build one FileResult dict (the shared format from README.md)."""
    st = st or os.stat(path)
    folder = os.path.dirname(path)
    if root:
        rel = os.path.relpath(folder, os.path.abspath(root))
        folder = _label(root) if rel == "." else os.path.join(_label(root), rel)
    return {
        "name": os.path.basename(path),
        "path": os.path.abspath(path),
        "folder": folder,
        "type": os.path.splitext(path)[1].lower() or "(none)",
        "size_mb": round(st.st_size / (1024 * 1024), 2),
        "size_bytes": st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
        "age_days": int((time.time() - st.st_mtime) // 86400),
        "doc_type": "",
        "found": [],
        "snippet": "",
        "duplicates": [],
    }


def walk(folder, progress=None):
    """Yield (path, stat) for normal files. Skips hidden and system folders."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(folder, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith((".", "$", "~")) and d.lower() not in SKIP_DIRS]
        for name in filenames:
            if name.startswith((".", "~$")) or name.lower() in ("desktop.ini", "thumbs.db"):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path, follow_symlinks=False)
            except OSError:
                continue
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            yield path, st
            count += 1
            if progress and count % 500 == 0:
                progress(count, 0, f"Listing files… {count:,} so far")
            if count >= MAX_FILES:
                return


def list_files(folder):
    """Just the paths (used by duplicates.copies_of)."""
    for path, _ in walk(folder):
        yield path


def quick_scan(folder, progress=None):
    files = [file_result(p, folder, st) for p, st in walk(folder, progress)]

    by_type = {}
    for f in files:
        group = next((g for g, exts in TYPE_GROUPS.items() if f["type"] in exts), "Other")
        by_type[group] = by_type.get(group, 0) + 1

    summary = {
        "folder": os.path.abspath(folder),
        "name": _label(folder),
        "total_files": len(files),
        "total_size_mb": round(sum(f["size_mb"] for f in files), 1),
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
        "not_opened_1yr": sum(1 for f in files if f["age_days"] > 365),
        "capped": len(files) >= MAX_FILES,
    }
    return {"files": files, "summary": summary}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drives":
        print(list_drives())
        sys.exit()
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    t = time.time()
    s = quick_scan(folder)["summary"]
    print(f"{s['name']}: {s['total_files']} files, {s['total_size_mb']} MB, "
          f"{s['not_opened_1yr']} not changed in over a year ({time.time() - t:.1f}s)")
    for group, n in s["by_type"].items():
        print(f"  {group}: {n}")
