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


# Windows IDs for the standard folders (these work even when OneDrive has moved them)
KNOWN_FOLDER_IDS = {
    "Desktop": "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "Documents": "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "Downloads": "374DE290-123F-4565-9164-39C4925E467B",
    "Pictures": "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "Music": "4BD8D571-6D19-48D3-BE97-422220080E43",
    "Videos": "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
}


def _windows_known_folder(guid_text):
    import ctypes
    import uuid
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    guid = GUID.from_buffer_copy(uuid.UUID(guid_text).bytes_le)
    out = ctypes.c_wchar_p()
    if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) != 0:
        return None
    path = out.value
    ctypes.windll.ole32.CoTaskMemFree(out)
    return path


def known_folders():
    """Where Desktop, Documents, Downloads... really are on this computer.
    On Windows, OneDrive often moves Desktop to C:\\Users\\you\\OneDrive\\Desktop."""
    home = os.path.expanduser("~")
    found = {}
    for name, guid in KNOWN_FOLDER_IDS.items():
        path = None
        if os.name == "nt":
            try:
                path = _windows_known_folder(guid)
            except Exception:
                path = None
        candidates = [path, os.path.join(home, name), os.path.join(home, "OneDrive", name)]
        if name == "Videos" and sys.platform == "darwin":
            candidates.insert(1, os.path.join(home, "Movies"))
        for c in candidates:
            if c and os.path.isdir(c):
                found[name] = c
                break
    return found


def _label(folder):
    """Short name for the scanned folder, e.g. "Downloads" or "C:"."""
    folder = os.path.abspath(folder)
    # A drive root (C:\\ or /) has no name: show it as-is, keeping the backslash
    return os.path.basename(folder.rstrip("\\/")) or folder


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
