"""app.py - the ClearTrace chat screen.

Run:  streamlit run app.py
Flow: message -> router.py picks a tool -> tools.py runs the algorithm file
      -> advisor.py writes the reply + reasons -> cards with buttons -> actions.py
"""
import os
import uuid

import streamlit as st

import actions
import advisor
import ai_client
import hosted
import router
import tools

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(APP_DIR, "demo_folder")
HOME = os.path.expanduser("~")
TOOL_FILES = {"quick_scan": "quick_scan.py", "sensitive": "sensitive.py",
              "duplicates": "duplicates.py", "search": "search.py + duplicates.py"}
ICONS = {"passport": "🪪", "payslip": "📄", "bank statement": "🏦", "TFN declaration": "🧾",
         "driver licence": "🪪", "medicare card": "💳", "personal details form": "📝"}

st.set_page_config(page_title="ClearTrace", page_icon="🔍", layout="centered")

# ---------------- state ----------------
ss = st.session_state
ss.setdefault("messages", [])
ss.setdefault("cards", {})
ss.setdefault("stats", {"sensitive": 0, "files": 0, "freed_mb": 0.0})
ss.setdefault("ai_calls", 0)
if hosted.HOSTED:
    # Public link: every visitor gets their own private fake laptop
    if "sandbox" not in ss or not os.path.isdir(ss.sandbox):
        ss.sandbox = hosted.new_sandbox()
        ss.folder = ss.sandbox
else:
    ss.setdefault("folder", DEMO if os.path.isdir(DEMO) else os.path.join(HOME, "Downloads"))


def say(role, text, cards=None, note=""):
    ss.messages.append({"role": role, "text": text, "cards": cards or [], "note": note})


def resolve_folder(name):
    """Turn "Downloads" etc. into a real folder, preferring the current base folder."""
    if not name:
        return ss.folder
    if hosted.HOSTED:  # never leave the visitor's sandbox
        for candidate in (os.path.join(ss.sandbox, name), os.path.join(ss.sandbox, name.capitalize())):
            if os.path.isdir(candidate) and hosted.inside(candidate, ss.sandbox):
                return candidate
        return ss.sandbox
    for base in (ss.folder, os.path.dirname(ss.folder), HOME):
        for candidate in (os.path.join(base, name), os.path.join(base, name.capitalize())):
            if os.path.isdir(candidate):
                return candidate
    return name if os.path.isdir(name) else ss.folder


def short(path):
    if hosted.HOSTED:
        return os.path.relpath(path, os.path.dirname(ss.sandbox))
    return path.replace(HOME, "~")


# ---------------- cards ----------------

def new_card(kind, **data):
    cid = uuid.uuid4().hex[:8]
    ss.cards[cid] = {"kind": kind, "status": "", **data}
    return cid


def build_cards(tool, results, reasons):
    ids = []
    if tool == "sensitive":
        for f in results:
            r = reasons.get(f["path"], {})
            ids.append(new_card("sensitive", file=f, reason=r.get("reason", ""),
                                decision=r.get("decision", "delete")))
    elif tool == "duplicates":
        for g in results:
            keepers = [f for f in g["files"] if reasons.get(f["path"], {}).get("decision") == "keep"]
            keeper = keepers[0] if keepers else advisor.pick_keeper(g["files"])
            ids.append(new_card("dupes", group=g, keeper=keeper,
                                reason=reasons.get(keeper["path"], {}).get("reason", "")))
    elif tool == "search":
        for f in results[:3]:
            ids.append(new_card("found", file=f, reason=reasons.get(f["path"], {}).get("reason", "")))
    return ids


def do_delete(paths, sensitive=False):
    msgs = []
    for p in paths:
        res = hosted.delete(p, ss.sandbox) if hosted.HOSTED else actions.delete(p)
        msgs.append(res["message"])
        if res["ok"]:
            ss.stats["files"] += 1
            ss.stats["freed_mb"] += res.get("freed_mb", 0)
            if sensitive:
                ss.stats["sensitive"] += 1
            hosted.add_room(1 if sensitive else 0, res.get("freed_mb", 0))
    return " ".join(msgs)


def on_sensitive(cid, delete):
    c = ss.cards[cid]
    c["status"] = do_delete([c["file"]["path"]], sensitive=True) if delete else "Kept."


def on_dupes(cid, keep_one):
    c = ss.cards[cid]
    if keep_one:
        others = [f["path"] for f in c["group"]["files"] if f["path"] != c["keeper"]["path"]]
        c["status"] = do_delete(others)
    else:
        c["status"] = "Kept all copies."


def on_found(cid, delete_copies):
    c = ss.cards[cid]
    c["status"] = do_delete(c["file"]["duplicates"]) if delete_copies else "Kept both."


