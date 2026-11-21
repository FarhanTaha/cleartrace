"""main.py - ClearTrace desktop app.

Opens a real app window (Edge WebView2 on Windows, WebKit on Mac) that shows
ui/index.html. The page calls the Python functions in Api below.

Run:    python main.py
Build:  pyinstaller build.spec   ->  dist/ClearTrace.exe
"""
import json
import os
import sys
import threading
import time
import uuid

import webview

import actions
import advisor
import ai_client
import router
import tools
from quick_scan import list_drives

HOME = os.path.expanduser("~")
TOOL_FILES = {"quick_scan": "quick_scan.py", "sensitive": "sensitive.py",
              "duplicates": "duplicates.py", "search": "search.py + duplicates.py"}
ICONS = {"passport": "🪪", "payslip": "📄", "bank statement": "🏦", "TFN declaration": "🧾",
         "driver licence": "🪪", "medicare card": "💳", "personal details form": "📝"}


def resource(path):
    """Find bundled files both when running from source and from the .exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)


def short(path):
    return path.replace(HOME, "~", 1) if path.startswith(HOME) else path


def rel(path, root):
    """Path shown to the user: relative to the folder being checked, e.g. Downloads/x.pdf."""
    try:
        r = os.path.relpath(path, root)
        if not r.startswith(".."):
            name = os.path.basename(root.rstrip("\\/")) or root
            return os.path.join(name, r)
    except ValueError:  # different drive on Windows
        pass
    return short(path)


class Api:
    """Every public method here can be called from JavaScript: pywebview.api.<name>()."""

    def __init__(self):
        self._window = None
        self._allowed = set()     # only files ClearTrace showed can be deleted
        self._last_progress = 0

    # ---------- setup ----------
    def info(self):
        shortcuts = []
        for name in ("Downloads", "Desktop", "Documents", "Pictures"):
            path = os.path.join(HOME, name)
            if os.path.isdir(path):
                shortcuts.append({"label": name, "path": path})
        drives = [{"label": d.rstrip("\\") if os.name == "nt" else (os.path.basename(d) or "Main drive (/)"),
                   "path": d} for d in list_drives()]
        return {"mode": ai_client.mode(), "shortcuts": shortcuts, "drives": drives,
                "home": HOME, "os": os.name}

    def choose_folder(self):
        dialog = getattr(getattr(webview, "FileDialog", None), "FOLDER", None) or webview.FOLDER_DIALOG
        result = self._window.create_file_dialog(dialog, directory=HOME)
        if not result:
            return None
        path = result[0] if isinstance(result, (list, tuple)) else result
        return {"path": path, "label": self._label(path)}

    def folder_label(self, path):
        return self._label(path)

    @staticmethod
    def _label(path):
        name = os.path.basename(path.rstrip("\\/"))
        return name or path

    # ---------- chat ----------
    def send(self, message, folder, forced_tool=None):
        try:
            return self._send(message, folder, forced_tool)
        except Exception as e:  # never crash the window
            return {"reply": f"Sorry, something went wrong: {e}", "cards": [], "note": ""}
        finally:
            self._progress_js(None)

    def _send(self, message, folder, forced_tool):
        if not folder or not os.path.isdir(folder):
            return {"reply": "Pick a folder or drive first.", "cards": [], "note": ""}
        if forced_tool:
            r = {"tool": forced_tool, "keywords": [], "folder": "", "reply": ""}
        else:
            self._progress_js({"label": "Understanding your request…"})
            r = router.route(message)
        tool = r["tool"]
        if tool == "chat":
            return {"reply": r.get("reply") or "I can scan a folder, find sensitive files, "
                    "find duplicates, or find a file. What would you like?",
                    "cards": [], "note": "router.py → chat"}
        if tool == "search" and not r.get("keywords"):
            return {"reply": "Sure, what's the file called? For example: “Find my DSB201 week 8 lecture”.",
                    "cards": [], "note": ""}

        target = self._resolve(folder, r.get("folder", ""))
        started = time.time()
        results = tools.run(tool, target, r.get("keywords"), progress=self._progress)
        self._progress_js({"label": "Writing the explanation…"})
        out = advisor.explain(tool, results, message)
        cards = self._cards(tool, results, out["reasons"], target)
        note = f"router.py → {TOOL_FILES[tool]} on {self._label(target)} · {time.time() - started:.1f}s"
        if tool == "search":
            note += f" · keywords: {', '.join(r['keywords'])}"
        if not out.get("ai"):
            note += " · basic reply (AI not reachable)"
        return {"reply": out["reply"], "cards": cards, "note": note, "mode": ai_client.mode()}

    @staticmethod
    def _resolve(folder, name):
        """'Downloads' etc. inside the chosen folder or the home folder; else the chosen folder."""
        if name:
            for base in (folder, HOME):
                for candidate in (os.path.join(base, name), os.path.join(base, name.capitalize())):
                    if os.path.isdir(candidate):
                        return candidate
        return folder

    # ---------- progress ----------
    def _progress(self, done, total, label):
        now = time.time()
        if now - self._last_progress < 0.1 and done != total:
            return
        self._last_progress = now
        self._progress_js({"done": done, "total": total, "label": label})

    def _progress_js(self, data):
        if self._window:
            try:
                self._window.evaluate_js(f"setProgress({json.dumps(data)})")
            except Exception:
                pass

    # ---------- cards ----------
    def _allow(self, paths):
        self._allowed.update(paths)
        return paths

    def _cards(self, tool, results, reasons, root):
        cards = []
        if tool == "sensitive":
            for f in results:
                r = reasons.get(f["path"], {})
                cards.append({
                    "id": uuid.uuid4().hex[:8], "kind": "sensitive",
                    "icon": ICONS.get(f["doc_type"], "🔒"), "name": f["name"],
                    "doc_type": f["doc_type"], "age": advisor.age_text(f["age_days"]),
                    "folder": f["folder"], "found": f["found"], "reason": r.get("reason", ""),
                    "copies": [os.path.dirname(rel(p, root)) for p in f["duplicates"]],
                    "delete_paths": self._allow([f["path"]] + f["duplicates"]),
                })
        elif tool == "duplicates":
            for g in results[:100]:
                keepers = [f for f in g["files"] if reasons.get(f["path"], {}).get("decision") == "keep"]
                keeper = keepers[0] if keepers else advisor.pick_keeper(g["files"])
                cards.append({
                    "id": uuid.uuid4().hex[:8], "kind": "dupes", "name": g["files"][0]["name"],
                    "count": len(g["files"]), "wasted": advisor.fmt_size(g["wasted_mb"]),
                    "files": [{"folder": f["folder"], "keep": f["path"] == keeper["path"]} for f in g["files"]],
                    "keep_label": os.path.basename(keeper["folder"]) or "this",
                    "delete_paths": self._allow([f["path"] for f in g["files"] if f["path"] != keeper["path"]]),
                })
        elif tool == "search":
            for f in results[:5]:
                cards.append({
                    "id": uuid.uuid4().hex[:8], "kind": "found", "name": f["name"],
                    "age": advisor.age_text(f["age_days"]), "path": rel(f["path"], root),
                    "full_path": f["path"], "copies": [rel(p, root) for p in f["duplicates"]],
                    "delete_paths": self._allow(list(f["duplicates"])),
                })
        return cards

    # ---------- actions ----------
    def delete(self, paths, sensitive=False):
        messages, freed, removed = [], 0.0, 0
        for p in paths:
            if p not in self._allowed:
                messages.append(f"Skipped {os.path.basename(p)}.")
                continue
            res = actions.delete(p)
            messages.append(res["message"])
            if res["ok"]:
                removed += 1
                freed += res.get("freed_mb", 0)
                self._allowed.discard(p)
        if removed and removed == len(paths):
            names = {os.path.basename(p) for p in paths}
            what = names.pop() if len(names) == 1 and removed == 1 else f"{removed} files"
            messages = [f"Moved {what} to the Recycle Bin."]
        return {"message": " ".join(messages), "removed": removed, "freed_mb": freed,
                "sensitive": 1 if (sensitive and removed) else 0}

    def open_location(self, path):
        """Show a file in Explorer / Finder."""
        import subprocess
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
        except OSError:
            pass

    # ---------- settings ----------
    def save_key(self, key):
        key = (key or "").strip()
        if not key:
            return "Paste a key first."
        error = ai_client.check_key(key)
        if not error:
            ai_client.save_key(key)
        return error

    def remove_key(self):
        ai_client.remove_key()
        return ai_client.mode()


WEBVIEW2_ID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def has_webview2():
    """Windows 11 always has WebView2; some older Windows 10 PCs don't."""
    import winreg
    keys = [(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_ID}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_ID}"),
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_ID}")]
    for root, path in keys:
        try:
            with winreg.OpenKey(root, path) as k:
                version, _ = winreg.QueryValueEx(k, "pv")
                if version and version != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False