def render_card(cid):
    c = ss.cards[cid]
    with st.container(border=True):
        if c["kind"] == "sensitive":
            f = c["file"]
            icon = ICONS.get(f["doc_type"], "🔒")
            st.markdown(f"{icon} **{f['name']}** · {f['doc_type']} · {advisor.age_text(f['age_days'])}")
            st.caption(f"📁 {f['folder']}  ·  found: {', '.join(f['found'])}")
            if c["reason"]:
                st.write(c["reason"])
            if c["status"]:
                st.success(c["status"])
            else:
                a, b, _ = st.columns([1, 1, 3])
                a.button("🗑️ Delete", key=f"d{cid}", on_click=on_sensitive, args=(cid, True), type="primary")
                b.button("Keep", key=f"k{cid}", on_click=on_sensitive, args=(cid, False))

        elif c["kind"] == "dupes":
            g, keeper = c["group"], c["keeper"]
            st.markdown(f"🗂️ **{g['files'][0]['name']}** has **{len(g['files'])} copies** "
                        f"({advisor.fmt_size(g['wasted_mb'])} wasted)")
            for f in g["files"]:
                mark = "✅ keep" if f["path"] == keeper["path"] else "↳ copy"
                st.caption(f"{mark} · 📁 {f['folder']}")
            if c["status"]:
                st.success(c["status"])
            else:
                a, b, _ = st.columns([2, 1, 2])
                a.button(f"Keep {os.path.basename(keeper['folder']) or 'this'} copy", key=f"d{cid}",
                         on_click=on_dupes, args=(cid, True), type="primary")
                b.button("Keep all", key=f"k{cid}", on_click=on_dupes, args=(cid, False))

        elif c["kind"] == "found":
            f = c["file"]
            st.markdown(f"📄 **{f['name']}** · {advisor.age_text(f['age_days'])}")
            st.caption(f"📁 {short(f['path'])}")
            if f["duplicates"]:
                for d in f["duplicates"]:
                    st.caption(f"↳ identical copy: {short(d)}")
                if c["status"]:
                    st.success(c["status"])
                else:
                    n = len(f["duplicates"])
                    a, b, _ = st.columns([2, 1, 2])
                    a.button(f"🗑️ Delete cop{'y' if n == 1 else 'ies'}", key=f"d{cid}",
                             on_click=on_found, args=(cid, True), type="primary")
                    b.button("Keep both" if n == 1 else "Keep all", key=f"k{cid}",
                             on_click=on_found, args=(cid, False))


def render_cards(card_ids):
    """Show finished cards, then ONE open card at a time."""
    pending = 0
    for cid in card_ids:
        if ss.cards[cid]["status"]:
            render_card(cid)
        elif pending == 0:
            render_card(cid)
            pending += 1
        else:
            pending += 1
    if pending > 1:
        st.caption(f"{pending - 1} more to review after this one.")


# ---------------- handling a message ----------------

def handle(message, forced_tool=None):
    say("user", message)
    allow_ai = True
    if hosted.HOSTED:
        allow_ai = hosted.ai_allowed(ss.ai_calls)
        if allow_ai:
            ss.ai_calls += 2
    if forced_tool:
        r = {"tool": forced_tool, "keywords": [], "folder": "", "reply": ""}
    else:
        r = router.route(message, allow_ai=allow_ai)
    tool = r["tool"]
    if tool == "chat":
        say("assistant", r.get("reply") or "I can scan a folder, find sensitive files, "
            "find duplicates, or find a file. What would you like?", note="router.py → chat")
        return
    folder = resolve_folder(r.get("folder", ""))
    if tool == "search" and not r.get("keywords"):
        say("assistant", "Sure, what's the file called? For example: “Find my DSB201 week 8 lecture”.")
        return
    try:
        results = tools.run(tool, folder, r.get("keywords"))
    except Exception as e:
        say("assistant", f"Sorry, I couldn't read that folder: {e}")
        return
    out = advisor.explain(tool, results, message, allow_ai=allow_ai)
    cards = build_cards(tool, results, out["reasons"])
    note = f"router.py → {TOOL_FILES[tool]} on {short(folder)}"
    if tool == "search":
        note += f" · keywords: {', '.join(r['keywords'])}"
    say("assistant", out["reply"], cards, note)



# ---------------- layout ----------------

s = ss.stats


def key_box(m):
    with st.expander("🔑 Use your own Anthropic key", expanded=(m == "offline")):
        if m == "local":
            st.write("Using your key. It's saved only on this laptop, in the `.env` file.")
            if st.button("Remove my key"):
                ai_client.remove_key()
                st.rerun()
        else:
            st.caption("Optional. Get one at console.anthropic.com → API Keys. "
                       "It's saved only on this laptop and is never shown again.")
            with st.form("key_form", clear_on_submit=True):
                key = st.text_input("API key", type="password", placeholder="sk-ant-...")
                if st.form_submit_button("Save key"):
                    key = key.strip()
                    if not key:
                        st.error("Paste a key first.")
                    else:
                        with st.spinner("Checking key…"):
                            error = ai_client.check_key(key)
                        if error:
                            st.error(error)
                        else:
                            ai_client.save_key(key)
                            st.rerun()


def reset_laptop():
    ss.sandbox = hosted.new_sandbox()
    ss.folder = ss.sandbox
    ss.messages, ss.cards = [], {}
    ss.stats = {"sensitive": 0, "files": 0, "freed_mb": 0.0}


with st.sidebar:
    if hosted.HOSTED:
        st.header("🖥️ Your practice laptop")
        st.write("This is a **fake laptop** with made-up payslips, passports and staff forms. "
                 "Delete anything: it's yours alone and resets any time.")
        st.button("↺ Reset laptop", on_click=reset_laptop)
        st.divider()
        st.write("**Use it on your real laptop**")
        st.caption("ClearTrace runs locally so your files never leave your computer. "
                   "Download it from GitHub and double-click the start file.")
    else:
        st.header("📁 Folder to check")
        choices = {"Demo files": DEMO}
        for name in ("Downloads", "Desktop", "Documents"):
            if os.path.isdir(os.path.join(HOME, name)):
                choices[name] = os.path.join(HOME, name)
        cols = st.columns(2)
        for i, (label, path) in enumerate(choices.items()):
            if os.path.isdir(path) and cols[i % 2].button(label, use_container_width=True):
                ss.folder = path
        typed = st.text_input("Or paste a folder path", value=ss.folder)
        if typed != ss.folder:
            if os.path.isdir(typed):
                ss.folder = typed
            else:
                st.error("That folder doesn't exist.")
        st.caption(f"Checking: `{short(ss.folder)}`")

    st.divider()
    st.metric("Sensitive files removed", s["sensitive"])
    st.metric("Space freed", advisor.fmt_size(s["freed_mb"]))
    st.caption("Deleted files go to the Recycle Bin / Trash, so you can restore them.")

    st.divider()
    m = ai_client.mode()
    st.caption({"server": "🟢 AI: ClearTrace server",
                "local": "🟢 AI: Claude",
                "offline": "🟡 AI offline: using built-in rules"}[m])
    if not hosted.HOSTED:
        key_box(m)
    if st.button("Clear chat"):
        ss.messages, ss.cards = [], {}
        st.rerun()

st.title("🔍 ClearTrace")
st.caption("Find the risky, forgotten and duplicate files on your laptop. Just ask.")

if hosted.HOSTED:
    r = hosted.room()
    st.success(f"🌏 **Live:** the room has removed **{r['sensitive']}** sensitive files "
               f"and freed **{advisor.fmt_size(r['freed_mb'])}** so far")
    c1, c2 = st.columns([3, 1])
    c1.caption(f"🖥️ You're cleaning up **{os.path.basename(ss.folder)}**: a fake laptop just for you.")
    c2.button("↺ Reset", on_click=reset_laptop, use_container_width=True, key="reset_main")
    with st.expander("📤 Or try a few of your own files"):
        st.caption("Upload PDFs, Word docs or text files. They're only kept for 2 hours, "
                   "then deleted. The download version never uploads anything.")
        ups = st.file_uploader("Files", accept_multiple_files=True, label_visibility="collapsed",
                               type=["pdf", "docx", "txt", "md", "csv", "jpg", "png"])
        if ups and st.button(f"Add {len(ups)} file{'s' if len(ups) != 1 else ''} to my laptop"):
            folder, n = hosted.save_uploads(ups, ss.sandbox)
            say("assistant", f"Added {n} file{'s' if n != 1 else ''} to Uploads. "
                "Try “Find sensitive files” or “Do I have duplicates?”")
            st.rerun()

b1, b2, b3 = st.columns(3)
clicked = None
if b1.button("🔍 Quick scan", use_container_width=True):
    clicked = ("Quick scan this folder", "quick_scan")
if b2.button("🔒 Find sensitive files", use_container_width=True):
    clicked = ("Find sensitive files", "sensitive")
if b3.button("🗂️ Find duplicates", use_container_width=True):
    clicked = ("Find duplicates", "duplicates")

if not ss.messages:
    with st.chat_message("assistant", avatar="🔍"):
        if hosted.HOSTED:
            st.write("Hi! I'm ClearTrace. This is Alex's (fake) laptop, and it's a mess. "
                     "Tap a button above, or ask me something like "
                     "“Anything risky in Downloads?” or “Find my DSB201 week 8 lecture”.")
        else:
            st.write("Hi! I'm ClearTrace. Pick a folder on the left, then click a button above, "
                     "or ask me something like “Any sensitive files in my Downloads?” "
                     "or “Find my DSB201 week 8 lecture”.")

for msg in ss.messages:
    with st.chat_message(msg["role"], avatar="🔍" if msg["role"] == "assistant" else "🙂"):
        st.write(msg["text"])
        if msg["cards"]:
            render_cards(msg["cards"])
        if msg["note"]:
            st.caption(f"⚙️ {msg['note']}")

if s["files"]:
    st.info(f"✨ {s['sensitive']} sensitive file{'s' if s['sensitive'] != 1 else ''} removed · "
            f"{advisor.fmt_size(s['freed_mb'])} freed")

prompt = st.chat_input("Ask ClearTrace… e.g. “Do I have duplicates?”")
if clicked or prompt:
    with st.spinner("Checking your files…"):
        if clicked:
            handle(*clicked)
        else:
            handle(prompt)
    st.rerun()