def need_webview2():
    """Explain the missing piece instead of showing a blank window."""
    import ctypes
    import webbrowser
    answer = ctypes.windll.user32.MessageBoxW(
        0, "ClearTrace needs Microsoft Edge WebView2, a free Microsoft component that most "
           "Windows PCs already have.\n\nClick Yes to download it (1 minute), then open ClearTrace again.",
        "ClearTrace", 0x04 | 0x40)  # Yes/No + info icon
    if answer == 6:  # Yes
        webbrowser.open(WEBVIEW2_URL)


def selftest(folder):
    """Used by the build check: scan a folder without opening a window, write results, exit."""
    api = Api()
    out = {"info": api.info()}
    for tool in ("quick_scan", "sensitive", "duplicates"):
        out[tool] = api.send("", folder, tool)
    out["search"] = api.send("find week 8", folder)
    failed = [k for k, v in out.items() if isinstance(v, dict) and str(v.get("reply", "")).startswith("Sorry")]
    out["ok"] = not failed
    with open(os.path.join(folder, "selftest_result.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    if sys.stdout:  # a windowed .exe has no console
        print(json.dumps({k: (v.get("reply") if isinstance(v, dict) and "reply" in v else v)
                          for k, v in out.items() if k != "info"}, indent=1, ensure_ascii=False))
    sys.exit(1 if failed else 0)


def main():
    if "--selftest" in sys.argv:
        selftest(sys.argv[sys.argv.index("--selftest") + 1])
        return
    api = Api()
    window = webview.create_window(
        "ClearTrace", url=resource(os.path.join("ui", "index.html")), js_api=api,
        width=1000, height=760, min_size=(420, 560), background_color="#F7F8FA")
    api._window = window
    # Wake the AI server in the background so the first message is quick
    threading.Thread(target=ai_client.warm_up, daemon=True).start()
    debug = "--debug" in sys.argv
    if os.name == "nt":
        if not has_webview2():
            need_webview2()
            return
        try:
            webview.start(gui="edgechromium", debug=debug)
        except Exception:
            need_webview2()
    else:
        webview.start(debug=debug)


if __name__ == "__main__":
    main()
